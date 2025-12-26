"""Backlinks panel widget for displaying incoming links."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Label, ListItem, ListView, Static


class BacklinksPanel(Vertical):
    """Panel showing backlinks to the current note."""

    DEFAULT_CSS = """
    BacklinksPanel {
        height: auto;
        max-height: 30%;
        border: solid $primary;
        padding: 1;
    }

    BacklinksPanel > Label {
        text-style: bold;
        color: $secondary;
        padding-bottom: 1;
    }

    BacklinksPanel ListView {
        height: auto;
        max-height: 20;
    }

    BacklinksPanel .empty-message {
        color: $text-muted;
        text-style: italic;
        padding: 1 0;
    }
    """

    class BacklinkSelected(Message):
        """Message sent when a backlink is selected."""

        def __init__(self, note_id: str):
            self.note_id = note_id
            super().__init__()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_note_id = None

    def compose(self) -> ComposeResult:
        yield Label("📎 Backlinks")
        yield Static("No note selected", classes="empty-message")

    async def update_backlinks(self, note_id: str) -> None:
        """Update backlinks for the given note.

        Args:
            note_id: ID of note to show backlinks for
        """
        self._current_note_id = note_id

        # Remove old content
        await self.query("ListView, .empty-message").remove()

        # Get backlinks from index
        try:
            from ...config import Config
            from ...index import SearchIndex

            config = Config()
            index = SearchIndex(config)

            try:
                backlinks = index.get_backlinks(note_id)
            finally:
                index.close()

            if not backlinks:
                self.mount(Static("No backlinks", classes="empty-message"))
                return

            # Create list view
            list_view = ListView()

            for link in backlinks:
                source_title = link["source_title"] or link["source_id"]
                source_id = link["source_id"]

                # Create list item with title and context
                item_text = f"{source_title}"
                if link["context"]:
                    # Show brief context
                    context = link["context"]
                    if len(context) > 60:
                        context = context[:57] + "..."
                    item_text += f'\n  "{context}"'

                # Store source_id in the list item for selection
                list_item = ListItem(Label(item_text))
                list_item.source_id = source_id  # Custom attribute
                list_view.append(list_item)

            self.mount(list_view)

        except Exception:
            # Show error message
            self.mount(
                Static("Error loading backlinks", classes="empty-message")
            )

    async def clear(self) -> None:
        """Clear backlinks display."""
        self._current_note_id = None
        await self.query("ListView, .empty-message").remove()
        self.mount(Static("No note selected", classes="empty-message"))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle backlink selection."""
        # Get the source_id from the selected item
        if hasattr(event.item, "source_id"):
            self.post_message(self.BacklinkSelected(event.item.source_id))
