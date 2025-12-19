"""Notes list panel widget."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Label, ListItem, ListView, Static

from ...config import Config
from ...index import SearchIndex


class NotesListPanel(Vertical):
    """Panel showing list of notes."""

    DEFAULT_CSS = """
    NotesListPanel {
        width: 100%;
        height: 1fr;
        border: solid $primary;
        padding: 0 1;
    }

    NotesListPanel > .panel-title {
        text-style: bold;
        color: $text;
        padding: 0;
    }

    NotesListPanel ListView {
        height: 1fr;
        background: transparent;
    }

    NotesListPanel ListItem {
        padding: 0;
    }

    NotesListPanel ListItem:hover {
        background: $surface-lighten-1;
    }

    NotesListPanel ListItem.-selected {
        background: $primary;
    }

    NotesListPanel .note-title {
        width: 100%;
    }

    NotesListPanel .note-meta {
        color: $text-muted;
        text-style: italic;
    }
    """

    class NoteSelected(Message):
        """Message sent when a note is selected."""

        def __init__(self, note_id: str) -> None:
            self.note_id = note_id
            super().__init__()

    class NoteActivated(Message):
        """Message sent when a note is activated (Enter)."""

        def __init__(self, note_id: str) -> None:
            self.note_id = note_id
            super().__init__()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config = Config()
        self._notes = []
        self._notes_by_id = {}
        self._current_filter = None
        self._filter_type = None  # "folder", "tag", or None

    def compose(self) -> ComposeResult:
        yield Static("📋 NOTES", classes="panel-title")
        yield ListView(id="notes-list")

    async def refresh_notes(self) -> None:
        """Refresh the notes list."""
        index = SearchIndex(self.config)
        try:
            if self._filter_type == "folder":
                if self._current_filter == "__inbox__":
                    self._notes = index.get_all_metadata(inbox=True)
                elif self._current_filter:
                    self._notes = index.get_all_metadata(
                        tag_filter=f"folder:{self._current_filter}"
                    )
                else:
                    self._notes = index.get_all_metadata()
            elif self._filter_type == "tag":
                self._notes = index.get_all_metadata(tag_filter=self._current_filter)
            else:
                self._notes = index.get_all_metadata()
        finally:
            index.close()

        self._notes_by_id = {}
        list_view = self.query_one("#notes-list", ListView)
        await list_view.clear()

        for note_meta in self._notes:
            note_id = self._extract_note_id(note_meta["file_path"])
            self._notes_by_id[note_id] = Path(note_meta["file_path"])

            # Format the display
            title = note_meta["title"][:40]
            if len(note_meta["title"]) > 40:
                title += "..."

            modified = datetime.fromisoformat(note_meta["modified"])
            date_str = modified.strftime("%m/%d")

            is_plain = note_meta.get("is_plain", False)
            icon = "📄" if is_plain else "🔒"

            label = f"{icon} {title} [{date_str}]"
            list_view.append(ListItem(Label(label), id=f"note-{note_id}"))

        # Update title with count
        title_widget = self.query_one(".panel-title", Static)
        filter_text = ""
        if self._filter_type == "folder":
            if self._current_filter == "__inbox__":
                filter_text = " (Inbox)"
            elif self._current_filter:
                filter_text = f" ({self._current_filter})"
        elif self._filter_type == "tag":
            filter_text = f" (#{self._current_filter})"

        title_widget.update(f"📋 NOTES{filter_text} [{len(self._notes)}]")

    def _extract_note_id(self, file_path: str) -> str:
        """Extract note ID from file path."""
        path = Path(file_path)
        name = path.stem
        if name.endswith(".md"):
            name = name[:-3]
        return name

    async def filter_by_folder(self, folder_name: str) -> None:
        """Filter notes by folder."""
        self._filter_type = "folder" if folder_name else None
        self._current_filter = folder_name if folder_name else None
        await self.refresh_notes()

    async def filter_by_tag(self, tag_name: str) -> None:
        """Filter notes by tag."""
        self._filter_type = "tag" if tag_name else None
        self._current_filter = tag_name if tag_name else None
        await self.refresh_notes()

    async def clear_filter(self) -> None:
        """Clear any active filter."""
        self._filter_type = None
        self._current_filter = None
        await self.refresh_notes()

    def get_note_path(self, note_id: str) -> Optional[Path]:
        """Get the file path for a note ID."""
        return self._notes_by_id.get(note_id)

    def get_note_metadata(self, note_id: str) -> Optional[dict]:
        """Get metadata for a note by ID (from index, no decryption)."""
        for note_meta in self._notes:
            if self._extract_note_id(note_meta["file_path"]) == note_id:
                return note_meta
        return None

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle note selection."""
        item_id = event.item.id or ""
        if item_id.startswith("note-"):
            note_id = item_id[5:]  # Remove "note-" prefix
            self.post_message(self.NoteSelected(note_id))

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle note highlight (cursor movement)."""
        if event.item:
            item_id = event.item.id or ""
            if item_id.startswith("note-"):
                note_id = item_id[5:]
                self.post_message(self.NoteSelected(note_id))
