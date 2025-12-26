"""Test that plain note save/load roundtrip preserves content."""

from datetime import datetime
from pathlib import Path

from gpgnotes.config import Config
from gpgnotes.links import extract_wiki_links
from gpgnotes.note import Note
from gpgnotes.storage import Storage


def test_plain_note_save_load_roundtrip(tmp_path):
    """Test that saving and loading a plain note preserves all content."""
    config = Config(tmp_path)
    config.ensure_dirs()
    storage = Storage(config)

    # Create a note with wiki links
    original_content = """# Test Note

## Section 1
This has a [[Wiki Link]] in it.

## Section 2
And another [[Second Link|with alias]].
"""

    note = Note(
        title="Test Note",
        content=original_content,
        tags=["test"],
        created=datetime(2025, 1, 1, 10, 0, 0),
    )

    # Set file path
    note.file_path = config.notes_dir / note.get_relative_path()
    note.file_path.parent.mkdir(parents=True, exist_ok=True)

    # Save
    saved_path = storage.save_plain_note(note)

    # Verify file exists
    assert saved_path.exists()

    # Read raw file to verify content was saved
    raw_content = saved_path.read_text()
    assert len(raw_content) > 0
    assert "[[Wiki Link]]" in raw_content
    assert "[[Second Link|with alias]]" in raw_content

    # Load note back
    loaded_note = storage.load_note(saved_path)

    # Verify all fields preserved
    assert loaded_note.title == "Test Note"
    assert loaded_note.tags == ["test"]
    assert loaded_note.created == datetime(2025, 1, 1, 10, 0, 0)

    # Most importantly: verify content preserved
    # Note: frontmatter library strips trailing newline, so we compare with rstrip
    assert loaded_note.content.rstrip() == original_content.rstrip(), f"Content mismatch!\nOriginal: {repr(original_content)}\nLoaded: {repr(loaded_note.content)}"

    # Verify wiki links are preserved
    assert "[[Wiki Link]]" in loaded_note.content
    assert "[[Second Link|with alias]]" in loaded_note.content

    # Verify wiki links can be extracted
    links = extract_wiki_links(loaded_note.content)
    assert len(links) == 2
    assert links[0].target == "Wiki Link"
    assert links[1].target == "Second Link"
    assert links[1].alias == "with alias"
