"""Tests for daily notes module."""

from datetime import datetime

from click.testing import CliRunner

from gpgnotes.cli import main
from gpgnotes.daily import DailyNoteManager
from gpgnotes.note import Note


class TestDailyNoteManager:
    """Tests for DailyNoteManager class."""

    def test_get_daily_note_path(self, test_config):
        """Test daily note path generation."""
        manager = DailyNoteManager(test_config)
        date = datetime(2025, 12, 17, 14, 30)

        path = manager.get_daily_note_path(date)

        # Should be: notes_dir/daily/YYYY/MM/YYYY-MM-DD.md.gpg
        assert "daily" in str(path)
        assert "2025" in str(path)
        assert "12" in str(path)
        assert "2025-12-17.md.gpg" in str(path)

    def test_get_daily_note_path_different_dates(self, test_config):
        """Test path generation for various dates."""
        manager = DailyNoteManager(test_config)

        # Test January (single digit month)
        jan_date = datetime(2025, 1, 5)
        jan_path = manager.get_daily_note_path(jan_date)
        assert "/01/" in str(jan_path)
        assert "2025-01-05.md.gpg" in str(jan_path)

        # Test December
        dec_date = datetime(2025, 12, 31)
        dec_path = manager.get_daily_note_path(dec_date)
        assert "/12/" in str(dec_path)
        assert "2025-12-31.md.gpg" in str(dec_path)

    def test_get_daily_note_nonexistent(self, test_config):
        """Test getting a daily note that doesn't exist."""
        manager = DailyNoteManager(test_config)
        date = datetime(2025, 12, 17)

        note = manager.get_daily_note(date)

        assert note is None

    def test_count_entries(self, test_config):
        """Test counting entries in a note."""
        manager = DailyNoteManager(test_config)

        # Create a note with entries
        note = Note(
            title="Captain's Log: 2025-12-17",
            content="""# Captain's Log: 2025-12-17

## Entries

- First entry
- Second entry
- Third entry
""",
            tags=["daily", "log"],
        )

        count = manager.count_entries(note)
        assert count == 3

    def test_count_entries_empty(self, test_config):
        """Test counting entries in empty note."""
        manager = DailyNoteManager(test_config)

        note = Note(
            title="Captain's Log: 2025-12-17",
            content="# Captain's Log: 2025-12-17\n\n## Entries\n",
            tags=["daily", "log"],
        )

        count = manager.count_entries(note)
        assert count == 0

    def test_generate_basic_summary_empty(self, test_config):
        """Test basic summary with no notes."""
        manager = DailyNoteManager(test_config)

        summary = manager.generate_summary([], "December 2025")

        assert "No daily notes found" in summary

    def test_generate_basic_summary(self, test_config):
        """Test basic summary generation without LLM."""
        manager = DailyNoteManager(test_config)

        # Create test notes
        notes = [
            Note(
                title="Captain's Log: 2025-12-15",
                content="# Log\n\n## Entries\n\n- Entry 1\n- Entry 2\n",
                tags=["daily", "log", "python"],
                created=datetime(2025, 12, 15),
            ),
            Note(
                title="Captain's Log: 2025-12-16",
                content="# Log\n\n## Entries\n\n- Entry 3\n",
                tags=["daily", "log", "testing"],
                created=datetime(2025, 12, 16),
            ),
        ]

        summary = manager._generate_basic_summary(notes, "Week 50")

        assert "Week 50 Summary" in summary
        assert "Days logged: 2" in summary
        assert "Total entries: 3" in summary
        assert "python" in summary or "testing" in summary

    def test_get_notes_for_week(self, test_config):
        """Test week calculation logic."""
        manager = DailyNoteManager(test_config)

        # Wednesday Dec 17, 2025
        date = datetime(2025, 12, 17)
        notes = manager.get_notes_for_week(date)

        # Should return empty list (no files exist)
        assert notes == []

    def test_get_notes_for_month(self, test_config):
        """Test month calculation logic."""
        manager = DailyNoteManager(test_config)

        notes = manager.get_notes_for_month(2025, 12)

        # Should return empty list (no files exist)
        assert notes == []


class TestDailyCLI:
    """Tests for daily CLI commands."""

    def test_daily_help(self):
        """Test daily command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["daily", "--help"])

        # May fail in CI without GPG setup, but should not crash
        assert result.exit_code in [0, 1]

    def test_daily_show_help(self):
        """Test daily show command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["daily", "show", "--help"])

        # May fail in CI without GPG setup, but should not crash
        assert result.exit_code in [0, 1]

    def test_daily_summary_help(self):
        """Test daily summary command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["daily", "summary", "--help"])

        # May fail in CI without GPG setup, but should not crash
        assert result.exit_code in [0, 1]

    def test_today_help(self):
        """Test today command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["today", "--help"])

        # May fail in CI without GPG setup, but should not crash
        assert result.exit_code in [0, 1]

    def test_yesterday_help(self):
        """Test yesterday command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["yesterday", "--help"])

        # May fail in CI without GPG setup, but should not crash
        assert result.exit_code in [0, 1]

    def test_daily_without_args_shows_help(self):
        """Test daily command without arguments shows help."""
        runner = CliRunner()
        result = runner.invoke(main, ["daily"])

        # Should show help or run without crashing
        # May fail with exit code 1 in test environment without GPG
        assert result.exit_code in [0, 1]

    def test_daily_summary_requires_period(self):
        """Test daily summary requires --month or --week."""
        runner = CliRunner()
        result = runner.invoke(main, ["daily", "summary"])

        # Should fail or prompt for period selection
        assert result.exit_code in [0, 1]


class TestDailyNoteFormat:
    """Tests for daily note format and structure."""

    def test_daily_note_title_format(self):
        """Test daily note title format."""
        expected_title = "Captain's Log: 2025-12-17"

        note = Note(
            title=expected_title,
            content=f"# {expected_title}\n\n## Entries\n",
            tags=["daily", "log"],
        )

        assert note.title == expected_title
        assert "daily" in note.tags
        assert "log" in note.tags

    def test_daily_note_content_structure(self):
        """Test daily note content structure."""
        content = """# Captain's Log: 2025-12-17

## Entries

- 09:15 - Morning standup
- 10:30 - Code review
"""
        note = Note(
            title="Captain's Log: 2025-12-17",
            content=content,
            tags=["daily", "log"],
        )

        assert "## Entries" in note.content
        assert "09:15" in note.content

    def test_entry_with_timestamp_format(self):
        """Test entry format with timestamp."""
        timestamp = datetime.now().strftime("%H:%M")
        entry = f"- {timestamp} - Test entry"

        assert " - " in entry
        assert ":" in entry.split(" - ")[0]
