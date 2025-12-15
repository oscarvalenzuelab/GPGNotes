"""Note storage operations with encryption."""

import os
import subprocess
from pathlib import Path
from typing import List, Optional
from .note import Note
from .encryption import Encryption
from .config import Config


class Storage:
    """Manages note storage with encryption."""

    def __init__(self, config: Config):
        """Initialize storage."""
        self.config = config
        self.notes_dir = config.notes_dir
        self.encryption = Encryption(config.get('gpg_key'))
        self.config.ensure_dirs()

    def save_note(self, note: Note) -> Path:
        """Save note to disk with encryption."""
        note.update_modified()

        # Get relative path and create full path
        rel_path = note.get_relative_path()
        full_path = self.notes_dir / rel_path

        # Create directory if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Encrypt and save
        markdown_content = note.to_markdown()
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
            self.notes_dir.rglob("*.md.gpg"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

    def edit_note(self, file_path: Path) -> Note:
        """Edit note using configured editor."""
        # Decrypt to temp file
        temp_path = self.encryption.decrypt_to_temp(file_path)

        try:
            # Open in editor
            editor = self.config.get('editor', 'nano')
            subprocess.run([editor, str(temp_path)], check=True)

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

    def search_notes(self, query: str) -> List[Note]:
        """Simple content search (will be replaced by index search)."""
        results = []

        for file_path in self.list_notes():
            try:
                note = self.load_note(file_path)
                if (query.lower() in note.title.lower() or
                    query.lower() in note.content.lower() or
                    any(query.lower() in tag.lower() for tag in note.tags)):
                    results.append(note)
            except Exception:
                # Skip files that can't be decrypted
                continue

        return results
