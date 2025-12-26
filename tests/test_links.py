"""Tests for wiki-style links functionality."""

import pytest
from pathlib import Path
from datetime import datetime

from gpgnotes.links import (
    WikiLink,
    extract_wiki_links,
    extract_context,
    slugify,
    LinkResolver,
    BacklinksManager,
)
from gpgnotes.note import Note
from gpgnotes.config import Config
from gpgnotes.storage import Storage
from gpgnotes.index import SearchIndex


class TestWikiLink:
    """Test WikiLink dataclass."""

    def test_wiki_link_creation(self):
        """Test creating a WikiLink."""
        link = WikiLink(target="Note Title")
        assert link.target == "Note Title"
        assert link.section is None
        assert link.block_id is None
        assert link.alias is None

    def test_wiki_link_with_section(self):
        """Test WikiLink with section."""
        link = WikiLink(target="Note", section="Heading")
        assert link.link_type == "section"
        assert str(link) == "[[Note#Heading]]"

    def test_wiki_link_with_block(self):
        """Test WikiLink with block ID."""
        link = WikiLink(target="Note", block_id="abc123")
        assert link.link_type == "block"
        assert str(link) == "[[Note^abc123]]"

    def test_wiki_link_with_alias(self):
        """Test WikiLink with alias."""
        link = WikiLink(target="Note Title", alias="custom text")
        assert str(link) == "[[Note Title|custom text]]"


class TestExtractWikiLinks:
    """Test wiki link extraction from content."""

    def test_extract_basic_link(self):
        """Test extracting basic wiki link."""
        content = "This is a [[Test Note]] link."
        links = extract_wiki_links(content)

        assert len(links) == 1
        assert links[0].target == "Test Note"
        assert links[0].section is None
        assert links[0].block_id is None

    def test_extract_multiple_links(self):
        """Test extracting multiple links."""
        content = "Link to [[Note 1]] and [[Note 2]] and [[Note 3]]."
        links = extract_wiki_links(content)

        assert len(links) == 3
        assert [l.target for l in links] == ["Note 1", "Note 2", "Note 3"]

    def test_extract_link_with_section(self):
        """Test extracting link with section."""
        content = "See [[Project Plan#Timeline]] for details."
        links = extract_wiki_links(content)

        assert len(links) == 1
        assert links[0].target == "Project Plan"
        assert links[0].section == "Timeline"
        assert links[0].link_type == "section"

    def test_extract_link_with_block(self):
        """Test extracting link with block ID."""
        content = "As mentioned in [[Meeting Notes^abc123]]."
        links = extract_wiki_links(content)

        assert len(links) == 1
        assert links[0].target == "Meeting Notes"
        assert links[0].block_id == "abc123"
        assert links[0].link_type == "block"

    def test_extract_link_with_alias(self):
        """Test extracting link with alias."""
        content = "Check [[Project Alpha|the main project]] docs."
        links = extract_wiki_links(content)

        assert len(links) == 1
        assert links[0].target == "Project Alpha"
        assert links[0].alias == "the main project"

    def test_extract_complex_link(self):
        """Test extracting complex link with section and alias."""
        content = "See [[Note#Section|custom text]] here."
        links = extract_wiki_links(content)

        assert len(links) == 1
        assert links[0].target == "Note"
        assert links[0].section == "Section"
        assert links[0].alias == "custom text"

    def test_extract_no_links(self):
        """Test content with no links."""
        content = "This has no wiki links at all."
        links = extract_wiki_links(content)

        assert len(links) == 0

    def test_extract_link_position(self):
        """Test link position tracking."""
        content = "Start [[Link1]] middle [[Link2]] end."
        links = extract_wiki_links(content)

        assert links[0].position < links[1].position


class TestExtractContext:
    """Test context extraction."""

    def test_extract_context_middle(self):
        """Test extracting context from middle of text."""
        content = "The quick brown fox jumps over the lazy dog."
        position = content.find("jumps")
        context = extract_context(content, position, chars=10)

        assert "fox jumps over" in context

    def test_extract_context_start(self):
        """Test extracting context from start of text."""
        content = "Start of text with some content."
        context = extract_context(content, 0, chars=10)

        assert context.startswith("Start")
        assert not context.startswith("...")

    def test_extract_context_end(self):
        """Test extracting context from end of text."""
        content = "Some content at the end."
        position = len(content) - 5
        context = extract_context(content, position, chars=10)

        assert context.endswith("end.")
        assert not context.endswith("...")


class TestSlugify:
    """Test heading slugification."""

    def test_slugify_basic(self):
        """Test basic slugification."""
        assert slugify("## My Heading") == "my-heading"

    def test_slugify_special_chars(self):
        """Test slugification with special characters."""
        assert slugify("# Hello, World!") == "hello-world"

    def test_slugify_multiple_spaces(self):
        """Test slugification with multiple spaces."""
        assert slugify("### Multiple   Spaces   Here") == "multiple-spaces-here"

    def test_slugify_mixed_case(self):
        """Test slugification with mixed case."""
        assert slugify("CamelCase Title") == "camelcase-title"


