"""Daily notes (Captain's Log) management."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from .config import Config
from .index import SearchIndex
from .note import Note
from .storage import Storage


class DailyNoteManager:
    """Manage daily notes with quick entries and summaries."""

    def __init__(self, config: Config):
        """Initialize daily note manager."""
        self.config = config
        self.storage = Storage(config)
        self.notes_dir = config.notes_dir

    def get_daily_note_path(self, date: datetime) -> Path:
        """Get path for daily note: daily/YYYY/MM/YYYY-MM-DD.md.gpg"""
        year = date.strftime("%Y")
        month = date.strftime("%m")
        filename = f"{date.strftime('%Y-%m-%d')}.md.gpg"
        return self.notes_dir / "daily" / year / month / filename

    def get_daily_note(self, date: datetime) -> Optional[Note]:
        """Get daily note for a specific date, or None if doesn't exist."""
        path = self.get_daily_note_path(date)
        if path.exists():
            return self.storage.load_note(path)
        return None

    def get_or_create_daily_note(self, date: datetime) -> Note:
        """Get daily note for date, create if doesn't exist."""
        existing = self.get_daily_note(date)
        if existing:
            return existing

        # Create new daily note
        date_str = date.strftime("%Y-%m-%d")
        title = f"Captain's Log: {date_str}"
        content = f"# Captain's Log: {date_str}\n\n## Entries\n"

        note = Note(
            title=title,
            content=content,
            tags=["daily", "log"],
            created=date.replace(hour=0, minute=0, second=0, microsecond=0),
        )

        # Save to the daily-specific path
        path = self.get_daily_note_path(date)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Use storage's encryption directly
        markdown_content = note.to_markdown()
        from .llm import sanitize_for_gpg

        markdown_content = sanitize_for_gpg(markdown_content)
        self.storage.encryption.encrypt(markdown_content, path)

        note.file_path = path

        # Index the note
        index = SearchIndex(self.config)
        index.add_note(note)
        index.close()

        return note

    def append_entry(self, note: Note, entry: str, with_time: bool = False) -> Note:
        """Append an entry to the daily note."""
        # Format entry with optional timestamp
        if with_time:
            timestamp = datetime.now().strftime("%H:%M")
            formatted_entry = f"- {timestamp} - {entry}"
        else:
            formatted_entry = f"- {entry}"

        # Append to content
        note.content = note.content.rstrip() + f"\n{formatted_entry}\n"
        note.update_modified()

        # Save the updated note
        path = note.file_path or self.get_daily_note_path(datetime.now())
        markdown_content = note.to_markdown()
        from .llm import sanitize_for_gpg

        markdown_content = sanitize_for_gpg(markdown_content)
        self.storage.encryption.encrypt(markdown_content, path)

        # Update index
        index = SearchIndex(self.config)
        index.add_note(note)
        index.close()

        return note

    def get_notes_for_period(self, start: datetime, end: datetime) -> List[Note]:
        """Get all daily notes in a date range."""
        notes = []
        current = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = end.replace(hour=23, minute=59, second=59)

        while current <= end:
            note = self.get_daily_note(current)
            if note:
                notes.append(note)
            current += timedelta(days=1)

        return notes

    def get_notes_for_month(self, year: int, month: int) -> List[Note]:
        """Get all daily notes for a specific month."""
        start = datetime(year, month, 1)
        # Get last day of month
        if month == 12:
            end = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = datetime(year, month + 1, 1) - timedelta(days=1)
        return self.get_notes_for_period(start, end)

    def get_notes_for_week(self, date: datetime) -> List[Note]:
        """Get all daily notes for the week containing the given date."""
        # Get Monday of the week
        start = date - timedelta(days=date.weekday())
        end = start + timedelta(days=6)
        return self.get_notes_for_period(start, end)

    def generate_summary(self, notes: List[Note], period_type: str) -> str:
        """Generate summary from daily notes.

        Uses LLM if configured, otherwise returns basic stats.
        """
        if not notes:
            return f"No daily notes found for {period_type}."

        # Try LLM summary first
        provider_name = self.config.get("llm_provider")
        if provider_name:
            try:
                return self._generate_llm_summary(notes, period_type)
            except Exception:
                # Fall back to basic summary on error
                pass

        # Basic stats fallback
        return self._generate_basic_summary(notes, period_type)

    def _generate_llm_summary(self, notes: List[Note], period_type: str) -> str:
        """Generate LLM-powered summary."""
        from .llm import get_provider

        provider_name = self.config.get("llm_provider")
        api_key = None
        if provider_name != "ollama":
            api_key = self.config.get_secret(f"{provider_name}_api_key")

        model = self.config.get("llm_model") or None
        provider = get_provider(provider_name, api_key=api_key, model=model)

        # Combine all notes
        combined = "\n\n".join([f"## {n.title}\n{n.content}" for n in notes])

        instructions = f"""Summarize these daily log entries for {period_type}.
Include:
- Key accomplishments and activities
- Common themes or patterns
- Notable entries worth highlighting

Format as a concise summary with bullet points."""

        return provider.enhance(combined, instructions)

    def _generate_basic_summary(self, notes: List[Note], period_type: str) -> str:
        """Generate basic stats summary (no LLM)."""
        # Count entries (lines starting with "- ")
        total_entries = 0
        for note in notes:
            total_entries += note.content.count("\n- ")

        # Collect all tags
        all_tags = set()
        for note in notes:
            all_tags.update(note.tags)
        # Remove default tags
        all_tags.discard("daily")
        all_tags.discard("log")

        # Date range
        dates = [n.created.date() for n in notes]
        start_date = min(dates)
        end_date = max(dates)

        summary = f"""## {period_type} Summary

**Statistics:**
- Days logged: {len(notes)}
- Total entries: {total_entries}
- Date range: {start_date} to {end_date}
"""

        if all_tags:
            summary += f"- Tags used: {', '.join(sorted(all_tags))}\n"

        summary += """
---
*Tip: Configure an LLM provider for AI-generated insights:*
`notes config --llm-provider openai --llm-key YOUR_KEY`
"""

        return summary

    def count_entries(self, note: Note) -> int:
        """Count the number of entries in a daily note."""
        return note.content.count("\n- ")
