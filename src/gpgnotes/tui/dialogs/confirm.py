"""Confirmation dialog for GPGNotes TUI."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmDialog(ModalScreen[bool]):
    """Confirmation dialog with Yes/No buttons."""

    DEFAULT_CSS = """
    ConfirmDialog {
        align: center middle;
    }

    ConfirmDialog > Container {
        width: auto;
        max-width: 60;
        height: auto;
        border: thick $error;
        background: $surface;
        padding: 1 2;
    }

    ConfirmDialog .dialog-title {
        text-style: bold;
        color: $error;
        text-align: center;
        padding-bottom: 1;
    }

    ConfirmDialog .dialog-message {
        text-align: center;
        padding-bottom: 1;
    }

    ConfirmDialog Horizontal {
        align: center middle;
        padding-top: 1;
    }

    ConfirmDialog Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, title: str, message: str = ""):
        super().__init__()
        self._title = title
        self._message = message

    def compose(self) -> ComposeResult:
        with Container():
            yield Static(f"⚠️ {self._title}", classes="dialog-title")
            if self._message:
                yield Static(self._message, classes="dialog-message")
            with Horizontal():
                yield Button("Yes (y)", variant="error", id="yes-btn")
                yield Button("No (n)", variant="primary", id="no-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "yes-btn":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_confirm(self) -> None:
        """Confirm the action."""
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel the action."""
        self.dismiss(False)
