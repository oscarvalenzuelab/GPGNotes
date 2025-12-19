"""New note dialog for GPGNotes TUI."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Static

from ...config import Config
from ...index import SearchIndex
from ...note import Note
from ...storage import Storage


class NewNoteDialog(ModalScreen[str | None]):
    """Dialog for creating a new note."""

    DEFAULT_CSS = """
    NewNoteDialog {
        align: center middle;
    }

    NewNoteDialog > Container {
        width: 70;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    NewNoteDialog .dialog-title {
        text-style: bold;
        color: $secondary;
        text-align: center;
        padding-bottom: 1;
    }

    NewNoteDialog .field-label {
        padding: 1 0 0 0;
    }

    NewNoteDialog Input {
        margin-bottom: 0;
    }

    NewNoteDialog Checkbox {
        padding: 1 0;
    }

    NewNoteDialog Horizontal {
        align: center middle;
        padding-top: 1;
    }

    NewNoteDialog Button {
        margin: 0 1;
    }

    NewNoteDialog .hint {
        color: $text-muted;
        text-style: italic;
        padding-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+enter", "create", "Create", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.config = Config()
        self.storage = Storage(self.config)

    def compose(self) -> ComposeResult:
        with Container():
            yield Static("📝 New Note", classes="dialog-title")

            yield Static("Title:", classes="field-label")
            yield Input(placeholder="Enter note title...", id="title-input")

            yield Static("Tags (comma-separated):", classes="field-label")
            yield Input(placeholder="tag1, tag2, tag3", id="tags-input")

            yield Static("Folder:", classes="field-label")
            yield Input(placeholder="Optional folder name", id="folder-input")

            yield Checkbox("Create as plain (unencrypted)", id="plain-checkbox")

            yield Static("Enter title and press Create", classes="hint")

            with Horizontal():
                yield Button("Create", variant="primary", id="create-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_mount(self) -> None:
        """Focus the title input on mount."""
        self.query_one("#title-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "create-btn":
            self._create_note()
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input fields."""
        if event.input.id == "title-input":
            # Move to tags input
            self.query_one("#tags-input", Input).focus()
        elif event.input.id == "tags-input":
            # Move to folder input
            self.query_one("#folder-input", Input).focus()
        elif event.input.id == "folder-input":
            # Create the note
            self._create_note()

    def _create_note(self) -> None:
        """Create the note with entered details."""
        title = self.query_one("#title-input", Input).value.strip()

        if not title:
            self.notify("Title cannot be empty", severity="error")
            return

        # Parse tags
        tags_input = self.query_one("#tags-input", Input).value.strip()
        tags = [t.strip() for t in tags_input.split(",") if t.strip()]

        # Add folder tag if specified
        folder = self.query_one("#folder-input", Input).value.strip()
        if folder:
            tags.append(f"folder:{folder}")

        # Check if plain
        is_plain = self.query_one("#plain-checkbox", Checkbox).value

        try:
            # Create the note
            note = Note(title=title, content="", tags=tags)

            # Save it
            if is_plain:
                file_path = self.storage.save_plain_note(note)
            else:
                file_path = self.storage.save_note(note)

            # Open in editor
            with self.app.suspend():
                self.storage.edit_note(file_path)

            # Reload and index
            note = self.storage.load_note(file_path)
            index = SearchIndex(self.config)
            try:
                index.add_note(note)
            finally:
                index.close()

            self.dismiss(title)

        except Exception as e:
            self.notify(f"Error creating note: {e}", severity="error")

    def action_cancel(self) -> None:
        """Cancel and close the dialog."""
        self.dismiss(None)

    def action_create(self) -> None:
        """Create the note."""
        self._create_note()
