"""Help screen for GPGNotes TUI."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Markdown, Static

HELP_TEXT = """
# GPGNotes TUI Help

## Navigation

| Key | Action |
|-----|--------|
| `↑/↓` or `j/k` | Navigate list |
| `Tab` | Switch panels |
| `Enter` | Open/select item |
| `Escape` | Cancel/back |

## Note Operations

| Key | Action |
|-----|--------|
| `n` | Create new note |
| `e` | Edit selected note |
| `d` | Delete selected note |

## Other Commands

| Key | Action |
|-----|--------|
| `s` | Search notes |
| `y` | Sync with Git |
| `r` | Refresh display |
| `F1` | Show this help |
| `q` | Quit application |

## Panels

- **Folders**: Filter notes by folder. Select "All Notes" to clear filter.
- **Notes**: List of notes. Use arrow keys to navigate, Enter to edit.
- **Tags**: Filter notes by tag.
- **Preview**: Shows selected note content with markdown rendering.

## Tips

- Notes are automatically saved when you close the editor
- Use folders to organize related notes
- The Inbox shows notes without any folder assignment
- Sync regularly to backup your notes

---
*Press Escape or Enter to close this help*
"""


class HelpScreen(ModalScreen[None]):
    """Help screen showing keyboard shortcuts and tips."""

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }

    HelpScreen > Container {
        width: 80%;
        max-width: 90;
        height: 85%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    HelpScreen .help-title {
        text-style: bold;
        color: $secondary;
        text-align: center;
        padding-bottom: 1;
    }

    HelpScreen VerticalScroll {
        height: 1fr;
    }

    HelpScreen .hint {
        color: $text-muted;
        text-style: italic;
        dock: bottom;
        padding-top: 1;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("enter", "close", "Close", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Container():
            with VerticalScroll():
                yield Markdown(HELP_TEXT)
            yield Static("Press Escape or Enter to close", classes="hint")

    def action_close(self) -> None:
        """Close the help screen."""
        self.dismiss(None)
