# Changelog

All notable changes to GPGNotes will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.12] - 2025-12-16

### Fixed

- **List Display**: Fixed table wrapping in `notes list` - entries now display on single lines with proper truncation using `no_wrap=True`.

### Changed

- **Documentation Reorganization**: Moved detailed documentation to `docs/` folder for cleaner README.
  - `docs/ai-enhancement.md` - AI/LLM configuration and usage
  - `docs/import-export.md` - File import and export details
  - `docs/configuration.md` - Note format, config options, Git sync
  - `docs/spell-checking.md` - Editor spell checking guides

## [0.1.11] - 2025-12-16

### Fixed

- **Plain Export Sync**: Fixed `--plain` export path to be inside the git repository (`notes/plain/`) so files sync correctly with `notes sync`.

## [0.1.10] - 2025-12-16

### Added

- **Open Most Recent Note**: `notes open --last` opens the most recently modified note.
- **Title-Based Fuzzy Matching**: Open notes by title with `notes open "meeting"` - shows matches for selection.
- **Enhanced List Command**: New options for `notes list`:
  - `--preview` / `-p`: Show first line of content
  - `--sort` / `-s`: Sort by `modified`, `created`, or `title`
  - `--limit` / `-n`: Set maximum notes to display
  - `--tag` / `-t`: Filter notes by tag
- **Recent Notes Command**: `notes recent` as shortcut for `notes list --sort modified -n 5`.
- **Note Title Autocomplete**: Tab completion for note titles in interactive mode after `open`, `delete`, `export`, `enhance` commands.

### Changed

- **Interactive Mode**: Updated help text to reflect new features and autocomplete capability.

## [0.1.9] - 2025-12-16

### Fixed

- **PDF Export Dependency**: Added missing `reportlab` to `[import]` optional dependencies for PDF export.
- **Documentation**: Clarified pipx installation instructions with both `pipx install gpgnotes[import]` and `pipx inject` options.

## [0.1.8] - 2025-12-16

### Added

- **File Import**: Import external files as encrypted notes with `notes import` command.
  - Supported formats: `.md`, `.txt`, `.rtf`, `.pdf`, `.docx`
  - Auto-detect titles from document content/metadata
  - Batch import with glob patterns (e.g., `notes import *.md`)
  - Optional `--title` and `--tags` flags
  - Available in both CLI and interactive mode

- **Extended Export Formats**: Added RTF, PDF, and DOCX export formats.
  - `notes export <id> --format pdf -o output.pdf`
  - `notes export <id> --format docx -o report.docx`
  - `notes export <id> --format rtf -o document.rtf`

- **Plain Folder Export**: Export notes to readable `plain/` folder with `--plain` flag.
  - Files sync with git and are viewable on GitHub
  - Mirrors notes directory structure (YYYY/MM/filename.md)

- **Command History**: Arrow key navigation through previous commands in interactive mode.
  - Persistent history saved to `~/.gpgnotes/command_history`
  - `history [N]` command to show last N commands

- **CONTRIBUTING.md**: Added contributor guidelines with development setup, code style, and PR process.

### Fixed

- **Workflow Security**: Added explicit `permissions: contents: read` to GitHub Actions workflows (resolves security scan alerts).
- **Mypy Path**: Fixed incorrect path in lint workflow (`src/lalanotes` → `src/gpgnotes`).

### Changed

- **Optional Dependencies**: Added `[import]` optional dependency group for document parsing (python-docx, pypdf, striprtf).
- **Export Refactor**: Refactored export command to use new exporter module for cleaner code organization.

## [0.1.7] - 2025-12-16

### Fixed

- **LLM Encoding Error**: Fixed `latin-1` codec error when saving LLM-enhanced notes. Added `sanitize_llm_output()` function to convert Unicode characters (smart quotes, em dashes, ellipsis, etc.) to ASCII equivalents before GPG encryption. Fixes #1.

## [0.1.6] - 2025-12-16

### Fixed

- **Menu Display in Enhancement UI**: Fixed interactive menus not displaying option keys ([a], [r], etc.) when using prompt_toolkit. Replaced Rich console.print with plain print() for reliable rendering across terminals.

