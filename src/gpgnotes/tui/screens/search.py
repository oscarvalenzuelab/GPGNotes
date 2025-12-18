"""Search screen for GPGNotes TUI."""

from datetime import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView, Static

from ...config import Config
from ...index import SearchIndex


class SearchScreen(ModalScreen[str | None]):
    """Search screen for finding notes."""

    DEFAULT_CSS = """
    SearchScreen {
        align: center middle;
    }

    SearchScreen > Container {
        width: 80%;
        max-width: 100;
        height: 80%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    SearchScreen .search-title {
        text-style: bold;
        color: $secondary;
        text-align: center;
        padding-bottom: 1;
    }

    SearchScreen Input {
        margin-bottom: 1;
    }

    SearchScreen .results-label {
        color: $text-muted;
        padding: 1 0;
    }

    SearchScreen ListView {
        height: 1fr;
        border: solid $primary-darken-1;
    }

    SearchScreen ListItem {
        padding: 0 1;
    }

    SearchScreen ListItem:hover {
        background: $surface-lighten-1;
    }

    SearchScreen ListItem.-selected {
        background: $primary;
    }

    SearchScreen .hint {
        color: $text-muted;
        text-style: italic;
        dock: bottom;
        padding-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "select", "Select", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.config = Config()
        self._results = []
        self._results_by_id = {}

    def compose(self) -> ComposeResult:
        with Container():
            yield Static("🔍 Search Notes", classes="search-title")
            yield Input(placeholder="Type to search...", id="search-input")
            yield Static("Results:", classes="results-label", id="results-label")
            yield ListView(id="results-list")
            yield Static("Enter=Select  Escape=Cancel", classes="hint")

    def on_mount(self) -> None:
        """Focus the search input on mount."""
        self.query_one("#search-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        query = event.value.strip()
        if len(query) >= 2:
            self._search(query)
        else:
            self._clear_results()

    def _search(self, query: str) -> None:
        """Perform search and update results."""
        index = SearchIndex(self.config)
        try:
            self._results = index.search(query, limit=20)
        finally:
            index.close()

        self._results_by_id = {}
        list_view = self.query_one("#results-list", ListView)
        list_view.clear()

        for file_path, title, modified in self._results:
            note_id = self._extract_note_id(file_path)
            self._results_by_id[note_id] = file_path

            # Format display
            display_title = title[:50]
            if len(title) > 50:
                display_title += "..."

            mod_date = datetime.fromisoformat(modified)
            date_str = mod_date.strftime("%Y-%m-%d")

            label = f"📄 {display_title} [{date_str}]"
            list_view.append(ListItem(Label(label), id=f"result-{note_id}"))

        # Update results label
        results_label = self.query_one("#results-label", Static)
        results_label.update(f"Results: {len(self._results)} found")

    def _clear_results(self) -> None:
        """Clear search results."""
        self._results = []
        self._results_by_id = {}
        list_view = self.query_one("#results-list", ListView)
        list_view.clear()

        results_label = self.query_one("#results-label", Static)
        results_label.update("Results: (type at least 2 characters)")

    def _extract_note_id(self, file_path: str) -> str:
        """Extract note ID from file path."""
        path = Path(file_path)
        name = path.stem
        if name.endswith(".md"):
            name = name[:-3]
        return name

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle result selection."""
        item_id = event.item.id or ""
        if item_id.startswith("result-"):
            note_id = item_id[7:]  # Remove "result-" prefix
            self.dismiss(note_id)

    def action_cancel(self) -> None:
        """Cancel and close the screen."""
        self.dismiss(None)

    def action_select(self) -> None:
        """Select highlighted item."""
        list_view = self.query_one("#results-list", ListView)
        if list_view.highlighted_child:
            item_id = list_view.highlighted_child.id or ""
            if item_id.startswith("result-"):
                note_id = item_id[7:]
                self.dismiss(note_id)
