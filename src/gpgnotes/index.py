"""Search index using SQLite FTS5."""

import sqlite3
from pathlib import Path
from typing import List, Tuple

from .config import Config
from .note import Note
from .todos import parse_todos


class SearchIndex:
    """Full-text search index for notes."""

    def __init__(self, config: Config):
        """Initialize search index."""
        self.config = config
        self.db_path = config.db_file
        self.conn: sqlite3.Connection = None
        self._init_db()

    def _init_db(self):
        """Initialize database with FTS5 table and todos table.

        Handles migrations for existing databases:
        - Creates notes_fts if not exists
        - Creates todos table if not exists (new in v0.3.0)
        - Creates note_links table if not exists (new in v0.5.0)
        - Adds indexes for efficient queries
        """
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

        # Check if notes_fts table exists and has the correct schema
        try:
            cursor = self.conn.execute("SELECT is_plain FROM notes_fts LIMIT 1")
            cursor.fetchone()
        except sqlite3.OperationalError:
            # Table doesn't exist or has old schema - recreate it
            self.conn.execute("DROP TABLE IF EXISTS notes_fts")
            self.conn.commit()

        # Create FTS5 virtual table for notes
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts
            USING fts5(
                title,
                content,
                tags,
                file_path UNINDEXED,
                created UNINDEXED,
                modified UNINDEXED,
                is_plain UNINDEXED
            )
        """)

        # Migration: Create todos table if it doesn't exist (v0.3.0+)
        # This is safe to run on both new and existing databases
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_path TEXT NOT NULL,
                line_number INTEGER NOT NULL,
                task TEXT NOT NULL,
                completed BOOLEAN NOT NULL DEFAULT 0,
                due_date TEXT,
                UNIQUE(note_path, line_number)
            )
        """)

        # Migration: Create note_links table if it doesn't exist (v0.5.0+)
        # Stores wiki-style links between notes for backlinks and link validation
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS note_links (
                source_id TEXT NOT NULL,
                source_title TEXT,
                target_id TEXT NOT NULL,
                target_title TEXT,
                link_type TEXT NOT NULL DEFAULT 'note',
                section TEXT NOT NULL DEFAULT '',
                block_id TEXT NOT NULL DEFAULT '',
                context TEXT,
                created_at TEXT NOT NULL,
                PRIMARY KEY (source_id, target_id, link_type, section, block_id)
            )
        """)

        # Create indexes for efficient queries (safe to run multiple times)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_todos_note_path ON todos(note_path)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_todos_completed ON todos(completed)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_backlinks ON note_links(target_id)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_source_links ON note_links(source_id)
        """)

        self.conn.commit()

    def add_note(self, note: Note):
        """Add or update note in index."""
        if not note.file_path:
            return

        # Use absolute path for consistency
        file_path_str = str(note.file_path.resolve())

        # Delete existing entry if present (try both absolute and as-is paths)
        self.conn.execute(
            """
            DELETE FROM notes_fts WHERE file_path = ? OR file_path = ?
        """,
            (file_path_str, str(note.file_path)),
        )
        self.conn.commit()

        # Insert new entry with absolute path
        self.conn.execute(
            """
            INSERT INTO notes_fts
            (title, content, tags, file_path, created, modified, is_plain)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                note.title,
                note.content,
                " ".join(note.tags),
                file_path_str,
                note.created.isoformat(),
                note.modified.isoformat(),
                1 if getattr(note, "is_plain", False) else 0,
            ),
        )

        self.conn.commit()

        # Automatically index links when note is added
        self.index_note_links(note)

        # Extract and store todos from the note content
        todos = parse_todos(note.content, file_path_str)
        if todos:
            todo_dicts = [
                {
                    "line_number": t.line_number,
                    "task": t.task,
                    "completed": t.completed,
                    "due_date": t.due_date,
                }
                for t in todos
            ]
            self.update_todos(file_path_str, todo_dicts)
        else:
            # Clear any existing todos if note no longer has any
            self.remove_todos_for_note(file_path_str)

        # Extract and index wiki links
        self.index_note_links(note)

    def remove_note(self, file_path: Path):
        """Remove note from index."""
        # Try to match both absolute and as-is paths
        abs_path = str(file_path.resolve())

        # First, get the note_id so we can remove links
        cursor = self.conn.execute(
            """
            SELECT file_path FROM notes_fts WHERE file_path = ? OR file_path = ?
            LIMIT 1
        """,
            (abs_path, str(file_path)),
        )
        row = cursor.fetchone()
        if row:
            # Extract note_id from file path
            from pathlib import Path as PathLib
            note_path = PathLib(row[0])
            note_id = note_path.stem.replace(".md", "")

            # Remove all links where this note is source or target
            self.conn.execute("DELETE FROM note_links WHERE source_id = ?", (note_id,))
            self.conn.execute("DELETE FROM note_links WHERE target_id = ?", (note_id,))

        self.conn.execute(
            """
            DELETE FROM notes_fts WHERE file_path = ? OR file_path = ?
        """,
            (abs_path, str(file_path)),
        )

        # Also remove todos for this note
        self.remove_todos_for_note(abs_path)
        self.remove_todos_for_note(str(file_path))

        self.conn.commit()

    def search(self, query: str, limit: int = 50) -> List[Tuple[str, str, str]]:
        """
        Search notes using FTS5.

        Returns list of (file_path, title, modified) tuples.
        """
        # Sanitize query for FTS5 by escaping special characters
        # Wrap in quotes to make it a phrase search and avoid syntax errors
        sanitized_query = query.replace('"', '""')  # Escape quotes
        fts_query = f'"{sanitized_query}"'

        cursor = self.conn.execute(
            """
            SELECT file_path, title, modified, rank
            FROM notes_fts
            WHERE notes_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """,
            (fts_query, limit),
        )

        return [(row["file_path"], row["title"], row["modified"]) for row in cursor]

    def search_by_title(
        self, title: str, exact: bool = True
    ) -> List[Tuple[str, str, str]]:
        """Search notes by title.

        Args:
            title: Title to search for
            exact: If True, search for exact title match

        Returns:
            List of (file_path, title, modified) tuples
        """
        if exact:
            # For exact match, use SQL LIKE instead of FTS5
            cursor = self.conn.execute(
                """
                SELECT file_path, title, modified
                FROM notes_fts
                WHERE title = ?
                ORDER BY modified DESC
                """,
                (title,),
            )
        else:
            # For fuzzy match, use FTS5 on title column
            sanitized_title = title.replace('"', '""')
            cursor = self.conn.execute(
                """
                SELECT file_path, title, modified
                FROM notes_fts
                WHERE title MATCH ?
                ORDER BY rank
                LIMIT 100
                """,
                (f'"{sanitized_title}"',),
            )

        return [(row["file_path"], row["title"], row["modified"]) for row in cursor]

    def search_by_tag(self, tag: str, limit: int = 50) -> List[str]:
        """Search notes by tag."""
        cursor = self.conn.execute(
            """
            SELECT file_path
            FROM notes_fts
            WHERE tags MATCH ?
            ORDER BY modified DESC
            LIMIT ?
        """,
            (f'"{tag}"', limit),
        )

        return [row["file_path"] for row in cursor]

    def list_all(self, limit: int = 100) -> List[Tuple[str, str, str]]:
        """
        List all notes in index.

        Returns list of (file_path, title, modified) tuples.
        """
        cursor = self.conn.execute(
            """
            SELECT file_path, title, modified
            FROM notes_fts
            ORDER BY modified DESC
            LIMIT ?
        """,
            (limit,),
        )

        return [(row["file_path"], row["title"], row["modified"]) for row in cursor]

    def get_all_metadata(
        self,
        sort_by: str = "modified",
        limit: int = None,
        tag_filter: str = None,
        inbox: bool = False,
        plain_filter: str = None,
    ) -> List[dict]:
        """
        Get metadata for all notes without decryption.

        Args:
            sort_by: Sort field ('modified', 'created', or 'title')
            limit: Maximum number of results (None for all)
            tag_filter: Filter by tag (None for all notes)
            inbox: If True, only return notes without any folder tags
            plain_filter: 'plain' for only plain notes, 'encrypted' for only encrypted

        Returns:
            List of dicts with keys: file_path, title, tags, created, modified, is_plain
        """
        # Build query
        query = (
            "SELECT file_path, title, tags, created, modified, is_plain "
            "FROM notes_fts"
        )

        # Add tag filter if specified
        params = []
        where_clauses = []
        if tag_filter:
            where_clauses.append("tags MATCH ?")
            params.append(f'"{tag_filter}"')

        # Add plain/encrypted filter
        if plain_filter == "plain":
            where_clauses.append("is_plain = 1")
        elif plain_filter == "encrypted":
            where_clauses.append("(is_plain = 0 OR is_plain IS NULL)")

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        # Add sorting
        if sort_by == "modified":
            query += " ORDER BY modified DESC"
        elif sort_by == "created":
            query += " ORDER BY created DESC"
        elif sort_by == "title":
            query += " ORDER BY title COLLATE NOCASE"

        # Add limit if specified (but not if inbox filtering, we filter after)
        if limit and not inbox:
            query += " LIMIT ?"
            params.append(limit)

        cursor = self.conn.execute(query, params)

        results = []
        for row in cursor:
            tags = row["tags"].split() if row["tags"] else []

            # If inbox mode, skip notes that have folder tags
            if inbox:
                has_folder = any(t.startswith("folder:") for t in tags)
                if has_folder:
                    continue

            results.append(
                {
                    "file_path": row["file_path"],
                    "title": row["title"],
                    "tags": tags,
                    "created": row["created"],
                    "modified": row["modified"],
                    "is_plain": (
                        bool(row["is_plain"]) if "is_plain" in row.keys() else False
                    ),
                }
            )

            # Apply limit after inbox filtering
            if limit and inbox and len(results) >= limit:
                break

        return results

    def get_folders(self) -> List[Tuple[str, int]]:
        """
        Get all folders (tags with 'folder:' prefix) with note counts.

        Returns:
            List of (folder_name, count) tuples sorted by count descending.
        """
        # Get all tags from all notes
        cursor = self.conn.execute("SELECT tags FROM notes_fts")

        folder_counts = {}
        for row in cursor:
            if row["tags"]:
                for tag in row["tags"].split():
                    if tag.startswith("folder:"):
                        folder_name = tag[7:]  # Remove 'folder:' prefix
                        folder_counts[folder_name] = (
                            folder_counts.get(folder_name, 0) + 1
                        )

        # Sort by count descending, then by name
        return sorted(folder_counts.items(), key=lambda x: (-x[1], x[0]))

    def update_todos(self, note_path: str, todos: List[dict]):
        """
        Update todos for a note.

        Args:
            note_path: Path to the note file
            todos: List of todo dicts with keys: line_number, task, completed
        """
        # Delete existing todos for this note
        self.conn.execute("DELETE FROM todos WHERE note_path = ?", (note_path,))

        # Insert new todos
        for todo in todos:
            self.conn.execute(
                """
                INSERT INTO todos (note_path, line_number, task, completed, due_date)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    note_path,
                    todo["line_number"],
                    todo["task"],
                    1 if todo["completed"] else 0,
                    todo.get("due_date"),
                ),
            )

        self.conn.commit()

    def get_todos(
        self,
        completed: bool = None,
        note_path: str = None,
        folder: str = None,
    ) -> List[dict]:
        """
        Get todos with optional filtering.

        Args:
            completed: Filter by completion status (None for all)
            note_path: Filter by specific note path
            folder: Filter by folder name (notes with folder:<name> tag)

        Returns:
            List of todo dicts with note metadata
        """
        # Build query with joins to get note metadata
        query = """
            SELECT t.id, t.note_path, t.line_number, t.task, t.completed, t.due_date,
                   n.title, n.tags, n.modified
            FROM todos t
            LEFT JOIN notes_fts n ON t.note_path = n.file_path
            WHERE 1=1
        """
        params = []

        if completed is not None:
            query += " AND t.completed = ?"
            params.append(1 if completed else 0)

        if note_path:
            query += " AND t.note_path = ?"
            params.append(note_path)

        if folder:
            # Filter by folder tag
            folder_tag = f"folder:{folder}"
            query += " AND n.tags LIKE ?"
            params.append(f"%{folder_tag}%")

        query += " ORDER BY n.modified DESC, t.line_number ASC"

        cursor = self.conn.execute(query, params)

        results = []
        for row in cursor:
            results.append(
                {
                    "id": row["id"],
                    "note_path": row["note_path"],
                    "line_number": row["line_number"],
                    "task": row["task"],
                    "completed": bool(row["completed"]),
                    "due_date": row["due_date"],
                    "note_title": row["title"],
                    "note_tags": row["tags"].split() if row["tags"] else [],
                    "note_modified": row["modified"],
                }
            )

        return results

    def get_todo_counts(self, folder: str = None) -> Tuple[int, int]:
        """
        Get count of incomplete and complete todos.

        Args:
            folder: Optional folder filter

        Returns:
            Tuple of (incomplete_count, complete_count)
        """
        if folder:
            folder_tag = f"folder:{folder}"
            cursor = self.conn.execute(
                """
                SELECT
                    SUM(CASE WHEN t.completed = 0 THEN 1 ELSE 0 END) as incomplete,
                    SUM(CASE WHEN t.completed = 1 THEN 1 ELSE 0 END) as complete
                FROM todos t
                LEFT JOIN notes_fts n ON t.note_path = n.file_path
                WHERE n.tags LIKE ?
                """,
                (f"%{folder_tag}%",),
            )
        else:
            cursor = self.conn.execute(
                """
                SELECT
                    SUM(CASE WHEN completed = 0 THEN 1 ELSE 0 END) as incomplete,
                    SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as complete
                FROM todos
                """
            )

        row = cursor.fetchone()
        return (row["incomplete"] or 0, row["complete"] or 0)

    def remove_todos_for_note(self, note_path: str):
        """Remove all todos for a specific note."""
        self.conn.execute("DELETE FROM todos WHERE note_path = ?", (note_path,))
        self.conn.commit()

    def rebuild_index(self, notes: List[Note]):
        """Rebuild entire index from scratch."""
        # Clear existing index
        self.conn.execute("DELETE FROM notes_fts")
        self.conn.commit()

        # Add all notes
        for note in notes:
            self.add_note(note)

    def index_note_links(self, note: Note):
        """Extract and index wiki links from a note.

        Args:
            note: Note to extract links from
        """
        from datetime import datetime

        from .links import LinkResolver, extract_context, extract_wiki_links

        # Remove old links from this note
        self.conn.execute("DELETE FROM note_links WHERE source_id = ?", (note.note_id,))

        # Extract links from content
        links = extract_wiki_links(note.content)
        if not links:
            self.conn.commit()
            return

        # Resolve each link and store
        resolver = LinkResolver(self.config)

        for link in links:
            # Try to resolve the target note
            target_note = resolver.resolve_link(link.target, fuzzy=False)

            target_id = target_note.note_id if target_note else link.target
            target_title = target_note.title if target_note else link.target

            # Extract context around the link
            context = extract_context(note.content, link.position)

            # Insert link
            self.conn.execute(
                """
                INSERT OR REPLACE INTO note_links
                (source_id, source_title, target_id, target_title, link_type,
                 section, block_id, context, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    note.note_id,
                    note.title,
                    target_id,
                    target_title,
                    link.link_type,
                    link.section or "",
                    link.block_id or "",
                    context,
                    datetime.now().isoformat(),
                ),
            )

        self.conn.commit()

    def get_note_links(self, note_id: str) -> List[dict]:
        """Get all outgoing links from a note.

        Args:
            note_id: Source note ID

        Returns:
            List of link dicts
        """
        cursor = self.conn.execute(
            """
            SELECT target_id, target_title, link_type, section, block_id, context
            FROM note_links
            WHERE source_id = ?
            ORDER BY target_title
            """,
            (note_id,),
        )

        return [dict(row) for row in cursor]

    def get_backlinks(self, note_id: str) -> List[dict]:
        """Get all backlinks (incoming links) to a note.

        Args:
            note_id: Target note ID

        Returns:
            List of backlink dicts with source note info
        """
        cursor = self.conn.execute(
            """
            SELECT source_id, source_title, link_type, section, block_id, context
            FROM note_links
            WHERE target_id = ?
            ORDER BY source_title
            """,
            (note_id,),
        )

        return [dict(row) for row in cursor]

    def get_backlink_count(self, note_id: str) -> int:
        """Get count of backlinks to a note.

        Args:
            note_id: Target note ID

        Returns:
            Number of backlinks
        """
        cursor = self.conn.execute(
            """
            SELECT COUNT(*) as count
            FROM note_links
            WHERE target_id = ?
            """,
            (note_id,),
        )

        row = cursor.fetchone()
        return row["count"] if row else 0

    def get_broken_links(self) -> List[dict]:
        """Find all broken links (links to non-existent notes).

        Returns:
            List of broken link dicts
        """
        # Get all unique target_ids from links
        cursor = self.conn.execute(
            """
            SELECT DISTINCT l.source_id, l.source_title, l.target_id, l.target_title,
                   l.link_type, l.section, l.block_id, l.context
            FROM note_links l
            LEFT JOIN notes_fts n ON l.target_id = n.file_path
                OR '/' || l.target_id || '.md.gpg' = SUBSTR(n.file_path, -LENGTH(l.target_id) - 7)
            WHERE n.file_path IS NULL
            ORDER BY l.source_title, l.target_title
            """
        )

        return [dict(row) for row in cursor]

    def remove_links_for_note(self, note_id: str):
        """Remove all links from a note.

        Args:
            note_id: Note ID to remove links for
        """
        self.conn.execute("DELETE FROM note_links WHERE source_id = ?", (note_id,))
        self.conn.commit()

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
