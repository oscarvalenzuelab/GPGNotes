"""GPG encryption/decryption for notes."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import gnupg


class Encryption:
    """Handles GPG encryption and decryption of notes."""

    def __init__(self, gpg_key: Optional[str] = None):
        """Initialize encryption with GPG key."""
        # Set GPG_TTY for proper terminal interaction
        if "GPG_TTY" not in os.environ:
            try:
                tty = subprocess.check_output(["tty"], text=True).strip()
                os.environ["GPG_TTY"] = tty
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Not running in a TTY (e.g., in tests)
                pass

        self.gpg = gnupg.GPG()
        self.gpg_key = gpg_key

    def encrypt(self, content: str, output_path: Path) -> bool:
        """Encrypt content and write to file."""
        if not self.gpg_key:
            raise ValueError("GPG key not configured")

        encrypted = self.gpg.encrypt(content, self.gpg_key, always_trust=True, armor=False)

        if not encrypted.ok:
            raise RuntimeError(f"Encryption failed: {encrypted.stderr}")

        with open(output_path, "wb") as f:
            f.write(encrypted.data)

        return True

    def decrypt(self, input_path: Path) -> str:
        """Decrypt file and return content."""
        if not self.gpg_key:
            raise ValueError("GPG key not configured")

        with open(input_path, "rb") as f:
            decrypted = self.gpg.decrypt_file(f)

        if not decrypted.ok:
            raise RuntimeError(f"Decryption failed: {decrypted.stderr}")

        return str(decrypted)

    def list_keys(self):
        """List available GPG keys."""
        return self.gpg.list_keys()

    def decrypt_to_temp(self, input_path: Path) -> Path:
        """Decrypt file to temporary location for editing."""
        content = self.decrypt(input_path)

        # Create temp file with .md extension for proper editor syntax highlighting
        temp_fd, temp_path = tempfile.mkstemp(suffix=".md")
        with open(temp_path, "w") as f:
            f.write(content)

        return Path(temp_path)

    def encrypt_from_temp(self, temp_path: Path, output_path: Path) -> bool:
        """Read from temp file and encrypt to output path."""
        from .llm import sanitize_for_gpg

        with open(temp_path, encoding="utf-8") as f:
            content = f.read()

        # Sanitize for GPG's latin-1 encoding
        content = sanitize_for_gpg(content)
        return self.encrypt(content, output_path)
