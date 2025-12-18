"""Main TUI Application for GPGNotes."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header

from ..config import Config
from ..index import SearchIndex
from ..storage import Storage
from .widgets.folders import FoldersPanel
from .widgets.notes_list import NotesListPanel
from .widgets.preview import PreviewPanel
from .widgets.tags import TagsPanel


class GPGNotesApp(App):
    """GPGNotes TUI Application."""

    TITLE = "GPGNotes"
    CSS_PATH = "styles/default.tcss"

    BINDINGS = [
        Binding("n", "new_note", "New", show=True),
        Binding("e", "edit_note", "Edit", show=True),
        Binding("d", "delete_note", "Delete", show=True),
        Binding("s", "search", "Search", show=True),
        Binding("y", "sync", "Sync", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("f1", "help", "Help"),
        Binding("tab", "focus_next", "Next Panel", show=False),
        Binding("shift+tab", "focus_previous", "Prev Panel", show=False),
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.config = Config()
        self.storage = Storage(self.config)
        self.index = SearchIndex(self.config)
        self._selected_note_id = None

    def compose(self) -> ComposeResult:
        """Create the app layout."""
        yield Header()
        yield Horizontal(
            Vertical(
                FoldersPanel(id="folders"),
                NotesListPanel(id="notes-list"),
                TagsPanel(id="tags"),
                id="sidebar",
            ),
            PreviewPanel(id="preview"),
            id="main-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize app on mount."""
        self.title = f"GPGNotes v{self._get_version()}"
        self.refresh_notes()

    def _get_version(self) -> str:
        """Get the app version."""
        try:
            from .. import __version__

            return __version__
        except ImportError:
            return "0.0.0"

    def refresh_notes(self) -> None:
        """Refresh the notes list."""
        notes_list = self.query_one("#notes-list", NotesListPanel)
        notes_list.refresh_notes()

        folders = self.query_one("#folders", FoldersPanel)
        folders.refresh_folders()

        tags = self.query_one("#tags", TagsPanel)
        tags.refresh_tags()

    def action_new_note(self) -> None:
        """Create a new note."""
        from .dialogs.new_note import NewNoteDialog

        self.push_screen(NewNoteDialog(), self._on_new_note_result)

    def _on_new_note_result(self, result: str | None) -> None:
        """Handle new note dialog result."""
        if result:
            self.refresh_notes()
            self.notify(f"Created: {result}", title="Note Created")

    def action_edit_note(self) -> None:
        """Edit the selected note."""
        if self._selected_note_id:
            self._edit_note(self._selected_note_id)
        else:
            self.notify("No note selected", severity="warning")

    def _edit_note(self, note_id: str) -> None:
        """Edit a note by ID."""

        from .widgets.notes_list import NotesListPanel

        notes_list = self.query_one("#notes-list", NotesListPanel)
        note_path = notes_list.get_note_path(note_id)

        if note_path:
            # Suspend app, edit in external editor, resume
            with self.suspend():
                try:
                    self.storage.edit_note(note_path)
                except Exception as e:
                    self.notify(f"Error editing: {e}", severity="error")

            self.refresh_notes()
            self._update_preview(note_id)

    def action_delete_note(self) -> None:
        """Delete the selected note."""
        if self._selected_note_id:
            from .dialogs.confirm import ConfirmDialog

            self.push_screen(
                ConfirmDialog("Delete this note?", "This action cannot be undone."),
                self._on_delete_confirm,
            )
        else:
            self.notify("No note selected", severity="warning")

    def _on_delete_confirm(self, confirmed: bool) -> None:
        """Handle delete confirmation."""
        if confirmed and self._selected_note_id:
            notes_list = self.query_one("#notes-list", NotesListPanel)
            note_path = notes_list.get_note_path(self._selected_note_id)

            if note_path:
                try:
                    note_path.unlink()
                    self.index.remove_note(note_path)
                    self.notify("Note deleted", title="Deleted")
                    self._selected_note_id = None
                    self.refresh_notes()
                    self._clear_preview()
                except Exception as e:
                    self.notify(f"Error deleting: {e}", severity="error")

    def action_search(self) -> None:
        """Open search screen."""
        from .screens.search import SearchScreen

        self.push_screen(SearchScreen(), self._on_search_result)

    def _on_search_result(self, note_id: str | None) -> None:
        """Handle search result selection."""
        if note_id:
            self._select_note(note_id)

    def action_sync(self) -> None:
        """Sync with Git."""
        self.notify("Syncing...", title="Sync")
        try:
            from ..git_sync import GitSync

            git_sync = GitSync(self.config)
            git_sync.sync("Sync from TUI")
            self.refresh_notes()
            self.notify("Sync complete", title="Sync")
        except Exception as e:
            self.notify(f"Sync failed: {e}", severity="error")

    def action_refresh(self) -> None:
        """Refresh the display."""
        self.refresh_notes()
        self.notify("Refreshed")

    def action_help(self) -> None:
        """Show help screen."""
        from .screens.help import HelpScreen

        self.push_screen(HelpScreen())

    def action_cancel(self) -> None:
        """Cancel current operation."""
        pass

    def _select_note(self, note_id: str) -> None:
        """Select a note and update preview."""
        self._selected_note_id = note_id
        self._update_preview(note_id)

    def _update_preview(self, note_id: str) -> None:
        """Update the preview panel with note content."""
        preview = self.query_one("#preview", PreviewPanel)
        notes_list = self.query_one("#notes-list", NotesListPanel)
        note_path = notes_list.get_note_path(note_id)

        if note_path:
            try:
                note = self.storage.load_note(note_path)
                preview.update_content(note)
            except Exception as e:
                preview.show_error(f"Error loading note: {e}")

    def _clear_preview(self) -> None:
        """Clear the preview panel."""
        preview = self.query_one("#preview", PreviewPanel)
        preview.clear()

    def on_notes_list_panel_note_selected(self, event) -> None:
        """Handle note selection from list."""
        self._select_note(event.note_id)

    def on_notes_list_panel_note_activated(self, event) -> None:
        """Handle note activation (Enter key) from list."""
        self._edit_note(event.note_id)

    def on_folders_panel_folder_selected(self, event) -> None:
        """Handle folder selection."""
        notes_list = self.query_one("#notes-list", NotesListPanel)
        notes_list.filter_by_folder(event.folder_name)

    def on_tags_panel_tag_selected(self, event) -> None:
        """Handle tag selection."""
        notes_list = self.query_one("#notes-list", NotesListPanel)
        notes_list.filter_by_tag(event.tag_name)

    def on_unmount(self) -> None:
        """Cleanup on unmount."""
        self.index.close()
