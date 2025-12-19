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
        self.plain_dir = config.notes_dir / "plain"
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

    def save_plain_note(self, note: Note) -> Path:
        """Save note to disk without encryption (plain markdown)."""
        note.update_modified()
        note.is_plain = True

        # Get relative path and create full path in plain directory
        rel_path = note.get_relative_path()
        # Remove .gpg extension for plain files
        rel_path_str = str(rel_path)
        if rel_path_str.endswith(".gpg"):
            rel_path_str = rel_path_str[:-4]  # Remove .gpg
        full_path = self.plain_dir / rel_path_str

        # Create directory if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Save as plain markdown
        markdown_content = note.to_markdown()
        full_path.write_text(markdown_content, encoding="utf-8")

        note.file_path = full_path
        return full_path

    def load_note(self, file_path: Path) -> Note:
        """Load and decrypt note from disk."""
        if not file_path.exists():
            raise FileNotFoundError(f"Note not found: {file_path}")

        # Check if it's a plain file
        if self._is_plain_file(file_path):
            return self.load_plain_note(file_path)

        # Decrypt and parse encrypted note
        content = self.encryption.decrypt(file_path)
        note = Note.from_markdown(content, file_path)

        return note

    def load_plain_note(self, file_path: Path) -> Note:
        """Load plain (non-encrypted) note from disk."""
        if not file_path.exists():
            raise FileNotFoundError(f"Note not found: {file_path}")

        # Read plain file content
        content = file_path.read_text(encoding="utf-8")

        # Try to parse as markdown with frontmatter
        try:
            note = Note.from_markdown(content, file_path)
            note.is_plain = True

            # If title is "Untitled", try to extract from content or use filename
            if note.title == "Untitled":
                # Try to extract first H1 heading
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("# "):
                        note.title = line[2:].strip()
                        break
                else:
                    # No H1 found, use filename
                    note.title = file_path.stem

            return note
        except Exception:
            # If parsing fails, create a simple note from the content
            # Try to extract title from first H1 heading or use filename
            title = file_path.stem
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("# "):
                    title = line[2:].strip()
                    break

            note = Note(title=title, content=content, file_path=file_path)
            note.is_plain = True
            return note

    def _is_plain_file(self, file_path: Path) -> bool:
        """Check if a file is a plain (non-encrypted) file."""
        # Files with .gpg extension are always encrypted
        if file_path.suffix == ".gpg":
            return False

        try:
            # Check if file is in plain directory (resolve paths for consistent comparison)
            file_path.resolve().relative_to(self.plain_dir.resolve())
            return True
        except ValueError:
            return False

    def list_notes(self, include_plain: bool = False) -> List[Path]:
        """List all note files.

        Args:
            include_plain: If True, include plain (non-encrypted) files

        Returns:
            List of file paths sorted by modification time (newest first)
        """
        if not self.notes_dir.exists():
            return []

        files = []

        # Find all .gpg files (encrypted notes)
        files.extend(self.notes_dir.rglob("*.md.gpg"))

        # Optionally include plain files
        if include_plain and self.plain_dir.exists():
            files.extend(self.list_plain_files())

        return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)

    def list_plain_files(self) -> List[Path]:
        """List all plain (non-encrypted) files."""
        if not self.plain_dir.exists():
            return []

        # Find all supported plain text formats
        plain_files = []
        for pattern in ["*.md", "*.txt", "*.html", "*.json"]:
            plain_files.extend(self.plain_dir.rglob(pattern))

        return plain_files

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
        # Check if it's a plain file
        if self._is_plain_file(file_path):
            return self.edit_plain_note(file_path)

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

    def edit_plain_note(self, file_path: Path) -> Note:
        """Edit plain (non-encrypted) note using configured editor."""
        if not file_path.exists():
            raise FileNotFoundError(f"Note not found: {file_path}")

        # Open in editor directly (no encryption/decryption needed)
        editor = self.config.get("editor", "nano")
        editor_cmd = self._build_editor_command(editor, str(file_path))
        subprocess.run(editor_cmd, check=True)

        # Load and return updated note
        return self.load_plain_note(file_path)

    def delete_note(self, file_path: Path) -> bool:
        """Delete note file."""
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def find_by_id(self, note_id: str) -> Path:
        """Find note file by ID (timestamp).

        Plain exports have 'p' prefix (e.g., p20251217191420 vs 20251217191420).
        """
        for file_path in self.list_notes(include_plain=True):
            if Note.extract_id_from_path(file_path) == note_id:
                return file_path
        raise FileNotFoundError(f"Note with ID {note_id} not found")

    def search_notes(self, query: str, include_plain: bool = True) -> List[Note]:
        """Simple content search (will be replaced by index search).

        Args:
            query: Search query string
            include_plain: If True, include plain files in search

        Returns:
            List of notes matching the query
        """
        results = []

        for file_path in self.list_notes(include_plain=include_plain):
            try:
                note = self.load_note(file_path)
                if (
                    query.lower() in note.title.lower()
                    or query.lower() in note.content.lower()
                    or any(query.lower() in tag.lower() for tag in note.tags)
                ):
                    results.append(note)
            except Exception:
                # Skip files that can't be decrypted/loaded
                continue

        return results