### Added

- **Interactive Mode Support for Enhance**: Added `enhance <ID>` command to interactive mode with tab completion and help documentation.

## [0.1.5] - 2025-12-16

### Fixed

- **Interactive Menu Display**: Fixed enhancement UI menus not showing option keys ([a], [r], etc.) in some terminals. Replaced Rich Table with direct console printing for better compatibility.
- **Tip Message**: Fixed "notes view" command reference to correct "notes open" command.

### Changed

- **Default OpenAI Model**: Changed default from `gpt-4` to `gpt-4o-mini` (more modern, cost-effective).
- **Auto-Set Model**: When setting `--llm-provider` without `--llm-model`, automatically sets provider's default model to prevent mismatches.

### Added

- **LLM Documentation**: Added comprehensive AI enhancement documentation to README including:
  - Installation instructions for both pip and pipx users
  - Setup guides for OpenAI and Ollama
  - Usage examples and enhancement presets
  - Security notes about API key encryption
- **Configuration Table**: Added LLM-related options to configuration reference table.

## [0.1.4] - 2025-12-16

### Added

- **LLM Enhancement**: AI-powered note enhancement with support for OpenAI and Ollama providers.
- **Interactive Refinement**: Human-in-the-loop workflow with iterative improvements, version history, and diff viewing.
- **GPG-Encrypted Secret Storage**: Secure API key storage using GPG encryption for LLM providers.
- **Enhancement Presets**: Quick enhancement options (grammar fix, clarity, conciseness, tone adjustment, structure).
- **Custom Instructions**: Support for custom enhancement instructions in both interactive and quick modes.
- **Text Wrapping**: Automatic text wrapping at 80 columns for vim, nano, and emacs.
- **Markdown Editor Support**: Vim/neovim now opens with markdown syntax highlighting, spell check, and proper wrapping.

### Fixed

- **Config Command in Interactive Mode**: Fixed AttributeError when running `config` command in interactive mode.
- **Editor Configuration**: Fixed infinite single-line notes by adding proper text wrapping configuration.
- **Vim Markdown Support**: Vim now properly handles markdown formatting (bold, italic) with syntax highlighting.

### Changed

- LLM dependencies are now optional (install with `pip install gpgnotes[llm]`).
- Editor commands now include appropriate flags for optimal markdown editing experience.

## [0.1.3] - 2025-12-16

### Fixed

- **Detached HEAD State**: Fixed critical issue where git operations left repository in detached HEAD state, preventing push operations.
- **Rebase Failures**: Switched from rebase to merge strategy for encrypted binary files, eliminating "could not apply" errors.
- **Stuck Rebase Operations**: Added automatic detection and abort of stuck rebase operations before pull.
- **HEAD Reference Errors**: Fixed "HEAD is a detached symbolic reference" errors during pull and push.

### Changed

- Git pull now uses merge strategy instead of rebase (safer for encrypted files).
- Pull attempts fast-forward merge first, falls back to regular merge if needed.
- Automatic detached HEAD detection and fix before all git operations.

## [0.1.2] - 2025-12-16

### Added

- **Auto-sync Before Opening**: `notes open` now syncs before opening to get the latest version of the note from remote.
- **Auto-sync After Editing**: Changes are automatically synced after editing a note, ensuring immediate backup.
- **Automatic Conflict Resolution**: Conflicts during pull/rebase are now resolved automatically by keeping the local version.
- **Index Rebuild After Sync**: Search index is automatically rebuilt after pulling notes to ensure all notes are searchable.

### Fixed

- **Divergent Branches Error**: Fixed "fatal: Need to specify how to reconcile divergent branches" by configuring Git to use rebase strategy with auto-stash.
- **Concurrent Editing**: Improved handling of concurrent edits across multiple devices by automatically resolving conflicts.
- **Failed Pushes After Conflicts**: Fixed push failures that occurred after pull conflicts by completing rebase automatically.

### Changed

- Git pull now uses rebase strategy instead of merge to maintain cleaner history.
- Local changes are automatically stashed and reapplied during pull operations.

## [0.1.1] - 2025-12-16

