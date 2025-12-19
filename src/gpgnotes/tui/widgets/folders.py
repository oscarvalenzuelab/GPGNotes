"""Folders panel widget."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Label, ListItem, ListView, Static

from ...config import Config
from ...index import SearchIndex


class FoldersPanel(Vertical):
    """Panel showing folder tree."""

    DEFAULT_CSS = """
    FoldersPanel {
        width: 100%;
        height: auto;
        max-height: 12;
        border: solid $primary;
        padding: 0 1;
    }

    FoldersPanel > .panel-title {
        text-style: bold;
        color: $text;
        padding: 0;
    }

    FoldersPanel ListView {
        height: auto;
        max-height: 8;
        background: transparent;
    }

    FoldersPanel ListItem {
        padding: 0;
    }

    FoldersPanel ListItem:hover {
        background: $surface-lighten-1;
    }

    FoldersPanel ListItem.-selected {
        background: $primary;
    }
    """

    class FolderSelected(Message):
        """Message sent when a folder is selected."""

        def __init__(self, folder_name: str) -> None:
            self.folder_name = folder_name
            super().__init__()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config = Config()
        self._folders = []

    def compose(self) -> ComposeResult:
        yield Static("📁 FOLDERS", classes="panel-title")
        yield ListView(id="folders-list")

    async def refresh_folders(self) -> None:
        """Refresh the folders list."""
        index = SearchIndex(self.config)
        try:
            self._folders = index.get_folders()
        finally:
            index.close()

        list_view = self.query_one("#folders-list", ListView)
        await list_view.clear()

        # Add "All Notes" option
        list_view.append(ListItem(Label("📋 All Notes"), id="folder-all"))

        # Add "Inbox" option
        list_view.append(ListItem(Label("📥 Inbox"), id="folder-inbox"))

        # Add folders
        for folder_name, count in self._folders:
            list_view.append(
                ListItem(Label(f"📂 {folder_name} ({count})"), id=f"folder-{folder_name}")
            )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle folder selection."""
        item_id = event.item.id or ""

        if item_id == "folder-all":
            self.post_message(self.FolderSelected(""))
        elif item_id == "folder-inbox":
            self.post_message(self.FolderSelected("__inbox__"))
        elif item_id.startswith("folder-"):
            folder_name = item_id[7:]  # Remove "folder-" prefix
            self.post_message(self.FolderSelected(folder_name))
