"""Configuration management for GPGNotes."""

import json
import os
from pathlib import Path
from typing import Optional


class Config:
    """Manages GPGNotes configuration."""

    DEFAULT_CONFIG_DIR = Path.home() / ".gpgnotes"
    DEFAULT_NOTES_DIR = DEFAULT_CONFIG_DIR / "notes"
    CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"
    DB_FILE = DEFAULT_CONFIG_DIR / "notes.db"
    SECRETS_FILE = DEFAULT_CONFIG_DIR / "secrets.gpg"

    DEFAULT_CONFIG = {
        "editor": os.environ.get("EDITOR", "nano"),
        "git_remote": "",
        "gpg_key": "",
        "auto_sync": True,
        "auto_tag": True,
        "llm_provider": "",  # openai, claude, ollama
        "llm_model": "",  # Model name (optional)
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
            with open(self.config_file) as f:
                return {**self.DEFAULT_CONFIG, **json.load(f)}
        return self.DEFAULT_CONFIG.copy()

    def save(self):
        """Save configuration to file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w") as f:
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
        return bool(self.get("gpg_key"))

    def is_first_run(self) -> bool:
        """Check if this is the first run (no config file exists)."""
        return not self.config_file.exists()

    def validate_gpg_key(self) -> tuple[bool, str]:
        """
        Validate that the configured GPG key exists.

        Returns:
            (is_valid, message) tuple
        """
        gpg_key = self.get("gpg_key")
        if not gpg_key:
            return False, "No GPG key configured"

        try:
            from .encryption import Encryption

            enc = Encryption()
            keys = enc.list_keys()

            # Check if key exists in keyring
            for key in keys:
                if gpg_key in key["keyid"] or any(gpg_key in uid for uid in key["uids"]):
                    return True, f"GPG key found: {key['uids'][0]}"

            return False, f"GPG key '{gpg_key}' not found in keyring"

        except Exception as e:
            return False, f"Error validating GPG key: {e}"

    def _get_secrets_path(self) -> Path:
        """Get path to encrypted secrets file."""
        return self.config_dir / "secrets.gpg"

    def _load_secrets(self) -> dict:
        """Load and decrypt secrets from GPG-encrypted file."""
        secrets_path = self._get_secrets_path()

        if not secrets_path.exists():
            return {}

        try:
            from .encryption import Encryption

            gpg_key = self.get("gpg_key")
            if not gpg_key:
                return {}

            enc = Encryption(gpg_key)
            encrypted_data = secrets_path.read_text()

            # Decrypt the data
            decrypted = enc.gpg.decrypt(encrypted_data)
            if not decrypted.ok:
                print(f"Warning: Could not decrypt secrets: {decrypted.stderr}")
                return {}

            return json.loads(str(decrypted))

        except Exception as e:
            print(f"Warning: Could not load secrets: {e}")
            return {}

    def _save_secrets(self, secrets: dict):
        """Encrypt and save secrets to GPG-encrypted file."""
        try:
            from .encryption import Encryption

            gpg_key = self.get("gpg_key")
            if not gpg_key:
                raise ValueError("No GPG key configured. Cannot save secrets.")

            enc = Encryption(gpg_key)
            secrets_json = json.dumps(secrets, indent=2)

            # Encrypt the data
            encrypted = enc.gpg.encrypt(secrets_json, gpg_key, always_trust=True, armor=True)
            if not encrypted.ok:
                raise RuntimeError(f"Encryption failed: {encrypted.stderr}")

            # Save encrypted data
            secrets_path = self._get_secrets_path()
            secrets_path.write_text(str(encrypted))

        except Exception as e:
            raise RuntimeError(f"Could not save secrets: {e}")

    def set_secret(self, key: str, value: str):
        """
        Store a secret value encrypted with GPG.

        Args:
            key: Secret identifier (e.g., 'openai_api_key')
            value: Secret value to encrypt and store
        """
        secrets = self._load_secrets()
        secrets[key] = value
        self._save_secrets(secrets)

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a decrypted secret value.

        Args:
            key: Secret identifier (e.g., 'openai_api_key')
            default: Default value if secret not found

        Returns:
            Decrypted secret value or default
        """
        secrets = self._load_secrets()
        return secrets.get(key, default)

    def delete_secret(self, key: str):
        """
        Delete a secret from encrypted storage.

        Args:
            key: Secret identifier to delete
        """
        secrets = self._load_secrets()
        if key in secrets:
            del secrets[key]
            self._save_secrets(secrets)

    def list_secrets(self) -> list[str]:
        """
        List all secret keys (not values) stored.

        Returns:
            List of secret key names
        """
        secrets = self._load_secrets()
        return list(secrets.keys())
