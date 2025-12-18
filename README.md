# GPGNotes

[![Tests](https://github.com/oscarvalenzuelab/GPGNotes/workflows/Tests/badge.svg)](https://github.com/oscarvalenzuelab/GPGNotes/actions/workflows/test.yml)
[![Lint](https://github.com/oscarvalenzuelab/GPGNotes/workflows/Lint/badge.svg)](https://github.com/oscarvalenzuelab/GPGNotes/actions/workflows/lint.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

A CLI note-taking tool with GPG encryption, automatic tagging, full-text search, and Git synchronization.

## Features

- **Markdown Notes** - Write notes in plain markdown with YAML frontmatter
- **GPG Encryption** - Every note is encrypted individually with GPG
- **Full-Text Search** - Fast SQLite FTS5-powered search across all notes
- **Auto-Tagging** - Intelligent tag generation using TF-IDF
- **Folders** - Tag-based virtual folders for organizing notes
- **Todo Tracking** - Aggregate tasks from markdown checkboxes across all notes
- **Git Sync** - Automatic synchronization with private GitHub repositories
- **Daily Notes** - Captain's Log style quick entries with summaries ([docs](docs/daily-notes.md))
- **Note Templates** - Built-in templates (meeting, project, bug, journal, research) with custom template support
- **Version History** - Git-based version tracking with history, diff, and restore commands
- **Markdown Rendering** - Rich terminal preview with formatted display
- **URL Import** - Web clipper to import content from URLs
- **Pagination** - Interactive pagination for list and search results
- **AI Enhancement** - Optional LLM-powered note refinement ([docs](docs/ai-enhancement.md))
- **Import/Export** - Support for PDF, DOCX, RTF formats ([docs](docs/import-export.md))

## Installation

### Prerequisites

- Python 3.11 or higher
- GPG (GnuPG) installed on your system
  - **Linux**: `sudo apt install gnupg` (Debian/Ubuntu)
  - **macOS**: `brew install gnupg`

### Install from PyPI

```bash
pip install gpgnotes
```

With optional dependencies:
```bash
pip install gpgnotes[llm]      # AI enhancement
pip install gpgnotes[import]   # PDF/DOCX import/export
```

### Install from source

```bash
git clone https://github.com/oscarvalenzuelab/GPGNotes.git
cd GPGNotes
pip install -e .
```

## Quick Start

### 1. Initialize

```bash
notes init
```

This guides you through:
- Selecting a GPG key
- Testing encryption
- Configuring your editor
- Setting up Git sync (optional)

**Don't have a GPG key?** Create one:
```bash
gpg --full-generate-key
```

### 2. Create a note

```bash
notes new "My First Note"
```

### 3. Search and manage

```bash
notes search "keyword"
notes list
notes open <note-id>
notes sync
```

## Command Reference

| Command | Description |
|---------|-------------|
| `notes new "Title"` | Create a new note |
| `notes new --template meeting` | Create note from template |
| `notes new --folder work` | Create note in folder |
| `notes list` | List all notes |
| `notes list --preview` | List with content preview |
| `notes list --folder work` | List notes in folder |
| `notes list --page-size 10` | List with custom pagination |
| `notes recent` | Show 5 most recent notes |
| `notes search "query"` | Full-text search |
| `notes search --tag work` | Search by tag |
| `notes search --folder work` | Search within folder |
| `notes folders` | List all folders with counts |
| `notes move <id> --folder work` | Add note to folder |
| `notes move <id> --unfolder work` | Remove note from folder |
| `notes todos` | List incomplete tasks |
| `notes todos --all` | Include completed tasks |
| `notes todos --folder work` | Tasks from specific folder |
| `notes open <id>` | Open note by ID |
| `notes open "title"` | Open by title (fuzzy match) |
| `notes open --last` | Open most recent note |
| `notes show <id> --render` | Display note with formatting |
| `notes preview <id>` | Rich markdown preview |
| `notes history <id>` | Show version history |
| `notes diff <id> --from <commit>` | Compare versions |
| `notes restore <id> --version <commit>` | Restore previous version |
| `notes template list` | List all templates |
| `notes template show <name>` | Preview a template |
| `notes tags` | List all tags |
| `notes delete <id>` | Delete a note |
| `notes sync` | Sync with Git |
| `notes config --show` | Show configuration |
| `notes daily "entry"` | Quick daily log entry ([docs](docs/daily-notes.md)) |
| `notes daily --time "entry"` | Entry with timestamp |
| `notes today` | Open today's daily note |
| `notes yesterday` | Open yesterday's note |
| `notes daily show` | View today's entries |
| `notes daily summary --month` | Generate monthly summary |
| `notes enhance <id>` | AI enhancement ([docs](docs/ai-enhancement.md)) |
| `notes import file.pdf` | Import file ([docs](docs/import-export.md)) |
| `notes import <url>` | Import from URL (web clipper) |
| `notes clip <url>` | Web clipper shortcut |
| `notes export <id>` | Export note ([docs](docs/import-export.md)) |

### Interactive Mode

Run `notes` without arguments for interactive mode with:
- Tab completion for note titles
- Command history (Up/Down arrows)
- Quick search by typing

## Security

- **GPG Encryption**: All notes encrypted with AES256
- **Local-first**: Your data stays on your machine
- **Private repos**: Git sync for private repositories only
- **Encrypted secrets**: API keys stored with GPG encryption

## Documentation

- [Configuration & Note Format](docs/configuration.md)
- [Daily Notes (Captain's Log)](docs/daily-notes.md)
- [AI Enhancement](docs/ai-enhancement.md)
- [Import & Export](docs/import-export.md)
- [Spell Checking](docs/spell-checking.md)

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

---

**Note**: This is an early release. Always backup your notes!
