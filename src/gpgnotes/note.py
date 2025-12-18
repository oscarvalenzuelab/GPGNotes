"""Note model and operations."""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import frontmatter


class Note:
    """Represents a note with metadata."""

    def __init__(
        self,
        title: str,
        content: str = "",
        tags: Optional[List[str]] = None,
        created: Optional[datetime] = None,
        modified: Optional[datetime] = None,
        file_path: Optional[Path] = None,
        is_plain: bool = False,
    ):
        """Initialize a note."""
        self.title = title
        self.content = content
        self.tags = tags or []
        self.created = created or datetime.now()
        self.modified = modified or datetime.now()
        self.file_path = file_path
        self.is_plain = is_plain

    @classmethod
    def from_markdown(cls, content: str, file_path: Optional[Path] = None) -> "Note":
        """Create note from markdown content with frontmatter."""
        post = frontmatter.loads(content)

        # Parse dates from ISO format strings if needed
        created = post.get("created", datetime.now())
        if isinstance(created, str):
            created = datetime.fromisoformat(created)

        modified = post.get("modified", datetime.now())
        if isinstance(modified, str):
            modified = datetime.fromisoformat(modified)

        return cls(
            title=post.get("title", "Untitled"),
            content=post.content,
            tags=post.get("tags", []),
            created=created,
            modified=modified,
            file_path=file_path,
        )

    def to_markdown(self) -> str:
        """Convert note to markdown with frontmatter."""
        post = frontmatter.Post(self.content)
        post["title"] = self.title
        post["tags"] = self.tags
        post["created"] = self.created.isoformat()
        post["modified"] = self.modified.isoformat()

        return frontmatter.dumps(post)

    def generate_filename(self, date: Optional[datetime] = None) -> str:
        """Generate filename based on timestamp."""
        date = date or self.created
        # Use timestamp as ID: YYYYMMDDHHmmss
        timestamp = date.strftime("%Y%m%d%H%M%S")
        return f"{timestamp}.md.gpg"

    def get_relative_path(self, date: Optional[datetime] = None) -> Path:
        """Get relative path for note (YYYY/MM/filename)."""
        date = date or self.created
        year = date.strftime("%Y")
        month = date.strftime("%m")
        filename = self.generate_filename(date)

        return Path(year) / month / filename

    @property
    def note_id(self) -> str:
        """Get note ID from filename or created timestamp."""
        if self.file_path:
            # Extract ID from filename (remove .md.gpg)
            return self.file_path.stem.replace(".md", "")
        # Fallback to timestamp from created date
        return self.created.strftime("%Y%m%d%H%M%S")

    @staticmethod
    def extract_id_from_path(file_path: Path) -> str:
        """Extract note ID from file path."""
        # Remove .md.gpg extension to get the timestamp ID
        return file_path.stem.replace(".md", "")

    def update_modified(self):
        """Update the modified timestamp."""
        self.modified = datetime.now()
