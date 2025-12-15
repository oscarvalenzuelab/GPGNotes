# NotesCLI

A self-contained CLI note-taking tool with GPG encryption, automatic tagging, full-text search, and Git synchronization.

## Features

- 📝 **Markdown Notes** - Write notes in plain markdown with YAML frontmatter
- 🔒 **GPG Encryption** - Every note is encrypted individually with GPG
- 🔍 **Full-Text Search** - Fast SQLite FTS5-powered search across all notes
- 🏷️ **Auto-Tagging** - Intelligent tag generation using TF-IDF
- 🔄 **Git Sync** - Automatic synchronization with private GitHub repositories
- 📅 **Date-Based Organization** - Notes organized by year/month automatically
- 💻 **Cross-Platform** - Works on Linux, macOS, and Windows
- 🎨 **Rich CLI** - Beautiful terminal interface with interactive mode
- 🚀 **Self-Contained** - No external dependencies or services required

## Installation

### Prerequisites

- Python 3.8 or higher
- GPG (GnuPG) installed on your system
  - **Linux**: `sudo apt install gnupg` (Debian/Ubuntu) or `sudo yum install gnupg` (RedHat/CentOS)
  - **macOS**: `brew install gnupg`
  - **Windows**: Download from [GnuPG.org](https://gnupg.org/download/)

### Install from PyPI (coming soon)

```bash
pip install notescli
```

### Install from source

```bash
git clone https://github.com/oscarvalenzuelab/notescli.git
cd notescli
pip install -e .
```

## Quick Start

### 1. Run Initial Setup

On first run, NotesCLI will guide you through interactive setup:

```bash
notes init
```

This will:
- Help you select a GPG key (or guide you to create one)
- Test encryption/decryption
- Configure your preferred editor
- Optionally set up Git sync
- Configure auto-sync and auto-tagging

**Don't have a GPG key?** Create one first:

```bash
gpg --full-generate-key
```

Choose the defaults (RSA, 3072 bits, no expiration). Remember your passphrase!

### 2. Create your first note

```bash
notes new "My First Note"
```

This will open your configured editor. Write your note, save, and exit.

### 3. Search and manage your notes

```bash
notes search "first"
notes search --tag important
notes list
notes sync  # Sync with Git (if configured)
```

## Usage

### Command Mode

```bash
# Create a new note
notes new "Meeting Notes" --tags "work,meetings"

# Search notes
notes search "project ideas"
notes search --tag work

# Edit a note
notes edit "meeting notes"

# List all notes
notes list

# Show all tags
notes tags

# Sync with Git
notes sync

# Rebuild search index
notes reindex

# Check spelling in notes (optional feature)
notes spellcheck           # Check all notes
notes spellcheck "query"   # Check specific notes

# Show configuration
notes config --show

# Update configuration
notes config --editor nano
notes config --auto-sync
notes config --no-auto-tag

# Re-run initial setup
notes init
```

### Interactive Mode

Simply run `notes` without any command to enter interactive mode:

```bash
notes
```

In interactive mode, you can:
- Type any text to search
- Use commands: `new`, `list`, `tags`, `sync`, `config`, `exit`
- Navigate results with tab completion

## Directory Structure

NotesCLI stores everything in `~/.notecli/`:

```
~/.notecli/
├── config.json          # Configuration file
├── notes.db            # Search index (SQLite)
├── .git/               # Git repository
└── notes/              # Your encrypted notes
    ├── 2025/
    │   ├── 01/
    │   │   ├── 2025-01-15-my-first-note.md.gpg
    │   │   └── 2025-01-15-meeting-notes.md.gpg
    │   └── 12/
    │       └── 2025-12-15-project-ideas.md.gpg
```

Each note is:
- **Encrypted** with your GPG key
- **Organized** by creation date (YYYY/MM/)
- **Named** using date + slugified title
- **Indexed** for fast searching

## Note Format

Notes use Markdown with YAML frontmatter:

```markdown
---
title: My Note Title
tags:
  - tag1
  - tag2
created: 2025-12-15T10:30:00
modified: 2025-12-15T10:35:00
---

# Your Note Content

This is the body of your note in **Markdown** format.

- Lists work
- Links work: [example](https://example.com)
- Code blocks work

## More sections...
```

The frontmatter is managed automatically by NotesCLI.

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `editor` | Text editor for notes | `$EDITOR` or `nano` |
| `git_remote` | Git remote URL | Not set |
| `gpg_key` | GPG key ID for encryption | Not set (required) |
| `auto_sync` | Auto-sync after changes | `true` |
| `auto_tag` | Auto-generate tags | `true` |

## Git Synchronization

NotesCLI uses Git for synchronization:

1. **Auto-commit**: Every change creates a commit
2. **Smart sync**: Pulls before pushing
3. **Conflict resolution**: Automatic merge when possible
4. **Private repos**: Designed for private GitHub/GitLab repos

### Setting up Git sync

1. Create a private repository on GitHub
2. Configure the remote:
   ```bash
   notes config --git-remote git@github.com:yourusername/notes.git
   ```
3. Enable auto-sync:
   ```bash
   notes config --auto-sync
   ```

Now every note change will automatically sync with your repository!

## Auto-Tagging

NotesCLI automatically generates tags using TF-IDF (Term Frequency-Inverse Document Frequency):

- Analyzes note title and content
- Extracts most relevant keywords
- Filters out common stop words
- Suggests 3-5 meaningful tags

You can always edit tags manually by editing the note's frontmatter.

## Spell Checking (Optional)

NotesCLI includes optional spell checking support. To enable it:

```bash
pip install notescli[spellcheck]
```

Then use the spellcheck command:

```bash
# Check spelling in all notes
notes spellcheck

# Check spelling in specific notes
notes spellcheck "meeting"
```

The spell checker will:
- Identify potentially misspelled words
- Provide suggestions for corrections
- Ignore markdown syntax and code blocks
- Skip YAML frontmatter

**Note**: The spell checker uses `pyspellchecker` which downloads dictionaries on first use.

## Security

- **Encryption**: All notes are encrypted with GPG (AES256)
- **Local-first**: Everything stored locally, you control the data
- **Private repos**: Git sync designed for private repositories
- **No cloud service**: No external services or API calls
- **Passphrase**: Your GPG passphrase protects everything

## Development

### Setup development environment

```bash
git clone https://github.com/oscarvalenzuelab/notescli.git
cd notescli
pip install -e ".[dev]"
```

### Run tests

```bash
pytest
```

### Code formatting

```bash
ruff check src/
ruff format src/
```

## Roadmap

- [ ] Export notes to various formats (PDF, HTML, etc.)
- [ ] Note templates
- [ ] Attachments support
- [ ] Mobile companion app
- [ ] Web interface
- [ ] End-to-end encrypted sync server
- [ ] Collaborative notes (shared encryption)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

## Author

**Oscar Valenzuela B.**
- Email: oscar.valenzuela.b@gmail.com
- GitHub: [@oscarvalenzuelab](https://github.com/oscarvalenzuelab)

## Acknowledgments

Inspired by:
- [Evernote](https://evernote.com/) - For pioneering digital note-taking
- [Notion](https://notion.so/) - For modern note organization
- [Standard Notes](https://standardnotes.com/) - For encrypted notes
- [Obsidian](https://obsidian.md/) - For markdown-based notes
- [Joplin](https://joplinapp.org/) - For open-source encrypted notes

---

**Note**: This is an early release (v0.1.0). Expect bugs and breaking changes. Always backup your notes!
