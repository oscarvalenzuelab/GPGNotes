# Phase 2: Todo List + Folders/Notebooks

## Overview

Combine two related features for better note organization and task management:
- **Todo List Functionality** (Issue #16 - size:S)
- **Folders/Notebooks** (Issue #23 - size:M)

**Combined Estimate:** Medium (M)

---

## Feature 1: Todo List Functionality

### Goals
- Parse markdown checkboxes in notes (`- [ ]` / `- [x]`)
- Aggregate todos across all notes
- Filter and manage tasks from CLI

### Commands

```bash
notes todos                    # List all incomplete tasks
notes todos --all              # Include completed tasks
notes todos --note <id>        # Filter by specific note
notes todos --folder <name>    # Filter by folder (ties into folders feature)
notes todos --due today        # Future: due date support
```

### Implementation

1. **Parser** (`src/gpgnotes/todos.py`)
   - Regex to find `- [ ]` and `- [x]` patterns
   - Extract task text and completion status
   - Track source note and line number

2. **Index Extension**
   - Add `todos` table to `index.db`:
     ```sql
     CREATE TABLE todos (
       id INTEGER PRIMARY KEY,
       note_path TEXT,
       line_number INTEGER,
       task TEXT,
       completed BOOLEAN,
       due_date TEXT,  -- Future
       FOREIGN KEY (note_path) REFERENCES notes_fts(file_path)
     );
     ```
   - Update todos when notes are saved/indexed

3. **CLI Command** (`notes todos`)
   - Query todos table
   - Display with note reference
   - Rich table output with checkboxes

4. **Toggle Command** (optional for v1)
   ```bash
   notes todo toggle <note-id> <line-number>
   ```

### Output Example

```
Incomplete Tasks (5)

Note: Sprint Planning (20251217...)
  □ Line 12: Review PR #43
  □ Line 13: Update documentation

Note: Project Ideas (20251216...)
  □ Line 8: Research SQLite FTS5 alternatives
  □ Line 15: Benchmark encryption performance

Note: Meeting Notes (20251215...)
  □ Line 22: Follow up with team on timeline
```

---

## Feature 2: Folders/Notebooks (Tag-Based)

### Approach: Tag-Based Virtual Folders

Use tag prefixes for folder organization. No storage changes required.

**Why tag-based?**
- Backward compatible (no migration)
- Notes can belong to multiple folders
- Simpler implementation
- Can add directory-based later if needed

### Syntax

```yaml
---
tags:
  - folder:work
  - folder:personal
  - project
  - meeting
---
```

### Commands

```bash
notes folders                  # List all folders with note counts
notes list --folder work       # List notes in folder
notes new "Title" --folder work  # Create note in folder
notes move <id> --folder work  # Add folder tag to note
notes move <id> --unfolder personal  # Remove folder tag
```

### Implementation

1. **Folder Detection**
   - Tags starting with `folder:` are treated as folders
   - Extract folder name after prefix

2. **CLI Changes**
   - Add `--folder` option to `list`, `search`, `new`
   - Add `notes folders` command
   - Add `notes move` command for folder management

3. **Index Query**
   - Filter by tag prefix in existing `notes_fts` table
   - No schema changes needed

4. **Shell Mode**
   - Add `folders` command
   - Add folder autocomplete

### Output Example

```bash
$ notes folders

Folders (4)
┌──────────────┬───────┐
│ Folder       │ Notes │
├──────────────┼───────┤
│ work         │    12 │
│ personal     │     8 │
│ projects     │     5 │
│ archive      │     3 │
└──────────────┴───────┘

Tip: Use 'notes list --folder <name>' to view notes
```

---

## Implementation Order

### Phase 2a: Folders (simpler, foundational)
1. Add `--folder` option to `notes new`
2. Add `--folder` filter to `notes list` and `notes search`
3. Add `notes folders` command
4. Add `notes move` command
5. Update shell mode
6. Tests

### Phase 2b: Todos
1. Create `todos.py` parser
2. Add todos table to index
3. Update indexing to extract todos
4. Add `notes todos` command
5. Update shell mode
6. Tests

### Phase 2c: Integration
1. `notes todos --folder <name>` filtering
2. Documentation
3. Update CHANGELOG

---

## Files to Modify/Create

### New Files
- `src/gpgnotes/todos.py` - Todo parser and manager
- `docs/folders.md` - Folders documentation
- `docs/todos.md` - Todos documentation
- `tests/test_todos.py` - Todo tests
- `tests/test_folders.py` - Folder tests

### Modified Files
- `src/gpgnotes/cli.py` - New commands and options
- `src/gpgnotes/index.py` - Todos table, folder queries
- `src/gpgnotes/note.py` - Folder helper methods
- `README.md` - Feature documentation

---

## Open Questions

1. **Todo due dates?** - Could parse `- [ ] Task @due(2025-12-20)` syntax
2. **Todo priorities?** - Could parse `- [ ] !!! High priority task`
3. **Nested folders?** - `folder:work/projects` or keep flat?
4. **Default folder?** - Config option for default folder on new notes?
5. **Folder colors?** - Visual distinction in list output?

---

## Estimated Effort

| Component | Estimate |
|-----------|----------|
| Folders CLI | 2-3 hours |
| Folders tests | 1 hour |
| Todos parser | 1-2 hours |
| Todos index | 1-2 hours |
| Todos CLI | 2-3 hours |
| Todos tests | 1-2 hours |
| Integration | 1 hour |
| Documentation | 1 hour |
| **Total** | **10-15 hours** |

---

## Version Target

**v0.3.0** - Folders & Todos Release