class TestLinkResolver:
    """Test link resolution."""

    def test_resolve_by_id(self, tmp_path):
        """Test resolving link by note ID."""
        config = Config(tmp_path)
        config.ensure_dirs()

        storage = Storage(config)
        resolver = LinkResolver(config)

        # Create a note
        note = Note(
            title="Test Note",
            content="Test content",
            created=datetime(2025, 1, 1, 10, 0, 0),
        )
        note.file_path = config.notes_dir / note.get_relative_path()
        note.file_path.parent.mkdir(parents=True, exist_ok=True)
        storage.save_plain_note(note)

        # Resolve by ID
        resolved = resolver.resolve_link(note.note_id, storage, fuzzy=False)
        assert resolved is not None
        assert resolved.title == "Test Note"

    def test_resolve_by_title(self, tmp_path):
        """Test resolving link by exact title."""
        config = Config(tmp_path)
        config.ensure_dirs()

        storage = Storage(config)
        index = SearchIndex(config)
        resolver = LinkResolver(config)

        # Create and index a note
        note = Note(title="Project Alpha", content="Content")
        note.file_path = config.notes_dir / note.get_relative_path()
        note.file_path.parent.mkdir(parents=True, exist_ok=True)
        storage.save_plain_note(note)
        index.add_note(note)

        # Resolve by title
        resolved = resolver.resolve_link("Project Alpha", storage, fuzzy=False)
        assert resolved is not None
        assert resolved.title == "Project Alpha"

        index.close()

    def test_resolve_fuzzy_match(self, tmp_path):
        """Test fuzzy link resolution."""
        config = Config(tmp_path)
        config.ensure_dirs()

        storage = Storage(config)
        index = SearchIndex(config)
        resolver = LinkResolver(config)

        # Create a note
        note = Note(title="Important Meeting Notes", content="Content")
        note.file_path = config.notes_dir / note.get_relative_path()
        note.file_path.parent.mkdir(parents=True, exist_ok=True)
        storage.save_plain_note(note)
        index.add_note(note)

        # Fuzzy match should find it
        resolved = resolver.resolve_link("meeting", storage, fuzzy=True)
        assert resolved is not None
        assert "Meeting" in resolved.title

        index.close()

    def test_resolve_nonexistent(self, tmp_path):
        """Test resolving nonexistent link."""
        config = Config(tmp_path)
        config.ensure_dirs()

        storage = Storage(config)
        resolver = LinkResolver(config)

        resolved = resolver.resolve_link("Nonexistent Note", storage, fuzzy=False)
        assert resolved is None


class TestBacklinksManager:
    """Test backlinks management."""

    def test_get_backlinks(self, tmp_path):
        """Test getting backlinks for a note."""
        from datetime import datetime, timedelta

        config = Config(tmp_path)
        config.ensure_dirs()

        storage = Storage(config)
        index = SearchIndex(config)
        manager = BacklinksManager(config)

        base_time = datetime(2025, 1, 1, 10, 0, 0)

        # Create target note
        target = Note(title="Target Note", content="Target content", created=base_time)
        target.file_path = config.notes_dir / target.get_relative_path()
        target.file_path.parent.mkdir(parents=True, exist_ok=True)
        storage.save_plain_note(target)
        index.add_note(target)

        # Create source note with link
        source = Note(
            title="Source Note",
            content="Link to [[Target Note]] here.",
            created=base_time + timedelta(seconds=1)
        )
        source.file_path = config.notes_dir / source.get_relative_path()
        source.file_path.parent.mkdir(parents=True, exist_ok=True)
        storage.save_plain_note(source)
        index.add_note(source)

        # Re-index source links to ensure they're properly resolved
        index.index_note_links(source)

        # Get backlinks
        backlinks = manager.get_backlinks(target)
        assert len(backlinks) == 1
        assert backlinks[0]["source_title"] == "Source Note"

        index.close()

    def test_get_backlink_count(self, tmp_path):
        """Test getting backlink count."""
        from datetime import datetime, timedelta

        config = Config(tmp_path)
        config.ensure_dirs()

        storage = Storage(config)
        index = SearchIndex(config)
        manager = BacklinksManager(config)

        base_time = datetime(2025, 1, 1, 10, 0, 0)

        # Create target note
        target = Note(title="Popular Note", content="Content", created=base_time)
        target.file_path = config.notes_dir / target.get_relative_path()
        target.file_path.parent.mkdir(parents=True, exist_ok=True)
        storage.save_plain_note(target)
        index.add_note(target)

        # Create multiple source notes
        for i in range(3):
            source = Note(
                title=f"Source {i}",
                content=f"Link to [[Popular Note]].",
                created=base_time + timedelta(seconds=i+1)
            )
            source.file_path = config.notes_dir / source.get_relative_path()
            source.file_path.parent.mkdir(parents=True, exist_ok=True)
            storage.save_plain_note(source)
            index.add_note(source)

        # Check count
        count = manager.get_backlink_count(target)
        assert count == 3

        index.close()

    def test_find_unlinked_mentions(self, tmp_path):
        """Test finding unlinked mentions."""
        from datetime import datetime, timedelta

        config = Config(tmp_path)
        config.ensure_dirs()

        storage = Storage(config)
        index = SearchIndex(config)
        manager = BacklinksManager(config)

        base_time = datetime(2025, 1, 1, 10, 0, 0)

        # Create target note
        target = Note(title="Important Topic", content="Content", created=base_time)
        target.file_path = config.notes_dir / target.get_relative_path()
        target.file_path.parent.mkdir(parents=True, exist_ok=True)
        storage.save_plain_note(target)
        index.add_note(target)

        # Create note with unlinked mention
        mention = Note(
            title="Discussion",
            content="We talked about Important Topic today.",
            created=base_time + timedelta(seconds=1)
        )
        mention.file_path = config.notes_dir / mention.get_relative_path()
        mention.file_path.parent.mkdir(parents=True, exist_ok=True)
        storage.save_plain_note(mention)
        index.add_note(mention)

        # Find unlinked mentions
        mentions = manager.find_unlinked_mentions(target, storage)
        assert len(mentions) == 1
        assert mentions[0]["title"] == "Discussion"
        assert "Important Topic" in mentions[0]["context"]

        index.close()
