"""Tests for note module."""

import pytest
from datetime import datetime
from pathlib import Path
from gpgnotes.note import Note


def test_note_creation():
    """Test creating a note."""
    note = Note(title="Test Note", content="This is a test")
    assert note.title == "Test Note"
    assert note.content == "This is a test"
    assert note.tags == []
    assert isinstance(note.created, datetime)
    assert isinstance(note.modified, datetime)


def test_note_with_tags():
    """Test creating a note with tags."""
    note = Note(title="Tagged Note", content="Content", tags=["python", "testing"])
    assert note.tags == ["python", "testing"]


def test_note_to_markdown():
    """Test converting note to markdown."""
    note = Note(title="Test", content="Content here")
    markdown = note.to_markdown()

    assert "title: Test" in markdown
    assert "Content here" in markdown


def test_note_from_markdown():
    """Test creating note from markdown."""
    markdown = """---
title: Test Note
tags:
  - tag1
  - tag2
created: 2025-01-15T10:00:00
modified: 2025-01-15T10:30:00
---

This is the content.
"""
    note = Note.from_markdown(markdown)

    assert note.title == "Test Note"
    assert note.content.strip() == "This is the content."
    assert note.tags == ["tag1", "tag2"]


def test_note_generate_filename():
    """Test filename generation."""
    note = Note(title="My Test Note")
    filename = note.generate_filename()

    assert filename.endswith(".md.gpg")
    # Filename should be timestamp-based: YYYYMMDDHHmmss.md.gpg
    timestamp_part = filename.replace(".md.gpg", "")
    assert len(timestamp_part) == 14  # YYYYMMDDHHmmss is 14 characters
    assert timestamp_part.isdigit()
    assert timestamp_part.startswith(note.created.strftime('%Y%m%d'))


def test_note_get_relative_path():
    """Test relative path generation."""
    created = datetime(2025, 12, 15, 10, 30)
    note = Note(title="Test", created=created)
    rel_path = note.get_relative_path()

    assert str(rel_path).startswith("2025/12/")
    assert str(rel_path).endswith(".md.gpg")


def test_note_update_modified():
    """Test updating modified timestamp."""
    note = Note(title="Test")
    original_modified = note.modified

    import time
    time.sleep(0.01)  # Small delay

    note.update_modified()
    assert note.modified > original_modified
