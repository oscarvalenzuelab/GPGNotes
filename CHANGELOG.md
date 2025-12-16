# Changelog

All notable changes to GPGNotes will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-12-16

### Added

**Initial Release**
- Self-contained CLI note-taking tool with GPG encryption
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

[0.1.0]: https://github.com/oscarvalenzuelab/gpgnotes/releases/tag/v0.1.0
