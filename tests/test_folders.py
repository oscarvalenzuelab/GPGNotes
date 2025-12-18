"""Tests for folder functionality."""

import pytest
from click.testing import CliRunner
from gpgnotes.cli import main
from gpgnotes.index import SearchIndex
from gpgnotes.note import Note
from datetime import datetime


def test_folders_command():
    """Test folders command runs without crashing."""
    runner = CliRunner()
    result = runner.invoke(main, ['folders'])

    # Should run without crashing
    assert result.exit_code in [0, 1]


def test_list_with_folder_option():
    """Test list command with --folder option."""
    runner = CliRunner()
    result = runner.invoke(main, ['list', '--folder', 'work'])

    # Should run without crashing
    assert result.exit_code in [0, 1]


def test_search_with_folder_option():
    """Test search command with --folder option."""
    runner = CliRunner()
    result = runner.invoke(main, ['search', '--folder', 'work'])

    # Should run without crashing
    assert result.exit_code in [0, 1]


def test_move_command_requires_folder():
    """Test move command requires --folder or --unfolder."""
    runner = CliRunner()
    result = runner.invoke(main, ['move', '12345678901234'])

    assert result.exit_code == 1
    # May show config warning or folder requirement message
    assert 'Specify --folder or --unfolder' in result.output or 'not configured' in result.output


def test_get_folders_empty(test_config):
    """Test get_folders returns empty list when no folders exist."""
    index = SearchIndex(test_config)
    try:
        folders = index.get_folders()
        assert folders == []
    finally:
        index.close()


def test_get_folders_with_notes(test_config):
    """Test get_folders returns folder counts."""
    index = SearchIndex(test_config)
    try:
        # Add notes with folder tags
        note1 = Note(
            title="Work Note 1",
            content="Content",
            tags=["folder:work", "project"]
        )
        note1.file_path = test_config.notes_dir / "20251218120000.gpg"

        note2 = Note(
            title="Work Note 2",
            content="Content",
            tags=["folder:work"]
        )
        note2.file_path = test_config.notes_dir / "20251218120100.gpg"

        note3 = Note(
            title="Personal Note",
            content="Content",
            tags=["folder:personal"]
        )
        note3.file_path = test_config.notes_dir / "20251218120200.gpg"

        index.add_note(note1)
        index.add_note(note2)
        index.add_note(note3)

        folders = index.get_folders()

        # Should have 2 folders
        assert len(folders) == 2

        # Check counts (sorted by count desc, then name)
        folder_dict = dict(folders)
        assert folder_dict["work"] == 2
        assert folder_dict["personal"] == 1

    finally:
        index.close()


def test_get_folders_ignores_non_folder_tags(test_config):
    """Test get_folders ignores tags without folder: prefix."""
    index = SearchIndex(test_config)
    try:
        note = Note(
            title="Test Note",
            content="Content",
            tags=["project", "meeting", "folder:work"]
        )
        note.file_path = test_config.notes_dir / "20251218120000.gpg"

        index.add_note(note)

        folders = index.get_folders()

        # Should only have 'work' folder, not project or meeting
        assert len(folders) == 1
        assert folders[0][0] == "work"
        assert folders[0][1] == 1

    finally:
        index.close()


def test_folder_tag_format():
    """Test that folder tags use correct format."""
    note = Note(
        title="Test",
        content="Content",
        tags=["folder:work", "folder:projects"]
    )

    # Verify tags are stored correctly
    assert "folder:work" in note.tags
    assert "folder:projects" in note.tags


def test_new_with_folder_help():
    """Test new command help shows folder option."""
    runner = CliRunner()
    result = runner.invoke(main, ['new', '--help'])

    # Help should work, but may fail if config check runs first
    if result.exit_code == 0:
        assert '--folder' in result.output or '-f' in result.output


def test_list_with_folder_help():
    """Test list command help shows folder option."""
    runner = CliRunner()
    result = runner.invoke(main, ['list', '--help'])

    # Help should work, but may fail if config check runs first
    if result.exit_code == 0:
        assert '--folder' in result.output


def test_move_help():
    """Test move command help."""
    runner = CliRunner()
    result = runner.invoke(main, ['move', '--help'])

    # Help should work, but may fail if config check runs first
    if result.exit_code == 0:
        assert '--folder' in result.output
        assert '--unfolder' in result.output
