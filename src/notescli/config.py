"""Configuration management for NoteCLI."""

import json
import os
from pathlib import Path
from typing import Optional


class Config:
    """Manages NoteCLI configuration."""

    DEFAULT_CONFIG_DIR = Path.home() / ".notecli"
    DEFAULT_NOTES_DIR = DEFAULT_CONFIG_DIR / "notes"
    CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"
    DB_FILE = DEFAULT_CONFIG_DIR / "notes.db"

    DEFAULT_CONFIG = {
        "editor": os.environ.get("EDITOR", "nano"),
        "git_remote": "",
        "gpg_key": "",
        "auto_sync": True,
        "auto_tag": True,
    }

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration."""
        self.config_dir = config_dir or self.DEFAULT_CONFIG_DIR
        self.config_file = self.config_dir / "config.json"
        self.notes_dir = self.config_dir / "notes"
        self.db_file = self.config_dir / "notes.db"
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from file or create default."""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return {**self.DEFAULT_CONFIG, **json.load(f)}
        return self.DEFAULT_CONFIG.copy()

    def save(self):
        """Save configuration to file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def get(self, key: str, default=None):
        """Get configuration value."""
        return self.config.get(key, default)

    def set(self, key: str, value):
        """Set configuration value."""
        self.config[key] = value
        self.save()

    def ensure_dirs(self):
        """Ensure all necessary directories exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.notes_dir.mkdir(parents=True, exist_ok=True)

    def is_configured(self) -> bool:
        """Check if minimum configuration is set."""
        return bool(self.get('gpg_key'))

    def is_first_run(self) -> bool:
        """Check if this is the first run (no config file exists)."""
        return not self.config_file.exists()

    def validate_gpg_key(self) -> tuple[bool, str]:
        """
        Validate that the configured GPG key exists.

        Returns:
            (is_valid, message) tuple
        """
        gpg_key = self.get('gpg_key')
        if not gpg_key:
            return False, "No GPG key configured"

        try:
            from .encryption import Encryption
            enc = Encryption()
            keys = enc.list_keys()

            # Check if key exists in keyring
            for key in keys:
                if gpg_key in key['keyid'] or any(gpg_key in uid for uid in key['uids']):
                    return True, f"GPG key found: {key['uids'][0]}"

            return False, f"GPG key '{gpg_key}' not found in keyring"

        except Exception as e:
            return False, f"Error validating GPG key: {e}"
