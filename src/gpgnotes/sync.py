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

            # Set remote if configured BEFORE creating initial commit
            remote_url = self.config.get("git_remote")
            if remote_url:
                try:
                    origin = self.repo.create_remote("origin", remote_url)
                except git.CommandError:
                    # Remote already exists
                    origin = self.repo.remotes.origin

                # Try to fetch and checkout existing remote branch
                try:
                    origin.fetch()

                    # Check if remote has branches (existing repo with notes)
                    if origin.refs:
                        # Find main or master branch
                        remote_branch = None
                        for ref in origin.refs:
                            if ref.name in ["origin/main", "origin/master"]:
                                remote_branch = ref.name.split("/")[1]
                                break

                        if remote_branch:
                            # Checkout and track the remote branch
                            self.repo.git.checkout("-b", remote_branch, f"origin/{remote_branch}")
                            return
                except Exception as e:
                    # Remote is empty or unreachable, continue with local init
                    print(f"Could not fetch from remote: {e}")

            # Create .gitignore (only if we didn't checkout from remote)
            gitignore_path = self.notes_dir / ".gitignore"
            if not gitignore_path.exists():
                gitignore_path.write_text("*.tmp\n.DS_Store\n")

            # Create initial commit to establish HEAD
            try:
                self.repo.index.add([".gitignore"])
                self.repo.index.commit("Initial commit")
            except Exception:
                # If commit fails, repo might already have commits
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
            # Add all changes including deletions
            self.repo.git.add(A=True)  # -A flag adds all changes including deletions

            # Check if there are changes to commit
            # Handle case where HEAD doesn't exist yet (no commits)
            try:
                if not self.repo.index.diff("HEAD"):
                    return False
            except git.BadName:
                # No HEAD yet - this will be the first commit
                pass

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
            # Get current branch name
            current_branch = self.repo.active_branch.name

            # Pull with explicit branch and use merge strategy (simpler than rebase)
            origin = self.repo.remotes.origin
            origin.pull(current_branch)
            return True
        except git.GitCommandError as e:
            # Ignore error if remote branch doesn't exist yet (new repo)
            if "couldn't find remote ref" in str(e).lower():
                return True
            # Handle unrelated histories (initial sync from existing remote)
            if "unrelated histories" in str(e).lower() or "refusing to merge" in str(e).lower():
                try:
                    # Pull with --allow-unrelated-histories flag
                    current_branch = self.repo.active_branch.name
                    self.repo.git.pull("origin", current_branch, allow_unrelated_histories=True)
                    return True
                except Exception as e2:
                    print(f"Pull with unrelated histories failed: {e2}")
                    return False
            # If pull fails due to conflicts, commit local changes and try again
            if "would be overwritten" in str(e).lower() or "fast-forward" in str(e).lower():
                try:
                    # Add and commit any untracked/uncommitted files
                    self.repo.git.add(A=True)
                    if self.repo.is_dirty() or self.repo.untracked_files:
                        self.repo.index.commit("Auto-commit before pull")
                    # Try pull again with current branch
                    current_branch = self.repo.active_branch.name
                    origin.pull(current_branch)
                    return True
                except Exception:
                    print(f"Pull failed: {e}")
                    return False
            print(f"Pull failed: {e}")
            return False
        except Exception as e:
            print(f"Pull failed: {e}")
            return False

    def push(self) -> bool:
        """Push changes to remote."""
        if not self.repo or not self.has_remote():
            return False

        try:
            origin = self.repo.remotes.origin
            current_branch = self.repo.active_branch.name

            # Try to push with set-upstream in case this is first push
            try:
                origin.push(refspec=f"{current_branch}:{current_branch}", set_upstream=True)
            except git.GitCommandError as e:
                # If already has upstream, try regular push
                if "already exists" in str(e).lower() or "up-to-date" in str(e).lower():
                    origin.push()
                else:
                    raise
            return True
        except Exception as e:
            print(f"Push failed: {e}")
            return False

    def sync(self, message: str = "Update notes") -> bool:
        """Full sync: commit, pull, push."""
        if not self.config.get("auto_sync"):
            return False

        self.init_repo()

        # Commit local changes FIRST (before pull to avoid conflicts)
        committed = self.commit(message)

        # Pull from remote
        if self.has_remote():
            pull_success = self.pull()
            if not pull_success:
                print("Warning: Pull failed, but local changes are committed")
                # Still try to push our commits
                if committed:
                    return self.push()
                return False

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
