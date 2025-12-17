# Daily Notes (Captain's Log)

GPGNotes includes a "Captain's Log" style daily notes feature for quick, timestamped entries throughout the day with optional AI-generated summaries.

## Quick Start

```bash
# Add a quick entry to today's log
notes daily "Fixed the authentication bug"

# Add entry with timestamp
notes daily "Started deployment" --time

# Open today's note in editor
notes today

# View today's entries
notes daily show

# Generate monthly summary
notes daily summary --month
```

## Commands

### Quick Entry

Add entries without opening an editor:

```bash
# Basic entry
notes daily "Your log entry here"

# With timestamp (e.g., "14:30 - Your entry")
notes daily "Started the meeting" --time
notes daily "Finished code review" -t
```

### View & Edit

```bash
# Open today's note in your editor
notes today

# Open yesterday's note
notes yesterday

# View today's entries (without editing)
notes daily show

# View specific date
notes daily show --date 2025-12-15

# View this week's entries
notes daily show --week
```

### Summaries

Generate summaries from your daily entries:

```bash
# Current month summary
notes daily summary --month

# Current week summary
notes daily summary --week

# Specific month
notes daily summary --month --year 2025 --month-num 11

# Save summary as a new note
notes daily summary --month --save
```

**With LLM configured**: Get AI-generated insights highlighting accomplishments, patterns, and themes.

**Without LLM**: Get basic statistics (days logged, entry count, tags used).

## Daily Note Format

Daily notes are stored with automatic formatting:

```markdown
---
title: "Captain's Log: 2025-12-17"
tags: ["daily", "log"]
created: 2025-12-17T00:00:00
modified: 2025-12-17T17:30:00
---

# Captain's Log: 2025-12-17

## Entries

- 09:15 - Morning standup - discussed blockers
- 10:30 - Code review for PR #45
- 12:00 - Lunch with team
- 14:45 - Finished API refactoring
- 16:00 - Fixed the authentication bug
```

## Storage

Daily notes are stored in a dedicated directory:

```
~/.gpgnotes/notes/
└── daily/
    └── 2025/
        └── 12/
            ├── 2025-12-15.md.gpg
            ├── 2025-12-16.md.gpg
            └── 2025-12-17.md.gpg
```

## Summary Generation

### With LLM (Recommended)

Configure an LLM provider for rich, AI-generated summaries:

```bash
# Using OpenAI
notes config --llm-provider openai --llm-key YOUR_API_KEY

# Using Ollama (local)
notes config --llm-provider ollama
```

Example LLM-generated summary:

```markdown
## December 2025 Summary

**Key Accomplishments:**
- Completed API refactoring project (Dec 5-12)
- Released v2.0 to production with zero downtime (Dec 16)
- Onboarded 3 new customers (Dec 18-22)

**Themes & Patterns:**
- Heavy focus on testing and QA in week 2
- Increased meeting frequency during release week
- Strong end-of-month customer engagement

**Notable Entries:**
> "Finally cracked the caching issue - was a race condition" - Dec 11
> "v2.0 deployed successfully, zero downtime!" - Dec 16
```

### Without LLM (Basic Stats)

If no LLM is configured, you'll get basic statistics:

```markdown
## December 2025 Summary

**Statistics:**
- Days logged: 22
- Total entries: 147
- Date range: 2025-12-01 to 2025-12-22
- Tags used: api, meeting, deployment, review

---
*Tip: Configure an LLM provider for AI-generated insights:*
`notes config --llm-provider openai --llm-key YOUR_KEY`
```

## Interactive Mode

All daily commands work in interactive mode:

```
notes> daily "Fixed the login bug"
✓ Added to Captain's Log: 2025-12-17

notes> today
[Opens editor]

notes> yesterday
[Opens editor]
```

## Tips

1. **Morning routine**: Start each day with `notes today` to review yesterday and plan today
2. **Quick capture**: Use `notes daily "entry"` for fast logging without opening an editor
3. **Weekly review**: Use `notes daily summary --week` every Friday
4. **Monthly retrospective**: Generate monthly summaries with `--save` to keep them as permanent notes

## Related Commands

- `notes new` - Create a regular note
- `notes list --tag daily` - List all daily notes
- `notes search "keyword"` - Search across all notes including daily entries
- `notes enhance <id>` - AI-enhance any note
