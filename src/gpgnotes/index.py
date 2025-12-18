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

        # Create indexes for efficient queries (safe to run multiple times)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_todos_note_path ON todos(note_path)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_todos_completed ON todos(completed)
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
            INSERT INTO notes_fts (title, content, tags, file_path, created, modified, is_plain)
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

    def remove_note(self, file_path: Path):
        """Remove note from index."""
        # Try to match both absolute and as-is paths
        abs_path = str(file_path.resolve())
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

    def search(self, query: str, limit: int = 50) -> List[Tuple[str, float]]:
        """
        Search notes using FTS5.

        Returns list of (file_path, rank) tuples.
        """
        # Sanitize query for FTS5 by escaping special characters
        # Wrap in quotes to make it a phrase search and avoid syntax errors
        sanitized_query = query.replace('"', '""')  # Escape quotes
        fts_query = f'"{sanitized_query}"'

        cursor = self.conn.execute(
            """
            SELECT file_path, rank
            FROM notes_fts
            WHERE notes_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """,
            (fts_query, limit),
        )

        return [(row["file_path"], row["rank"]) for row in cursor]

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
        self, sort_by: str = "modified", limit: int = None, tag_filter: str = None
    ) -> List[dict]:
        """
        Get metadata for all notes without decryption.

        Args:
            sort_by: Sort field ('modified', 'created', or 'title')
            limit: Maximum number of results (None for all)
            tag_filter: Filter by tag (None for all notes)

        Returns:
            List of dicts with keys: file_path, title, tags, created, modified, is_plain
        """
        # Build query
        query = "SELECT file_path, title, tags, created, modified, is_plain FROM notes_fts"

        # Add tag filter if specified
        params = []
        if tag_filter:
            query += " WHERE tags MATCH ?"
            params.append(f'"{tag_filter}"')

        # Add sorting
        if sort_by == "modified":
            query += " ORDER BY modified DESC"
        elif sort_by == "created":
            query += " ORDER BY created DESC"
        elif sort_by == "title":
            query += " ORDER BY title COLLATE NOCASE"

        # Add limit if specified
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor = self.conn.execute(query, params)

        results = []
        for row in cursor:
            results.append(
                {
                    "file_path": row["file_path"],
                    "title": row["title"],
                    "tags": row["tags"].split() if row["tags"] else [],
                    "created": row["created"],
                    "modified": row["modified"],
                    "is_plain": bool(row["is_plain"]) if "is_plain" in row.keys() else False,
                }
            )

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
                        folder_counts[folder_name] = folder_counts.get(folder_name, 0) + 1

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
