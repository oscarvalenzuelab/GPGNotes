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
            # Configure merge strategy for existing repo
            self._configure_git()
        except git.InvalidGitRepositoryError:
            # Initialize new repo
            self.repo = git.Repo.init(self.notes_dir)
            self._configure_git()

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

    def _configure_git(self):
        """Configure Git settings for automatic conflict resolution."""
        if not self.repo:
            return

        with self.repo.config_writer() as git_config:
            # Don't use rebase by default - merge is safer for encrypted files
            git_config.set_value("pull", "rebase", "false")
            # Use recursive merge strategy with ours preference
            git_config.set_value("merge", "conflictstyle", "merge")
            # Allow fast-forward when possible, but merge when needed
            git_config.set_value("pull", "ff", "true")

    def _fix_detached_head(self) -> bool:
        """Fix detached HEAD state by checking out the branch."""
        if not self.repo:
            return False

        try:
            # Check if HEAD is detached
            if self.repo.head.is_detached:
                print("Detected detached HEAD, fixing...")
                # Get the main/master branch
                branch_name = None
                for ref in self.repo.references:
                    if ref.name in ["main", "master"]:
                        branch_name = ref.name
                        break

                if branch_name:
                    self.repo.git.checkout(branch_name)
                    print(f"Checked out {branch_name}")
                    return True
                else:
                    # Create main branch if it doesn't exist
                    self.repo.git.checkout("-b", "main")
                    print("Created and checked out main branch")
                    return True
            return True
        except Exception as e:
            print(f"Could not fix detached HEAD: {e}")
            return False

    def _abort_rebase_if_active(self) -> bool:
        """Abort rebase if one is in progress."""
        try:
            rebase_dir = self.notes_dir / ".git" / "rebase-merge"
            rebase_apply_dir = self.notes_dir / ".git" / "rebase-apply"

            if rebase_dir.exists() or rebase_apply_dir.exists():
                print("Aborting stuck rebase...")
                self.repo.git.rebase("--abort")
                return True
            return True
        except Exception as e:
            print(f"Could not abort rebase: {e}")
            return False

    def _resolve_note_conflicts(self):
        """Automatically resolve conflicts in note files."""
        if not self.repo:
            return False

        try:
            # Get list of conflicted files
            conflicted = []
            for item in self.repo.index.unmerged_blobs().keys():
                conflicted.append(item)

            if not conflicted:
                return True

            # Resolve each conflicted note file
            for file_path in conflicted:
                full_path = self.notes_dir / file_path

                if not full_path.exists() or not str(file_path).endswith(".md.gpg"):
                    # Skip non-note files or deleted files
                    continue

                try:
                    # For encrypted notes, we can't easily merge content
                    # Use the "ours" strategy (keep local version)
                    self.repo.git.checkout("--ours", file_path)
                    self.repo.index.add([file_path])
                    print(f"Resolved conflict in {file_path} (kept local version)")
                except Exception as e:
                    print(f"Could not resolve conflict in {file_path}: {e}")
                    return False

            # Complete the merge
            try:
                if self.repo.index.diff("HEAD"):
                    self.repo.index.commit("Merge remote changes (auto-resolved)")
                    print("Merge completed successfully")
            except Exception as e:
                print(f"Warning: Could not complete merge: {e}")
                return False

            return True

        except Exception as e:
            print(f"Error resolving conflicts: {e}")
            return False

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

        # Fix detached HEAD if present
        if not self._fix_detached_head():
            return False

        # Abort any stuck rebase
        if not self._abort_rebase_if_active():
            return False

        try:
            # Get current branch name
            try:
                current_branch = self.repo.active_branch.name
            except TypeError:
                # HEAD is detached, fix it
                self._fix_detached_head()
                current_branch = self.repo.active_branch.name

            # Pull with current branch using merge strategy (ff-only first)
            origin = self.repo.remotes.origin
            try:
                origin.pull(current_branch, ff_only=True)
                return True
            except git.GitCommandError:
                # Fast-forward failed, try regular merge using git command directly
                # This bypasses any ff=only config that might be set
                self.repo.git.pull("origin", current_branch, no_ff=False)
                return True

        except git.GitCommandError as e:
            error_msg = str(e).lower()

            # Ignore error if remote branch doesn't exist yet (new repo)
            if "couldn't find remote ref" in error_msg:
                return True

            # Handle unrelated histories (initial sync from existing remote)
            if "unrelated histories" in error_msg or "refusing to merge" in error_msg:
                try:
                    current_branch = self.repo.active_branch.name
                    self.repo.git.pull("origin", current_branch, allow_unrelated_histories=True)
                    return True
                except Exception as e2:
                    print(f"Pull with unrelated histories failed: {e2}")
                    return False

            # Handle merge conflicts
            if "conflict" in error_msg or "merge conflict" in error_msg:
                print("Detected conflicts during pull, attempting auto-resolution...")
                if self._resolve_note_conflicts():
                    print("Conflicts resolved successfully")
                    return True
                else:
                    print("Could not auto-resolve conflicts")
                    return False

            # If pull fails due to uncommitted changes
            if "would be overwritten" in error_msg or "overwritten by merge" in error_msg:
                try:
                    # Add and commit any untracked/uncommitted files
                    self.repo.git.add(A=True)
                    if self.repo.is_dirty() or self.repo.untracked_files:
                        self.repo.index.commit("Auto-commit before pull")
                    # Try pull again
                    current_branch = self.repo.active_branch.name
                    origin.pull(current_branch)
                    return True
                except git.GitCommandError as e2:
                    # If there are conflicts after committing, try to resolve them
                    if "conflict" in str(e2).lower():
                        if self._resolve_note_conflicts():
                            return True
                    print(f"Pull failed: {e2}")
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

        # Fix detached HEAD if present
        if not self._fix_detached_head():
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
