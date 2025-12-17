"""Note storage operations with encryption."""

import os
import subprocess
from pathlib import Path
from typing import List

from .config import Config
from .encryption import Encryption
from .llm import sanitize_for_gpg
from .note import Note


class Storage:
    """Manages note storage with encryption."""

    def __init__(self, config: Config):
        """Initialize storage."""
        self.config = config
        self.notes_dir = config.notes_dir
        self.encryption = Encryption(config.get("gpg_key"))
        self.config.ensure_dirs()

    def save_note(self, note: Note) -> Path:
        """Save note to disk with encryption."""
        note.update_modified()

        # Get relative path and create full path
        rel_path = note.get_relative_path()
        full_path = self.notes_dir / rel_path

        # Create directory if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Encrypt and save (sanitize for GPG's latin-1 encoding)
        markdown_content = note.to_markdown()
        markdown_content = sanitize_for_gpg(markdown_content)
        self.encryption.encrypt(markdown_content, full_path)

        note.file_path = full_path
        return full_path

    def load_note(self, file_path: Path) -> Note:
        """Load and decrypt note from disk."""
        if not file_path.exists():
            raise FileNotFoundError(f"Note not found: {file_path}")

        # Decrypt and parse
        content = self.encryption.decrypt(file_path)
        note = Note.from_markdown(content, file_path)

        return note

    def list_notes(self) -> List[Path]:
        """List all note files."""
        if not self.notes_dir.exists():
            return []

        # Find all .gpg files
        return sorted(
            self.notes_dir.rglob("*.md.gpg"), key=lambda p: p.stat().st_mtime, reverse=True
        )

    def _build_editor_command(self, editor: str, file_path: str) -> list[str]:
        """
        Build editor command with appropriate flags for markdown and text wrapping.

        Args:
            editor: Editor name (vim, nano, etc.)
            file_path: Path to file to edit

        Returns:
            Command list for subprocess
        """
        editor_base = os.path.basename(editor).lower()

        # Vim/Neovim: set textwidth, wrap, spell check for markdown
        if editor_base in ["vim", "vi", "nvim"]:
            return [
                editor,
                "+set textwidth=80",  # Wrap at 80 columns
                "+set wrap",  # Enable visual line wrapping
                "+set linebreak",  # Break at word boundaries
                "+set spell spelllang=en_us",  # Enable spell check
                "+set filetype=markdown",  # Enable markdown syntax
                "+normal G",  # Go to end of file
                str(file_path),
            ]

        # Nano: enable wrapping and spell check
        elif editor_base == "nano":
            return [
                editor,
                "-w",  # Disable line wrapping (we'll use soft wrap)
                "-r",
                "80",  # Set right margin at 80
                "-S",  # Enable smooth scrolling
                str(file_path),
            ]

        # Emacs: markdown mode with auto-fill
        elif editor_base == "emacs":
            return [
                editor,
                "--eval",
                "(markdown-mode)",
                "--eval",
                "(auto-fill-mode 1)",
                "--eval",
                "(setq-default fill-column 80)",
                str(file_path),
            ]

        # VS Code: just open the file (has built-in markdown support)
        elif editor_base in ["code", "code-insiders"]:
            return [editor, "--wait", str(file_path)]

        # Default: no special flags
        else:
            return [editor, str(file_path)]

    def edit_note(self, file_path: Path) -> Note:
        """Edit note using configured editor."""
        # Decrypt to temp file
        temp_path = self.encryption.decrypt_to_temp(file_path)

        try:
            # Open in editor with appropriate flags
            editor = self.config.get("editor", "nano")
            editor_cmd = self._build_editor_command(editor, str(temp_path))
            subprocess.run(editor_cmd, check=True)

            # Re-encrypt
            self.encryption.encrypt_from_temp(temp_path, file_path)

            # Load and return updated note
            return self.load_note(file_path)

        finally:
            # Clean up temp file
            if temp_path.exists():
                os.unlink(temp_path)

    def delete_note(self, file_path: Path) -> bool:
        """Delete note file."""
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def find_by_id(self, note_id: str) -> Path:
        """Find note file by ID (timestamp)."""
        # Search for file with this ID in all directories
        for file_path in self.list_notes():
            if Note.extract_id_from_path(file_path) == note_id:
                return file_path
        raise FileNotFoundError(f"Note with ID {note_id} not found")

    def search_notes(self, query: str) -> List[Note]:
        """Simple content search (will be replaced by index search)."""
        results = []

        for file_path in self.list_notes():
            try:
                note = self.load_note(file_path)
                if (
                    query.lower() in note.title.lower()
                    or query.lower() in note.content.lower()
                    or any(query.lower() in tag.lower() for tag in note.tags)
                ):
                    results.append(note)
            except Exception:
                # Skip files that can't be decrypted
                continue

        return results
