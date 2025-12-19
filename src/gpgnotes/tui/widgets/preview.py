"""Preview panel widget for displaying note content."""

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Markdown, Static

from ...note import Note


class PreviewPanel(VerticalScroll):
    """Panel showing note preview with markdown rendering."""

    DEFAULT_CSS = """
    PreviewPanel {
        width: 1fr;
        height: 100%;
        border: solid $primary;
        padding: 1 2;
    }

    PreviewPanel > .preview-title {
        text-style: bold;
        color: $secondary;
        padding-bottom: 1;
    }

    PreviewPanel > .preview-meta {
        color: $text-muted;
        padding-bottom: 1;
    }

    PreviewPanel > .preview-content {
        width: 100%;
    }

    PreviewPanel > .empty-message {
        color: $text-muted;
        text-style: italic;
    }

    PreviewPanel > .error-message {
        color: $error;
    }

    PreviewPanel > .encrypted-notice {
        color: $warning;
        text-style: bold;
        padding: 2 0;
        text-align: center;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_note = None

    def compose(self) -> ComposeResult:
        yield Static("Select a note to preview", classes="empty-message")

    def update_content(self, note: Note) -> None:
        """Update the preview with note content."""
        self._current_note = note

        # Clear current content
        self.remove_children()

        # Add title
        self.mount(Static(f"# {note.title}", classes="preview-title"))

        # Add metadata
        meta_parts = []
        if note.tags:
            # Filter out folder tags for display
            display_tags = [t for t in note.tags if not t.startswith("folder:")]
            if display_tags:
                meta_parts.append(f"Tags: {', '.join(display_tags)}")

        # Show folders
        folders = [t[7:] for t in note.tags if t.startswith("folder:")]
        if folders:
            meta_parts.append(f"Folders: {', '.join(folders)}")

        if note.modified:
            meta_parts.append(f"Modified: {note.modified.strftime('%Y-%m-%d %H:%M')}")

        if meta_parts:
            self.mount(Static(" | ".join(meta_parts), classes="preview-meta"))

        # Add content as markdown
        if note.content:
            self.mount(Markdown(note.content, classes="preview-content"))
        else:
            self.mount(Static("(No content)", classes="empty-message"))

    def update_metadata(self, metadata: dict) -> None:
        """Update preview with metadata only (for encrypted notes without decryption)."""
        self._current_note = None

        # Clear current content
        self.remove_children()

        # Add title
        title = metadata.get("title", "Untitled")
        self.mount(Static(f"# {title}", classes="preview-title"))

        # Add metadata
        meta_parts = []
        tags = metadata.get("tags", [])
        if tags:
            # Filter out folder tags for display
            display_tags = [t for t in tags if not t.startswith("folder:")]
            if display_tags:
                meta_parts.append(f"Tags: {', '.join(display_tags)}")

        # Show folders
        folders = [t[7:] for t in tags if t.startswith("folder:")]
        if folders:
            meta_parts.append(f"Folders: {', '.join(folders)}")

        modified_str = metadata.get("modified")
        if modified_str:
            try:
                modified = datetime.fromisoformat(modified_str)
                meta_parts.append(f"Modified: {modified.strftime('%Y-%m-%d %H:%M')}")
            except (ValueError, TypeError):
                pass

        if meta_parts:
            self.mount(Static(" | ".join(meta_parts), classes="preview-meta"))

        # Show encrypted notice
        self.mount(
            Static(
                "🔒 Encrypted Note\n\nPress Enter to decrypt and edit",
                classes="encrypted-notice",
            )
        )

    def show_error(self, message: str) -> None:
        """Show an error message."""
        self.remove_children()
        self.mount(Static(f"Error: {message}", classes="error-message"))

    def clear(self) -> None:
        """Clear the preview."""
        self._current_note = None
        self.remove_children()
        self.mount(Static("Select a note to preview", classes="empty-message"))
