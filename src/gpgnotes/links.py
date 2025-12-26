"""Wiki-style links and backlinks for notes."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from .config import Config
from .note import Note


@dataclass
class WikiLink:
    """Represents a wiki-style link."""

    target: str  # Note title or ID
    section: Optional[str] = None  # For [[Note#section]]
    block_id: Optional[str] = None  # For [[Note^blockid]]
    alias: Optional[str] = None  # For [[Note|alias]]
    position: int = 0  # Character position in text

    @property
    def link_type(self) -> str:
        """Get the type of link."""
        if self.block_id:
            return "block"
        elif self.section:
            return "section"
        else:
            return "note"

    def __str__(self) -> str:
        """String representation of the link."""
        result = f"[[{self.target}"
        if self.section:
            result += f"#{self.section}"
        if self.block_id:
            result += f"^{self.block_id}"
        if self.alias:
            result += f"|{self.alias}"
        result += "]]"
        return result


# Wiki link pattern: [[target#section^blockid|alias]]
# All parts except target are optional
WIKI_LINK_PATTERN = re.compile(
    r"\[\["  # Opening [[
    r"([^\]#^|]+)"  # target (required) - note title or ID
    r"(?:#([^\]^|]+))?"  # section (optional) - #heading
    r"(?:\^([a-f0-9]+))?"  # block_id (optional) - ^abc123
    r"(?:\|([^\]]+))?"  # alias (optional) - |display text
    r"\]\]",  # Closing ]]
    re.MULTILINE,
)


def extract_wiki_links(content: str) -> List[WikiLink]:
    """Extract all wiki links from note content.

    Args:
        content: Note content to parse

    Returns:
        List of WikiLink objects found in content
    """
    links = []
    for match in WIKI_LINK_PATTERN.finditer(content):
        target = match.group(1).strip()
        section = match.group(2).strip() if match.group(2) else None
        block_id = match.group(3) if match.group(3) else None
        alias = match.group(4).strip() if match.group(4) else None

        links.append(
            WikiLink(
                target=target,
                section=section,
                block_id=block_id,
                alias=alias,
                position=match.start(),
            )
        )
    return links


def extract_context(content: str, position: int, chars: int = 50) -> str:
    """Extract text around a link for preview.

    Args:
        content: Full note content
        position: Character position of the link
        chars: Number of characters to extract on each side

    Returns:
        Context snippet with ellipsis
    """
    start = max(0, position - chars)
    end = min(len(content), position + chars)

    snippet = content[start:end].strip()

    # Add ellipsis if truncated
    if start > 0:
        snippet = "..." + snippet
    if end < len(content):
        snippet = snippet + "..."

    # Clean up whitespace
    snippet = " ".join(snippet.split())

    return snippet


def slugify(text: str) -> str:
    """Convert heading to URL-safe slug.

    Args:
        text: Heading text

    Returns:
        Slugified version (lowercase, hyphenated)
    """
    # Remove markdown heading markers
    text = text.lstrip("#").strip()
    # Convert to lowercase and replace spaces/special chars
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug.strip("-")


class LinkResolver:
    """Resolves wiki links to actual notes."""

    def __init__(self, config: Config):
        """Initialize link resolver.

        Args:
            config: Application configuration
        """
        self.config = config

    def resolve_link(
        self, target: str, storage=None, fuzzy: bool = True
    ) -> Optional[Note]:
        """Resolve wiki link target to actual note.

        Resolution order:
        1. Try as exact note ID (timestamp)
        2. Try as exact title match
        3. Try fuzzy title match if enabled

        Args:
            target: Note title or ID to resolve
            storage: Storage instance for loading notes
            fuzzy: Enable fuzzy matching

        Returns:
            Resolved Note or None if not found
        """
        if not storage:
            from .storage import Storage

            storage = Storage(self.config)

        # Try as ID first (timestamp format: YYYYMMDDHHmmss)
        if re.match(r"^\d{14}$", target):
            note_path = self._find_note_by_id(target)
            if note_path and note_path.exists():
                return storage.load_note(note_path)

        # Try exact title match
        from .index import SearchIndex

        index = SearchIndex(self.config)
        results = index.search(f'title:"{target}"', limit=100)

        for result in results:
            note_path = Path(result["file_path"])
            if note_path.exists():
                note = storage.load_note(note_path)
                if note.title.lower() == target.lower():
                    index.close()
                    return note

        # Try fuzzy match if enabled
        if fuzzy:
            results = index.search(target, limit=10)
            if results:
                # Get most recent match
                most_recent = max(results, key=lambda r: r.get("modified", ""))
                note_path = Path(most_recent["file_path"])
                if note_path.exists():
                    note = storage.load_note(note_path)
                    index.close()
                    return note

        index.close()
        return None

    def _find_note_by_id(self, note_id: str) -> Optional[Path]:
        """Find note file path by ID.

        Args:
            note_id: Note ID (timestamp format YYYYMMDDHHmmss)

        Returns:
            Path to note file or None
        """
        # Extract year and month from ID
        if len(note_id) < 8:
            return None

        year = note_id[:4]
        month = note_id[4:6]

        # Check both encrypted and plain versions
        base_path = self.config.notes_dir / year / month
        encrypted_path = base_path / f"{note_id}.md.gpg"
        plain_path = base_path / f"{note_id}.md"

        if encrypted_path.exists():
            return encrypted_path
        elif plain_path.exists():
            return plain_path

        return None

    def get_broken_links(self, storage=None) -> List[Tuple[Note, WikiLink]]:
        """Find all broken links across all notes.

        Args:
            storage: Storage instance

        Returns:
            List of (source_note, broken_link) tuples
        """
        if not storage:
            from .storage import Storage

            storage = Storage(self.config)

        broken = []

        # Get all notes
        from .index import SearchIndex

        index = SearchIndex(self.config)
        results = index.search("*", limit=10000)

        for result in results:
            note_path = Path(result["file_path"])
            if not note_path.exists():
                continue

            try:
                note = storage.load_note(note_path)
                links = extract_wiki_links(note.content)

                for link in links:
                    resolved = self.resolve_link(link.target, storage, fuzzy=False)
                    if not resolved:
                        broken.append((note, link))
            except Exception:
                continue

        index.close()
        return broken


class BacklinksManager:
    """Manages backlinks (incoming links) for notes."""

    def __init__(self, config: Config):
        """Initialize backlinks manager.

        Args:
            config: Application configuration
        """
        self.config = config

    def get_backlinks(
        self, note: Note, include_context: bool = True
    ) -> List[dict]:
        """Get all backlinks to a note.

        Args:
            note: Target note to find backlinks for
            include_context: Include context snippets

        Returns:
            List of backlink dicts with source note info
        """
        from .index import SearchIndex

        index = SearchIndex(self.config)

        backlinks = []
        try:
            results = index.get_backlinks(note.note_id)

            for result in results:
                backlink = {
                    "source_id": result["source_id"],
                    "source_title": result.get("source_title", ""),
                    "link_type": result.get("link_type", "note"),
                    "section": result.get("section"),
                    "block_id": result.get("block_id"),
                }

                if include_context:
                    backlink["context"] = result.get("context", "")

                backlinks.append(backlink)
        finally:
            index.close()

        return backlinks

    def get_backlink_count(self, note: Note) -> int:
        """Get count of backlinks to a note.

        Args:
            note: Target note

        Returns:
            Number of backlinks
        """
        from .index import SearchIndex

        index = SearchIndex(self.config)
        try:
            count = index.get_backlink_count(note.note_id)
        finally:
            index.close()

        return count

    def find_unlinked_mentions(self, note: Note, storage=None) -> List[dict]:
        """Find notes that mention note title but don't use wiki link.

        Args:
            note: Target note to find mentions of
            storage: Storage instance

        Returns:
            List of dicts with note info and mention context
        """
        if not storage:
            from .storage import Storage

            storage = Storage(self.config)

        from .index import SearchIndex

        index = SearchIndex(self.config)

        mentions = []
        try:
            # Search for note title in content
            results = index.search(note.title, limit=100)

            for result in results:
                note_path = Path(result["file_path"])

                # Skip the note itself
                if note_path == note.file_path:
                    continue

                if not note_path.exists():
                    continue

                try:
                    source_note = storage.load_note(note_path)

                    # Check if title appears but not as wiki link
                    content = source_note.content
                    if note.title in content:
                        # Check if it's already a wiki link
                        links = extract_wiki_links(content)
                        linked_titles = [link.target for link in links]

                        if note.title not in linked_titles:
                            # Find position of mention
                            pos = content.find(note.title)
                            context = extract_context(content, pos)

                            mentions.append(
                                {
                                    "note_id": source_note.note_id,
                                    "title": source_note.title,
                                    "context": context,
                                    "file_path": str(note_path),
                                }
                            )
                except Exception:
                    continue
        finally:
            index.close()

        return mentions
