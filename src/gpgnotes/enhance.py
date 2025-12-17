"""Note enhancement with LLM assistance."""

import difflib
from typing import Optional

from prompt_toolkit import prompt
from prompt_toolkit.validation import ValidationError, Validator
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from .config import Config
from .llm import get_provider
from .note import Note

console = Console()


class ChoiceValidator(Validator):
    """Validator for user choice input."""

    def __init__(self, valid_choices: list[str]):
        self.valid_choices = [c.lower() for c in valid_choices]

    def validate(self, document):
        text = document.text.lower().strip()
        if text and text not in self.valid_choices:
            raise ValidationError(message=f"Please enter one of: {', '.join(self.valid_choices)}")


class EnhancementSession:
    """Manages an interactive enhancement session."""

    def __init__(self, note: Note, config: Config):
        """
        Initialize enhancement session.

        Args:
            note: The note to enhance
            config: Configuration object
        """
        self.note = note
        self.config = config
        self.original_content = note.content
        self.current_content = note.content
        self.history = [note.content]  # Track all versions
        self.current_index = 0

    def _get_provider(self):
        """Get configured LLM provider."""
        provider_name = self.config.get("llm_provider")
        if not provider_name:
            raise ValueError("No LLM provider configured. Use 'notes config --llm-provider <name>'")

        # Get API key from secrets (not needed for Ollama)
        api_key = None
        if provider_name != "ollama":
            api_key = self.config.get_secret(f"{provider_name}_api_key")
            if not api_key:
                raise ValueError(
                    f"No API key configured for {provider_name}. Use 'notes config --llm-key <key>'"
                )

        model = self.config.get("llm_model") or None
        return get_provider(provider_name, api_key=api_key, model=model)

    def _show_content(self, content: str, title: str = "Content"):
        """Display content in a panel."""
        console.print(Panel(content.strip(), title=title, border_style="cyan"))

    def _show_diff(self, old: str, new: str):
        """Show unified diff between two versions."""
        diff = difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile="Original",
            tofile="Enhanced",
            lineterm="",
        )

        diff_text = "".join(diff)
        if not diff_text:
            console.print("[yellow]No changes detected[/yellow]")
            return

        syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=False)
        console.print(Panel(syntax, title="Unified Diff", border_style="yellow"))

    def _show_menu(self) -> str:
        """Show interactive menu and get user choice."""
        print("\nWhat would you like to do?\n")
        print("  [a] Accept changes and save")
        print("  [r] Reject changes (keep original)")
        print("  [i] Iterate with new instructions")
        print("  [d] Show detailed diff")
        print("  [b] Back to previous version")
        print("  [v] View current version")
        print("  [o] View original version")
        print("  [q] Quit without saving")

        validator = ChoiceValidator(["a", "r", "i", "d", "b", "v", "o", "q"])

        try:
            choice = prompt(
                "\nYour choice: ",
                validator=validator,
                validate_while_typing=False,
            )
            return choice.lower().strip()
        except (KeyboardInterrupt, EOFError):
            return "q"

    def _get_default_instructions(self) -> str:
        """Show preset enhancement options."""
        print("\nChoose enhancement style:\n")
        print("  [1] Fix grammar and spelling")
        print("  [2] Improve clarity and readability")
        print("  [3] Make more concise")
        print("  [4] Make more professional")
        print("  [5] Make more casual")
        print("  [6] Add bullet points/structure")
        print("  [c] Custom instructions")

        try:
            choice = prompt("\nChoice (or press Enter for grammar): ").lower().strip() or "1"

            presets = {
                "1": "Fix all grammar and spelling errors. Maintain the original tone and style.",
                "2": "Improve clarity and readability. Make the text easier to understand while keeping the same information.",
                "3": "Make the text more concise without losing important information. Remove redundancy.",
                "4": "Rewrite in a professional, formal tone. Improve structure and clarity.",
                "5": "Rewrite in a casual, conversational tone while keeping it clear and organized.",
                "6": "Organize the content with bullet points, headings, and clear structure where appropriate.",
            }

            if choice in presets:
                return presets[choice]
            else:
                # Custom instructions
                custom = prompt("Enter your custom instructions: ").strip()
                return custom if custom else presets["1"]

        except (KeyboardInterrupt, EOFError):
            return "Fix all grammar and spelling errors."

    def enhance(self, instructions: Optional[str] = None) -> bool:
        """
        Run interactive enhancement session.

        Args:
            instructions: Initial enhancement instructions (None for interactive)

        Returns:
            True if changes were saved, False if cancelled
        """
        # Get initial instructions if not provided
        if not instructions:
            instructions = self._get_default_instructions()

        console.print(f"\n[bold blue]Enhancing with instructions:[/bold blue] {instructions}")

        # Get provider
        try:
            provider = self._get_provider()
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            return False

        # Initial enhancement
        try:
            with console.status("[bold blue]Requesting enhancement from LLM..."):
                enhanced = provider.enhance(self.current_content, instructions)

            self.current_content = enhanced
            self.history.append(enhanced)
            self.current_index = len(self.history) - 1

        except Exception as e:
            console.print(f"[red]Enhancement failed:[/red] {e}")
            return False

        # Interactive loop
        while True:
            console.print("\n" + "=" * 60 + "\n")

            # Show original and enhanced side by side
            self._show_content(self.original_content, "Original Note")
            console.print()
            self._show_content(self.current_content, "Enhanced Version")

            # Show menu and get choice
            choice = self._show_menu()

            if choice == "a":
                # Accept changes
                self.note.content = self.current_content
                console.print("\n[green]✓ Changes accepted and will be saved[/green]")
                return True

            elif choice == "r":
                # Reject changes
                console.print("\n[yellow]Changes rejected. Original content preserved.[/yellow]")
                return False

            elif choice == "i":
                # Iterate with new instructions
                console.print()
                new_instructions = prompt("Enter new enhancement instructions: ").strip()
                if new_instructions:
                    try:
                        with console.status("[bold blue]Refining with your feedback..."):
                            enhanced = provider.enhance(self.current_content, new_instructions)

                        self.current_content = enhanced
                        self.history.append(enhanced)
                        self.current_index = len(self.history) - 1

                        console.print("[green]✓ Refinement complete[/green]")

                    except Exception as e:
                        console.print(f"[red]Refinement failed:[/red] {e}")

            elif choice == "d":
                # Show diff
                console.print()
                self._show_diff(self.original_content, self.current_content)
                input("\nPress Enter to continue...")

            elif choice == "b":
                # Go back to previous version
                if self.current_index > 0:
                    self.current_index -= 1
                    self.current_content = self.history[self.current_index]
                    console.print(
                        f"[yellow]Reverted to version {self.current_index + 1}/"
                        f"{len(self.history)}[/yellow]"
                    )
                else:
                    console.print("[yellow]Already at original version[/yellow]")

            elif choice == "v":
                # View current
                console.print()
                self._show_content(self.current_content, "Current Version")
                input("\nPress Enter to continue...")

            elif choice == "o":
                # View original
                console.print()
                self._show_content(self.original_content, "Original Version")
                input("\nPress Enter to continue...")

            elif choice == "q":
                # Quit
                console.print("\n[yellow]Enhancement cancelled. No changes saved.[/yellow]")
                return False


def quick_enhance(note: Note, config: Config, instructions: str) -> Note:
    """
    Quick enhancement without interactive UI.

    Args:
        note: The note to enhance
        config: Configuration object
        instructions: Enhancement instructions

    Returns:
        Enhanced note (original note is modified in-place)
    """
    # Get provider
    provider_name = config.get("llm_provider")
    if not provider_name:
        raise ValueError("No LLM provider configured")

    api_key = None
    if provider_name != "ollama":
        api_key = config.get_secret(f"{provider_name}_api_key")
        if not api_key:
            raise ValueError(f"No API key configured for {provider_name}")

    model = config.get("llm_model") or None
    provider = get_provider(provider_name, api_key=api_key, model=model)

    # Enhance
    enhanced = provider.enhance(note.content, instructions)
    note.content = enhanced

    return note
