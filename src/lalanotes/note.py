"""Note model and operations."""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import frontmatter
from slugify import slugify


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
    ):
        """Initialize a note."""
        self.title = title
        self.content = content
        self.tags = tags or []
        self.created = created or datetime.now()
        self.modified = modified or datetime.now()
        self.file_path = file_path

    @classmethod
    def from_markdown(cls, content: str, file_path: Optional[Path] = None) -> "Note":
        """Create note from markdown content with frontmatter."""
        post = frontmatter.loads(content)

        return cls(
            title=post.get("title", "Untitled"),
            content=post.content,
            tags=post.get("tags", []),
            created=post.get("created", datetime.now()),
            modified=post.get("modified", datetime.now()),
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
        """Generate filename based on date and title."""
        date = date or self.created
        slug = slugify(self.title)
        return f"{date.strftime('%Y-%m-%d')}-{slug}.md.gpg"

    def get_relative_path(self, date: Optional[datetime] = None) -> Path:
        """Get relative path for note (YYYY/MM/filename)."""
        date = date or self.created
        year = date.strftime("%Y")
        month = date.strftime("%m")
        filename = self.generate_filename(date)

        return Path(year) / month / filename

    def update_modified(self):
        """Update the modified timestamp."""
        self.modified = datetime.now()
