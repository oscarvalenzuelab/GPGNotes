"""Search index using SQLite FTS5."""

import sqlite3
from pathlib import Path
from typing import List, Tuple

from .config import Config
from .note import Note


class SearchIndex:
    """Full-text search index for notes."""

    def __init__(self, config: Config):
        """Initialize search index."""
        self.config = config
        self.db_path = config.db_file
        self.conn: sqlite3.Connection = None
        self._init_db()

    def _init_db(self):
        """Initialize database with FTS5 table."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

        # Check if table exists and has the correct schema
        try:
            cursor = self.conn.execute("SELECT is_plain FROM notes_fts LIMIT 1")
            cursor.fetchone()
        except sqlite3.OperationalError:
            # Table doesn't exist or has old schema - recreate it
            self.conn.execute("DROP TABLE IF EXISTS notes_fts")
            self.conn.commit()

        # Create FTS5 virtual table
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

        self.conn.commit()

    def add_note(self, note: Note):
        """Add or update note in index."""
        if not note.file_path:
            return

        # Delete existing entry if present
        self.remove_note(note.file_path)

        # Insert new entry
        self.conn.execute(
            """
            INSERT INTO notes_fts (title, content, tags, file_path, created, modified, is_plain)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                note.title,
                note.content,
                " ".join(note.tags),
                str(note.file_path),
                note.created.isoformat(),
                note.modified.isoformat(),
                1 if getattr(note, "is_plain", False) else 0,
            ),
        )

        self.conn.commit()

    def remove_note(self, file_path: Path):
        """Remove note from index."""
        self.conn.execute(
            """
            DELETE FROM notes_fts WHERE file_path = ?
        """,
            (str(file_path),),
        )

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
                    "is_plain": bool(row.get("is_plain", 0)),
                }
            )

        return results

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
