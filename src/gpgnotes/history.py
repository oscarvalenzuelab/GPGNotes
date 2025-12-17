"""Version history management for GPGNotes using Git."""

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class Version:
    """Represents a single version in note history."""

    number: int
    commit: str
    date: datetime
    message: str
    author: str
    is_current: bool = False


class VersionHistory:
    """Manage version history using Git."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def _run_git(self, *args) -> str:
        """Run a git command and return output."""
        try:
            result = subprocess.run(
                ["git", "-C", str(self.repo_path)] + list(args),
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git command failed: {e.stderr}")

    def get_history(self, file_path: Path) -> List[Version]:
        """Get all commits that modified this file.

        Returns versions in reverse chronological order (newest first).
        """
        if not file_path.exists():
            return []

        # Get relative path from repo root
        rel_path = file_path.relative_to(self.repo_path)

        try:
            # Get commit history for this file
            log_output = self._run_git(
                "log",
                "--format=%H|%at|%s|%an",
                "--follow",  # Follow renames
                "--",
                str(rel_path),
            )

            if not log_output:
                return []

            versions = []
            commits = log_output.strip().split("\n")

            for i, line in enumerate(commits):
                parts = line.split("|", 3)
                if len(parts) < 4:
                    continue

                commit_hash, timestamp, message, author = parts

                version = Version(
                    number=len(commits) - i,  # Reverse numbering (oldest = 1)
                    commit=commit_hash[:7],
                    date=datetime.fromtimestamp(int(timestamp)),
                    message=message,
                    author=author,
                    is_current=(i == 0),  # First commit is current
                )
                versions.append(version)

            return versions

        except RuntimeError:
            return []

    def get_version_content(self, file_path: Path, commit: str) -> bytes:
        """Get file content at specific commit."""
        rel_path = file_path.relative_to(self.repo_path)

        try:
            content = self._run_git("show", f"{commit}:{rel_path}")
            return content.encode("utf-8")
        except RuntimeError as e:
            raise FileNotFoundError(f"Version not found: {e}")

    def get_version_by_number(self, file_path: Path, version_num: int) -> Optional[str]:
        """Get commit hash by version number."""
        history = self.get_history(file_path)
        for version in history:
            if version.number == version_num:
                return version.commit
        return None

    def diff_versions(
        self, file_path: Path, from_commit: str, to_commit: str
    ) -> str:
        """Get unified diff between two versions."""
        rel_path = file_path.relative_to(self.repo_path)

        try:
            diff_output = self._run_git(
                "diff",
                "--no-color",
                from_commit,
                to_commit,
                "--",
                str(rel_path),
            )
            return diff_output
        except RuntimeError:
            return ""

    def get_file_at_date(self, file_path: Path, date: str) -> Optional[str]:
        """Get commit hash closest to specified date."""
        rel_path = file_path.relative_to(self.repo_path)

        try:
            # Get first commit before or at the specified date
            commit = self._run_git(
                "rev-list",
                "-1",
                f"--before={date}",
                "HEAD",
                "--",
                str(rel_path),
            )
            return commit[:7] if commit else None
        except RuntimeError:
            return None

    def restore_version(
        self, file_path: Path, commit: str, storage
    ) -> None:
        """Restore file to a specific version by creating a new version.

        This is non-destructive - creates a new commit with old content.
        """
        # Get content from historical version
        content_bytes = self.get_version_content(file_path, commit)

        # Decrypt if it's a .gpg file
        if file_path.suffix == ".gpg":
            from .encryption import Encryption

            encryption = Encryption(storage.config.get("gpg_key"))
            # Save temporary file
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".gpg", delete=False) as tmp:
                tmp.write(content_bytes)
                tmp_path = Path(tmp.name)

            try:
                # Decrypt
                content = encryption.decrypt(tmp_path)
            finally:
                tmp_path.unlink()

            # Load as note and save
            note = storage.load_note(file_path)
            note.content = content
            storage.save_note(note)
        else:
            # Plain file, just write content
            file_path.write_bytes(content_bytes)


def parse_diff_output(diff: str) -> List[Tuple[str, str]]:
    """Parse git diff output into lines with change type.

    Returns list of (change_type, line) tuples where change_type is:
    - 'add' for additions (+)
    - 'del' for deletions (-)
    - 'ctx' for context lines
    """
    result = []

    for line in diff.split("\n"):
        if line.startswith("+++") or line.startswith("---"):
            continue  # Skip file headers
        elif line.startswith("@@"):
            result.append(("hdr", line))  # Hunk header
        elif line.startswith("+"):
            result.append(("add", line[1:]))
        elif line.startswith("-"):
            result.append(("del", line[1:]))
        else:
            result.append(("ctx", line))

    return result
