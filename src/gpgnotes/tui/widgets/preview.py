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

    PreviewPanel > .preview-separator {
        color: $primary;
        padding: 1 0;
    }

    PreviewPanel > .backlinks-header {
        text-style: bold;
        color: $secondary;
        padding: 0 0 1 0;
    }

    PreviewPanel > .backlink-item {
        color: $text;
        padding: 0;
    }

    PreviewPanel > .backlink-context {
        color: $text-muted;
        text-style: italic;
        padding: 0 0 0 2;
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

        # Add backlinks section if enabled
        self._add_backlinks_section(note)

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

    def _add_backlinks_section(self, note: Note) -> None:
        """Add backlinks section to preview if enabled."""
        try:
            # Get config to check if backlinks should be shown
            from ...config import Config

            config = Config()
            show_mode = config.get("tui_show_backlinks", "both")

            if show_mode not in ["preview", "both"]:
                return

            # Get backlinks from index
            from ...index import SearchIndex

            index = SearchIndex(config)
            try:
                backlinks = index.get_backlinks(note.note_id)
            finally:
                index.close()

            if not backlinks:
                return

            # Add separator
            self.mount(Static("─" * 60, classes="preview-separator"))

            # Add backlinks header
            self.mount(
                Static(
                    f"📎 Backlinks ({len(backlinks)})",
                    classes="backlinks-header",
                )
            )

            # Add each backlink
            for link in backlinks:
                source_title = link["source_title"] or link["source_id"]
                self.mount(Static(f"  • {source_title}", classes="backlink-item"))

                if link["context"]:
                    # Truncate context if too long
                    context = link["context"]
                    if len(context) > 100:
                        context = context[:97] + "..."
                    self.mount(Static(f'    "{context}"', classes="backlink-context"))

        except Exception:
            # Silently fail if backlinks can't be loaded
            pass
