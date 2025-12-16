# GPGNotes

[![Tests](https://github.com/oscarvalenzuelab/lalanotes/workflows/Tests/badge.svg)](https://github.com/oscarvalenzuelab/lalanotes/actions/workflows/test.yml)
[![Lint](https://github.com/oscarvalenzuelab/lalanotes/workflows/Lint/badge.svg)](https://github.com/oscarvalenzuelab/lalanotes/actions/workflows/lint.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

A self-contained CLI note-taking tool with GPG encryption, automatic tagging, full-text search, and Git synchronization.

## Features

- **Markdown Notes** - Write notes in plain markdown with YAML frontmatter
- **GPG Encryption** - Every note is encrypted individually with GPG
- **Full-Text Search** - Fast SQLite FTS5-powered search across all notes
- **Auto-Tagging** - Intelligent tag generation using TF-IDF
- **Git Sync** - Automatic synchronization with private GitHub repositories

## Installation

### Prerequisites

- Python 3.11 or higher
- GPG (GnuPG) installed on your system
  - **Linux**: `sudo apt install gnupg` (Debian/Ubuntu) or `sudo yum install gnupg` (RedHat/CentOS)
  - **macOS**: `brew install gnupg`

### Install from PyPI (coming soon)

```bash
pip install gpgnotes
```

### Install from source

```bash
git clone https://github.com/oscarvalenzuelab/lalanotes.git
cd lalanotes
pip install -e .
```

## Quick Start

### 1. Run Initial Setup

On first run, GPGNotes will guide you through interactive setup:

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

# Open/edit a note
notes open <note-id>

# List all notes
notes list

# Show all tags
notes tags

# Export a note
notes export <note-id> --format markdown
notes export <note-id> --format html -o output.html
notes export <note-id> --format json

# Delete a note
notes delete <note-id>

# Sync with Git
notes sync

# Rebuild search index
notes reindex

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

GPGNotes stores everything in `~/.gpgnotes/`:

```
~/.gpgnotes/
├── config.json          # Configuration file
├── notes.db            # Search index (SQLite)
├── .git/               # Git repository
└── notes/              # Your encrypted notes
    ├── 2025/
    │   ├── 01/
    │   │   ├── 20250115103000.md.gpg
    │   │   └── 20250115143500.md.gpg
    │   └── 12/
    │       └── 20251215091200.md.gpg
```

Each note is:
- **Encrypted** with your GPG key
- **Organized** by creation date (YYYY/MM/)
- **Named** using timestamp (YYYYMMDDHHmmss)
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

The frontmatter is managed automatically by GPGNotes.

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `editor` | Text editor for notes | `$EDITOR` or `nano` |
| `git_remote` | Git remote URL | Not set |
| `gpg_key` | GPG key ID for encryption | Not set (required) |
| `auto_sync` | Auto-sync after changes | `true` |
| `auto_tag` | Auto-generate tags | `true` |

## Git Synchronization

GPGNotes uses Git for synchronization:

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

GPGNotes automatically generates tags using TF-IDF (Term Frequency-Inverse Document Frequency):

- Analyzes note title and content
- Extracts most relevant keywords
- Filters out common stop words
- Suggests 3-5 meaningful tags

You can always edit tags manually by editing the note's frontmatter.

## Spell Checking in Your Editor

GPGNotes uses your preferred text editor (vim, nano, etc.) which already have spell checking built-in:

**Vim/Vi:**
```vim
:set spell spelllang=en_us    " Enable spell check
:set nospell                  " Disable spell check
z=                            " View suggestions for word under cursor
]s                            " Jump to next misspelled word
[s                            " Jump to previous misspelled word
```

**Nano:**
```bash
nano -S                       " Start nano with spell checking
Ctrl+T                        " Check spelling while editing
```

**Add to your shell profile** to always enable spell checking:
```bash
# For vim users (~/.vimrc)
autocmd FileType markdown setlocal spell spelllang=en_us

# For nano users (~/.nanorc)
set speller "aspell -c"
```

No external dependencies needed - the editor you already use has spell checking!

## Security

- **Encryption**: All notes are encrypted with GPG (AES256)
- **Local-first**: Everything stored locally, you control the data
- **Private repos**: Git sync designed for private repositories
- **No cloud service**: No external services or API calls
- **Passphrase**: Your GPG passphrase protects everything

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

---

**Note**: This is an early release (v0.1.0). Expect bugs and breaking changes. Always backup your notes!
