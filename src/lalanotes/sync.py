"""Git synchronization for notes."""

from typing import Optional

import git

from .config import Config


class GitSync:
    """Handles Git operations for note synchronization."""

    def __init__(self, config: Config):
        """Initialize Git sync."""
        self.config = config
        self.notes_dir = config.notes_dir
        self.repo: Optional[git.Repo] = None

    def init_repo(self):
        """Initialize or open Git repository."""
        try:
            self.repo = git.Repo(self.notes_dir)
        except git.InvalidGitRepositoryError:
            # Initialize new repo
            self.repo = git.Repo.init(self.notes_dir)

            # Create .gitignore
            gitignore_path = self.notes_dir / ".gitignore"
            if not gitignore_path.exists():
                gitignore_path.write_text("*.tmp\n.DS_Store\n")

            # Set remote if configured
            remote_url = self.config.get("git_remote")
            if remote_url:
                try:
                    self.repo.create_remote("origin", remote_url)
                except git.CommandError:
                    # Remote already exists
                    pass

    def has_remote(self) -> bool:
        """Check if remote is configured."""
        if not self.repo:
            return False
        return len(self.repo.remotes) > 0

    def commit(self, message: str = "Update notes") -> bool:
        """Commit changes to Git."""
        if not self.repo:
            self.init_repo()

        try:
            # Add all changes
            self.repo.index.add("*")

            # Check if there are changes to commit
            if not self.repo.index.diff("HEAD"):
                return False

            # Commit
            self.repo.index.commit(message)
            return True

        except Exception as e:
            print(f"Commit failed: {e}")
            return False

    def pull(self) -> bool:
        """Pull changes from remote."""
        if not self.repo or not self.has_remote():
            return False

        try:
            origin = self.repo.remotes.origin
            origin.pull()
            return True
        except Exception as e:
            print(f"Pull failed: {e}")
            return False

    def push(self) -> bool:
        """Push changes to remote."""
        if not self.repo or not self.has_remote():
            return False

        try:
            origin = self.repo.remotes.origin
            origin.push()
            return True
        except Exception as e:
            print(f"Push failed: {e}")
            return False

    def sync(self, message: str = "Update notes") -> bool:
        """Full sync: pull, commit, push."""
        if not self.config.get("auto_sync"):
            return False

        self.init_repo()

        # Pull first
        if self.has_remote():
            self.pull()

        # Commit local changes
        committed = self.commit(message)

        # Push if we have remote and committed something
        if self.has_remote() and committed:
            return self.push()

        return True

    def resolve_conflicts(self):
        """Attempt automatic conflict resolution."""
        if not self.repo:
            return

        # Check for conflicts
        unmerged = [item[0] for item in self.repo.index.unmerged_blobs()]

        if not unmerged:
            return

        # For now, use "ours" strategy (keep local version)
        # In future, could implement smarter merge
        for file_path in unmerged:
            full_path = self.notes_dir / file_path
            if full_path.exists():
                self.repo.index.add([file_path])
