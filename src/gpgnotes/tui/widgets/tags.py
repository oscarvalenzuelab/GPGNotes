"""Tags panel widget."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Label, ListItem, ListView, Static

from ...config import Config
from ...index import SearchIndex


class TagsPanel(Vertical):
    """Panel showing tags list."""

    DEFAULT_CSS = """
    TagsPanel {
        width: 100%;
        height: auto;
        max-height: 10;
        border: solid $primary;
        padding: 0 1;
    }

    TagsPanel > .panel-title {
        text-style: bold;
        color: $text;
        padding: 0;
    }

    TagsPanel ListView {
        height: auto;
        max-height: 6;
        background: transparent;
    }

    TagsPanel ListItem {
        padding: 0;
    }

    TagsPanel ListItem:hover {
        background: $surface-lighten-1;
    }

    TagsPanel ListItem.-selected {
        background: $primary;
    }
    """

    class TagSelected(Message):
        """Message sent when a tag is selected."""

        def __init__(self, tag_name: str) -> None:
            self.tag_name = tag_name
            super().__init__()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config = Config()
        self._tags = {}

    def compose(self) -> ComposeResult:
        yield Static("🏷️ TAGS", classes="panel-title")
        yield ListView(id="tags-list")

    async def refresh_tags(self) -> None:
        """Refresh the tags list."""
        index = SearchIndex(self.config)
        try:
            # Get all notes and collect tags
            notes = index.get_all_metadata()
            self._tags = {}
            for note in notes:
                for tag in note.get("tags", []):
                    # Skip folder tags
                    if not tag.startswith("folder:"):
                        self._tags[tag] = self._tags.get(tag, 0) + 1
        finally:
            index.close()

        list_view = self.query_one("#tags-list", ListView)
        await list_view.clear()

        # Sort by count (descending) then name
        sorted_tags = sorted(self._tags.items(), key=lambda x: (-x[1], x[0]))

        for tag_name, count in sorted_tags[:15]:  # Show top 15 tags
            list_view.append(ListItem(Label(f"#{tag_name} ({count})"), id=f"tag-{tag_name}"))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle tag selection."""
        item_id = event.item.id or ""
        if item_id.startswith("tag-"):
            tag_name = item_id[4:]  # Remove "tag-" prefix
            self.post_message(self.TagSelected(tag_name))
