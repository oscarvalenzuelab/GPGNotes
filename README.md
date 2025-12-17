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
- **Git Sync** - Automatic synchronization with private GitHub repositories
- **AI Enhancement** - Optional LLM-powered note refinement (OpenAI, Ollama)

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
git clone https://github.com/oscarvalenzuelab/GPGNotes.git
cd GPGNotes
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
notes open "meeting"    # Fuzzy match by title
notes open --last       # Open most recent

# List all notes
notes list
notes list --preview              # Show content preview
notes list --sort title           # Sort by title
notes list --tag work --limit 10  # Filter and limit

# Recent notes (shortcut)
notes recent         # Last 5 notes
notes recent -n 10   # Last 10 notes

# Show all tags
notes tags

# Export a note
notes export <note-id> --format markdown
notes export <note-id> --format html -o output.html
notes export <note-id> --format json
notes export <note-id> --format pdf -o output.pdf   # requires [import] extras
notes export <note-id> --format docx -o output.docx # requires [import] extras
notes export <note-id> --plain                       # export to plain/ folder

# Import external files (requires [import] extras)
notes import document.pdf
notes import report.docx --title "Q4 Report" --tags work,quarterly
notes import *.md  # batch import

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

# AI-powered note enhancement (requires llm extras)
notes enhance <note-id>                                      # Interactive mode
notes enhance <note-id> --instructions "Fix grammar" --quick # Quick mode

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
- Use commands: `new`, `list`, `recent`, `open`, `tags`, `sync`, `config`, `exit`
- Tab-complete note titles after `open`, `delete`, `export`, `enhance`
- Use Up/Down arrows to navigate command history

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
| `llm_provider` | LLM provider (openai, ollama) | Not set |
| `llm_model` | LLM model name | Provider default |
| `llm_key` | API key (GPG-encrypted) | Not set |

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

## File Import & Export (Optional)

GPGNotes can import external files and export notes to various formats including PDF and DOCX.

### Installation

**If installed with pip:**

```bash
pip install gpgnotes[import]
```

**If installed with pipx:**

```bash
# Option 1: Install with extras (new install)
pipx install gpgnotes[import]

# Option 2: Inject into existing install
pipx inject gpgnotes python-docx pypdf striprtf reportlab
```

### Importing Files

Import external documents as encrypted notes:

```bash
# Import a single file
notes import document.pdf

# Import with custom title and tags
notes import report.docx --title "Q4 Report" --tags work,quarterly

# Batch import multiple files
notes import *.md
```

**Supported formats:** `.md`, `.txt`, `.rtf`, `.pdf`, `.docx`

### Exporting Notes

Export notes to various formats:

```bash
# Text-based formats (output to stdout or file)
notes export <note-id> --format markdown
notes export <note-id> --format html -o output.html
notes export <note-id> --format json
notes export <note-id> --format rtf -o output.rtf

# Binary formats (require output file)
notes export <note-id> --format pdf -o output.pdf
notes export <note-id> --format docx -o output.docx
```

### Plain Folder Export

Export notes to a readable `plain/` folder that syncs with Git:

```bash
notes export <note-id> --plain
```

This exports to `~/.gpgnotes/plain/YYYY/MM/filename.md`, mirroring the notes structure. These files:
- Are unencrypted and human-readable
- Sync with Git alongside your encrypted notes
- Are viewable directly on GitHub as formatted markdown

## AI-Powered Note Enhancement (Optional)

GPGNotes includes optional AI-powered note enhancement to improve your writing. This feature supports multiple LLM providers and uses a human-in-the-loop workflow for iterative refinement.

### Installation

**If installed with pip:**

```bash
pip install gpgnotes[llm]
```

**If installed with pipx:**

You need to inject the LLM dependencies into the GPGNotes virtual environment:

```bash
pipx inject gpgnotes openai anthropic ollama
```

Or inject only what you need:

```bash
pipx inject gpgnotes openai    # For OpenAI only
pipx inject gpgnotes ollama    # For Ollama only
```

### Supported Providers

- **OpenAI** (GPT-4, GPT-4o, GPT-4o-mini) - Cloud-based, requires API key
- **Ollama** (llama3.1, etc.) - Local LLM, no API key needed

### Setup

**For OpenAI:**

```bash
notes config --llm-provider openai
notes config --llm-key sk-your-api-key-here
notes config --llm-model gpt-4o-mini  # Optional, defaults to gpt-4o-mini
```

API keys are encrypted with your GPG key and stored securely.

**For Ollama (local):**

First, [install Ollama](https://ollama.ai/) and pull a model:

```bash
ollama pull llama3.1
```

Then configure GPGNotes:

```bash
notes config --llm-provider ollama
notes config --llm-model llama3.1  # Optional, defaults to llama3.1
```

### Usage

**Interactive mode** (recommended):

```bash
notes enhance <note-id>
```

This opens an interactive workflow where you can:
- Choose from enhancement presets (grammar, clarity, conciseness, tone, structure)
- Provide custom instructions
- Iterate with new instructions to refine the output
- View diffs between original and enhanced versions
- Navigate version history (back/forward)
- Accept or reject changes

**Quick mode** (auto-apply):

```bash
notes enhance <note-id> --instructions "Fix grammar and spelling" --quick
```

### Enhancement Presets

1. **Fix grammar and spelling** - Correct errors while maintaining tone
2. **Improve clarity** - Make text easier to understand
3. **Make more concise** - Remove redundancy
4. **Make more professional** - Formal, structured tone
5. **Make more casual** - Conversational tone
6. **Add structure** - Organize with bullet points and headings

### Security Note

- OpenAI API keys are encrypted with GPG before storage
- Ollama runs entirely locally (no data sent to external services)
- Note content is sent to the LLM provider for enhancement (except Ollama)

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
- **Encrypted secrets**: API keys stored encrypted with GPG
- **Passphrase**: Your GPG passphrase protects everything
- **Optional cloud**: LLM features are opt-in and use Ollama by default (local)

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

---

**Note**: This is an early release. Expect bugs and breaking changes. Always backup your notes!