### Fixed

- **Git Sync on New Computer**: Fixed critical issue where `notes sync` wouldn't pull existing notes when setting up on a new computer. The `init_repo` now properly fetches and checks out the remote branch before creating any local commits.
- **Git Push Upstream**: Fixed "no upstream branch" error on first push by automatically setting upstream when pushing to a new remote.
- **Auto-Reindex After Sync**: Added automatic search index rebuild after `notes sync` to ensure pulled notes appear in search results and `notes list`.

### Changed

- Removed "self-contained" from project description (the tool requires system GPG installation, so it's not fully self-contained).

## [0.1.0] - 2025-12-16

### Added

**Initial Release**
- CLI note-taking tool with GPG encryption
- Full-text search powered by SQLite FTS5
- Automatic tag generation using TF-IDF analysis
- Git synchronization for backup and multi-device sync
- Markdown notes with YAML frontmatter support
- Date-based organization (YYYY/MM) for encrypted notes
- Interactive CLI mode with command completion

**Core Features**
- Individual GPG encryption for each note
- Fast search across all encrypted notes
- Intelligent auto-tagging based on content
- Export notes to markdown, HTML, JSON, and text formats
- Note management (create, open, edit, delete, list)
- Tag browsing and filtering
- Configuration management with sensible defaults

**CLI Commands**
- `notes init` - Interactive setup with GPG key configuration
- `notes new` - Create new encrypted notes
- `notes open` - Open and edit existing notes
- `notes search` - Full-text search with tag filtering
- `notes list` - List all notes
- `notes tags` - Show all tags
- `notes export` - Export notes to various formats
- `notes delete` - Delete notes
- `notes sync` - Git synchronization
- `notes reindex` - Rebuild search index
- `notes config` - Manage configuration

**Security**
- GPG (AES256) encryption for all notes
- Local-first design with no external services
- Private Git repository support
- Passphrase-protected encryption keys

**Platform Support**
- Linux (tested on Ubuntu)
- macOS (tested on macOS latest)
- Python 3.11 and 3.12

### Technical Details
- Built with Click for CLI framework
- Rich library for beautiful terminal output
- GitPython for Git operations
- python-gnupg for encryption
- scikit-learn for TF-IDF tag generation
- Comprehensive test suite (29 tests, 32% coverage)
- GitHub Actions CI/CD pipeline
- Configuration stored in `~/.gpgnotes/`

### Known Limitations
- Interactive GPG passphrase entry required for encryption operations
- Windows platform not currently supported
- Sync requires Git remote to be configured manually
- Initial sync from existing remote requires `--allow-unrelated-histories` (handled automatically)

[0.1.12]: https://github.com/oscarvalenzuelab/GPGNotes/releases/tag/v0.1.12
[0.1.11]: https://github.com/oscarvalenzuelab/GPGNotes/releases/tag/v0.1.11
[0.1.10]: https://github.com/oscarvalenzuelab/GPGNotes/releases/tag/v0.1.10
[0.1.9]: https://github.com/oscarvalenzuelab/GPGNotes/releases/tag/v0.1.9
[0.1.8]: https://github.com/oscarvalenzuelab/GPGNotes/releases/tag/v0.1.8
[0.1.7]: https://github.com/oscarvalenzuelab/GPGNotes/releases/tag/v0.1.7
[0.1.6]: https://github.com/oscarvalenzuelab/GPGNotes/releases/tag/v0.1.6
[0.1.5]: https://github.com/oscarvalenzuelab/GPGNotes/releases/tag/v0.1.5
[0.1.4]: https://github.com/oscarvalenzuelab/GPGNotes/releases/tag/v0.1.4
[0.1.3]: https://github.com/oscarvalenzuelab/GPGNotes/releases/tag/v0.1.3
[0.1.2]: https://github.com/oscarvalenzuelab/GPGNotes/releases/tag/v0.1.2
[0.1.1]: https://github.com/oscarvalenzuelab/GPGNotes/releases/tag/v0.1.1
[0.1.0]: https://github.com/oscarvalenzuelab/GPGNotes/releases/tag/v0.1.0
