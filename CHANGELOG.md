# Changelog

All notable changes to GPGNotes will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.10] - 2025-12-17

### Fixed

- **Plain Note Title Extraction**: Plain (non-encrypted) notes now correctly display their titles in `notes list`. The system now extracts titles from the first H1 heading (`# Title`) in plain files, or falls back to the filename if no H1 heading is found.

### Changed

- **Type Indicators**: Replaced emoji type indicators (📄/🔒) with simple text indicators in `notes list`:
  - `P` for plain (unencrypted) files
  - `E` for encrypted files
- **List Table Layout**: Adjusted column widths for better fit on 80-column terminals (ID: 14, Type: 8, Title: 35, Tags: 20, Modified: 16)

## [0.2.8] - 2025-12-17

### Added

- **Plain File Support**: Full integration of plain (non-encrypted) exported files into the notes system.
  - Plain files are now included in `notes list`, `notes search`, `notes open`, and `notes delete` commands
  - Visual indicators in list view: 📄 for plain files, 🔒 for encrypted files
  - Direct editing of plain files without encryption/decryption overhead
  - Plain files automatically indexed for fast searching
  - Database schema updated with `is_plain` column to track file types
  - Run `notes reindex` after upgrade to index existing plain files

### Fixed

- **Export Sync Issue**: Fixed `notes export --plain` not syncing exported files to git repository. Plain-exported notes are now automatically added and committed when auto-sync is enabled.

### Changed

- `Storage.list_notes()` now accepts `include_plain` parameter to include plain files
- `SearchIndex` now tracks plain file status for proper display in list view
- All index rebuild operations now include plain files by default
- Database automatically migrates to new schema on first run

## [0.2.4] - 2025-12-17

### Added

- **Daily Notes (Captain's Log)**: Quick daily log entries with timestamps and AI-generated summaries (#25).
  - `notes daily "entry"` - Quick append to today's log (no editor opens)
  - `notes daily "entry" --time` - Entry with timestamp prefix (e.g., "14:30 - entry")
  - `notes today` - Open today's daily note in editor
  - `notes yesterday` - Open yesterday's daily note
  - `notes daily show` - View today's entries
  - `notes daily show --week` - View this week's entries
  - `notes daily summary --month` - Generate monthly summary
  - `notes daily summary --week` - Generate weekly summary
  - `notes daily summary --save` - Save summary as a new note
  - LLM-powered summaries with accomplishments, themes, and patterns (requires LLM configuration)
  - Basic stats fallback when LLM not configured
  - Daily notes stored in `daily/YYYY/MM/YYYY-MM-DD.md.gpg`
  - Full interactive mode support

### Documentation

- Added [Daily Notes documentation](docs/daily-notes.md) with usage examples and summary generation guide

## [0.2.3] - 2025-12-17

### Fixed

- **Unicode Encoding Error**: Fixed `latin-1` codec error when creating notes with Unicode characters (smart quotes, em dashes, etc.). The `sanitize_for_gpg()` function is now applied to all note content before encryption, not just during import. Fixes issue where typing characters like `'` would cause "Error creating note" message.

- **Background Sync Crash**: Fixed exception in atexit callback `_background_sync` that caused Click to be re-invoked with note title words as arguments. Removed redundant auto-tagging from the exit callback since it's already performed immediately when notes are created/imported.

## [0.2.2] - 2025-12-17

### Fixed

- **Critical Performance Issue**: Fixed severe performance degradation in `notes list` and `notes search` commands (#37).
  - **Before**: 10-12 seconds for just 8 notes (each note decrypted on every load)
  - **After**: < 0.1 seconds for 8 notes (~100x performance improvement)
  - Added `SearchIndex.get_all_metadata()` method to retrieve metadata from index.db without decryption
  - Rewrote `list()` and `search()` commands to use index queries
  - Only decrypt files when preview is requested and only for the current page
  - Scales efficiently to hundreds of notes with no performance degradation

- **Web Clipper Content Extraction**: Fixed web clipper importing entire HTML structure instead of main content (#36).
  - Enhanced `HTMLToMarkdown` parser to skip non-content tags (nav, header, footer, aside, script, style, etc.)
  - Implemented skip depth tracking to properly ignore nested navigation elements
  - Added support for semantic HTML5 content tags (article, main)
  - Results in clean, focused content extraction without navigation clutter

### Changed

- `notes list` and `notes search` now use database queries for metadata instead of decrypting files
- Web clipper now filters out navigation and structural HTML elements for cleaner notes

## [0.2.1] - 2025-12-17

### Added

- **Interactive Pagination**: Added pagination for `notes list` and `notes search` commands (#19).
  - Interactive navigation with `n` (next page), `p` (previous page), `q` (quit)
  - `--page-size N` option to customize results per page (default: 20)
  - `--no-pagination` flag to disable pagination
  - Displays page counter (e.g., "Page 1 of 5")

- **Note Templates**: Full template system with built-in and custom template support (#22).
  - `notes template list` - List all available templates (built-in and custom)
  - `notes template show <name>` - Preview a template
  - `notes template create <name>` - Create custom template from editor
  - `notes template edit <name>` - Edit custom template
  - `notes template delete <name>` - Delete custom template
  - `notes new --template <name>` - Create note from template
  - `--var key=value` support for template variable substitution
  - 5 built-in templates: meeting, project, bug, journal, research
  - Variable syntax: `{{title}}`, `{{date}}`, `{{datetime}}`, etc.
  - Custom templates stored in `~/.gpgnotes/templates/custom/`

- **Version History**: Git-based version history tracking for notes (#24).
  - `notes history <id>` - Show all versions of a note with commit history
  - `notes show <id> --version <commit>` - View specific version of a note
  - `notes diff <id> --from <commit> --to <commit>` - Compare two versions
  - `notes restore <id> --version <commit>` - Restore note to previous version
  - Decrypts `.gpg` files for readable diffs

- **Markdown Rendering**: Rich markdown preview in terminal (#29).
  - `notes show <id> --render` - Display note with formatted markdown
  - `notes preview <id>` - Shortcut for rendered preview
  - Supports headers, lists, code blocks, links, and formatting

- **URL Import/Web Clipper**: Import web content as notes (#31).
  - `notes import <url>` - Import content from URL
  - `notes clip <url>` - Shortcut alias for web clipping
  - HTML to Markdown conversion with metadata preservation
  - Adds source URL and clipped timestamp to note frontmatter
  - Custom User-Agent header for better compatibility

### Changed

- **Phase 1 Complete**: All Phase 1 (Foundation & Core UX) milestone features implemented.
- Version bump from 0.1.13 to 0.2.1 to reflect new feature set.

### Fixed

- **Diff Display**: Fixed version diff showing encrypted binary data instead of decrypted content.
- **Code Formatting**: Applied `ruff format` to all source files for consistency.
- **Import Order**: Fixed import ordering issues detected by `ruff check`.

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

[0.2.10]: https://github.com/oscarvalenzuelab/GPGNotes/releases/tag/v0.2.10
[0.2.8]: https://github.com/oscarvalenzuelab/GPGNotes/releases/tag/v0.2.8
[0.2.2]: https://github.com/oscarvalenzuelab/GPGNotes/releases/tag/v0.2.2
[0.2.1]: https://github.com/oscarvalenzuelab/GPGNotes/releases/tag/v0.2.1
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
