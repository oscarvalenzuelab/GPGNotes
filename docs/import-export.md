# File Import & Export

GPGNotes can import external files and export notes to various formats including PDF and DOCX.

## Installation

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

## Importing Files

Import external documents as encrypted notes:

```bash
# Import a single file
notes import document.pdf

# Import with custom title and tags
notes import report.docx --title "Q4 Report" --tags work,quarterly

# Batch import multiple files
notes import *.md
```

### Supported Import Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| Markdown | `.md` | Title from first heading |
| Plain Text | `.txt` | Title from filename |
| Rich Text | `.rtf` | Requires striprtf |
| PDF | `.pdf` | Requires pypdf |
| Word Document | `.docx` | Requires python-docx |

## URL Import (Web Clipper)

Import content directly from web pages as encrypted notes:

```bash
# Import from URL
notes import https://example.com/article

# Use the clip shortcut
notes clip https://blog.example.com/post

# Import with custom title
notes import https://example.com --title "My Custom Title"
```

### Features

- **HTML to Markdown conversion** - Automatically converts web content to markdown format
- **Automatic title extraction** - Extracts title from the page's first heading
- **Metadata preservation** - Adds source URL and clipped timestamp to note frontmatter
- **No dependencies** - Uses built-in Python libraries (urllib, HTMLParser)

### Example Output

```markdown
---
source_url: https://example.com/article
clipped_at: 2025-12-17 14:30:00
---

*Clipped from [https://example.com/article](https://example.com/article)*

# Article Title

Content converted to markdown...
```

## Exporting Notes

Export notes to various formats:

```bash
# Text-based formats (output to stdout or file)
notes export <note-id> --format markdown
notes export <note-id> --format html -o output.html
notes export <note-id> --format json
notes export <note-id> --format rtf -o output.rtf
notes export <note-id> --format text

# Binary formats (require output file)
notes export <note-id> --format pdf -o output.pdf
notes export <note-id> --format docx -o output.docx
```

### Supported Export Formats

| Format | Extension | Requires |
|--------|-----------|----------|
| Markdown | `.md` | - |
| HTML | `.html` | - |
| JSON | `.json` | - |
| Plain Text | `.txt` | - |
| RTF | `.rtf` | - |
| PDF | `.pdf` | reportlab |
| DOCX | `.docx` | python-docx |

## Plain Folder Export

Export notes to a readable `plain/` folder that syncs with Git:

```bash
notes export <note-id> --plain
```

This exports to `~/.gpgnotes/notes/plain/YYYY/MM/filename.md`, mirroring the notes structure.

### Benefits

- **Human-readable**: Unencrypted markdown files
- **Git-friendly**: Syncs alongside encrypted notes
- **GitHub viewable**: Browse formatted notes on GitHub
- **Backup**: Secondary copy of your notes

### Directory Structure

```
~/.gpgnotes/notes/
├── 2025/
│   └── 12/
│       ├── 20251215091200.md.gpg  # Encrypted
│       └── ...
└── plain/
    └── 2025/
        └── 12/
            └── 20251215091200.md  # Readable
```
