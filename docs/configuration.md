# Configuration

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

### Setting Options

```bash
# Show current configuration
notes config --show

# Set editor
notes config --editor vim
notes config --editor nano
notes config --editor "code --wait"

# Enable/disable auto-sync
notes config --auto-sync
notes config --no-auto-sync

# Enable/disable auto-tagging
notes config --auto-tag
notes config --no-auto-tag

# Set Git remote
notes config --git-remote git@github.com:user/notes.git

# Set LLM provider
notes config --llm-provider openai
notes config --llm-provider ollama
```

## Git Synchronization

GPGNotes uses Git for synchronization:

1. **Auto-commit**: Every change creates a commit
2. **Smart sync**: Pulls before pushing
3. **Conflict resolution**: Automatic merge when possible
4. **Private repos**: Designed for private GitHub/GitLab repos

### Setting Up Git Sync

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

### Manual Sync

```bash
notes sync
```

## Auto-Tagging

GPGNotes automatically generates tags using TF-IDF (Term Frequency-Inverse Document Frequency):

- Analyzes note title and content
- Extracts most relevant keywords
- Filters out common stop words
- Suggests 3-5 meaningful tags

You can always edit tags manually by editing the note's frontmatter.

### Disable Auto-Tagging

```bash
notes config --no-auto-tag
```

## Directory Structure

GPGNotes stores everything in `~/.gpgnotes/`:

```
~/.gpgnotes/
├── config.json          # Configuration file
├── notes.db             # Search index (SQLite)
└── notes/               # Git repository with encrypted notes
    ├── .git/
    ├── 2025/
    │   ├── 01/
    │   │   ├── 20250115103000.md.gpg
    │   │   └── 20250115143500.md.gpg
    │   └── 12/
    │       └── 20251215091200.md.gpg
    └── plain/           # Optional plain text exports
```

Each note is:
- **Encrypted** with your GPG key
- **Organized** by creation date (YYYY/MM/)
- **Named** using timestamp (YYYYMMDDHHmmss)
- **Indexed** for fast searching
