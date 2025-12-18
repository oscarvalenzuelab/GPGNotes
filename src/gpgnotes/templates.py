"""Template management for GPGNotes."""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Built-in templates
BUILTIN_TEMPLATES = {
    "meeting": """---
title: "{{title}}"
tags: ["meeting"]
---

# {{title}}

**Date**: {{date}}
**Attendees**:

## Agenda


## Notes


## Action Items
- [ ]

## Follow-up

""",
    "project": """---
title: "{{title}}"
tags: ["project"]
status: active
---

# {{title}}

## Overview


## Goals
-

## Timeline


## Resources


## Progress Log

### {{date}}
- Project created

""",
    "bug": """---
title: "Bug: {{title}}"
tags: ["bug"]
status: investigating
severity: medium
---

# Bug: {{title}}

## Description


## Steps to Reproduce
1.

## Expected Behavior


## Actual Behavior


## Environment
- OS:
- Version:

## Investigation Notes


## Solution


""",
    "journal": """---
title: "{{date}} - Journal"
tags: ["journal", "daily"]
---

# {{date}}

## Morning Thoughts


## What I'm Working On
-

## Reflections


## Tomorrow
-

""",
    "research": """---
title: "Research: {{title}}"
tags: ["research"]
---

# Research: {{title}}

## Question/Topic


## Sources
-

## Key Findings


## Summary


## Open Questions
-

""",
    "1on1": """---
title: "1:1 with {{person}}"
tags: ["1on1", "meeting"]
---

# 1:1 with {{person}}

**Date**: {{date}}

## Check-in
- How are you doing?
- Any blockers or concerns?

## Their Topics
-

## My Topics
-

## Career & Growth
-

## Action Items
- [ ]

## Notes


## Follow-up for Next Time
-

""",
    "prompt": """---
title: "{{title}}"
tags: ["prompt", "ai"]
model:
version: 1
status: draft
---

# {{title}}

## Purpose
<!-- What is this prompt designed to accomplish? -->


## Target Model
- Model:
- Temperature:
- Max tokens:

## System Prompt
```
```

## User Prompt Template
```
```

## Input Variables
| Variable | Description | Example |
|----------|-------------|---------|
| | | |

## Example Input
```
```

## Expected Output
```
```

## Context / Background
<!-- Additional context the AI needs to understand -->


## Constraints & Guidelines
- [ ]
- [ ]

## Edge Cases
-

## Evaluation Criteria
- [ ] Accuracy:
- [ ] Tone:
- [ ] Format:

## Iteration Log

### {{date}} - v1
- Initial version

## Notes


""",
}


class TemplateEngine:
    """Template engine with variable substitution."""

    @staticmethod
    def get_default_variables() -> Dict[str, str]:
        """Get default variables available to all templates."""
        now = datetime.now()
        return {
            "date": now.strftime("%Y-%m-%d"),
            "datetime": now.isoformat(),
            "year": now.strftime("%Y"),
            "month": now.strftime("%m"),
            "day": now.strftime("%d"),
            "time": now.strftime("%H:%M"),
        }

    @staticmethod
    def parse_variables(var_list: List[str]) -> Dict[str, str]:
        """Parse variable list in key=value format."""
        variables = {}
        for var_str in var_list:
            if "=" in var_str:
                key, value = var_str.split("=", 1)
                variables[key.strip()] = value.strip()
        return variables

    @staticmethod
    def render(template: str, variables: Dict[str, str]) -> str:
        """Render template with variable substitution.

        Supports {{variable}} syntax with optional defaults.
        """
        # Merge with defaults
        all_vars = {**TemplateEngine.get_default_variables(), **variables}

        def replace(match):
            var_name = match.group(1)
            return all_vars.get(var_name, match.group(0))

        return re.sub(r"\{\{(\w+)\}\}", replace, template)

    @staticmethod
    def extract_variables(template: str) -> List[str]:
        """Extract all variable names from a template."""
        matches = re.findall(r"\{\{(\w+)\}\}", template)
        # Remove default variables and duplicates
        defaults = set(TemplateEngine.get_default_variables().keys())
        return sorted(set(matches) - defaults)


class TemplateManager:
    """Manage note templates."""

    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self.builtin_dir = templates_dir / "builtin"
        self.custom_dir = templates_dir / "custom"

        # Create directories
        self.builtin_dir.mkdir(parents=True, exist_ok=True)
        self.custom_dir.mkdir(parents=True, exist_ok=True)

        # Initialize built-in templates if they don't exist
        self._init_builtin_templates()

    def _init_builtin_templates(self):
        """Write built-in templates to disk."""
        for name, content in BUILTIN_TEMPLATES.items():
            template_path = self.builtin_dir / f"{name}.md"
            if not template_path.exists():
                template_path.write_text(content, encoding="utf-8")

    def list_templates(self) -> Dict[str, List[str]]:
        """List all available templates."""
        builtin = []
        custom = []

        # List built-in templates
        for template_file in self.builtin_dir.glob("*.md"):
            builtin.append(template_file.stem)

        # List custom templates
        for template_file in self.custom_dir.glob("*.md"):
            custom.append(template_file.stem)

        return {"builtin": sorted(builtin), "custom": sorted(custom)}

    def get_template(self, name: str) -> Optional[str]:
        """Get template content by name."""
        # Check built-in first
        builtin_path = self.builtin_dir / f"{name}.md"
        if builtin_path.exists():
            return builtin_path.read_text(encoding="utf-8")

        # Check custom
        custom_path = self.custom_dir / f"{name}.md"
        if custom_path.exists():
            return custom_path.read_text(encoding="utf-8")

        return None

    def save_template(self, name: str, content: str, overwrite: bool = False) -> Path:
        """Save a custom template."""
        template_path = self.custom_dir / f"{name}.md"

        if template_path.exists() and not overwrite:
            raise FileExistsError(f"Template '{name}' already exists")

        template_path.write_text(content, encoding="utf-8")
        return template_path

    def delete_template(self, name: str) -> bool:
        """Delete a custom template."""
        # Don't allow deleting built-in templates
        builtin_path = self.builtin_dir / f"{name}.md"
        if builtin_path.exists():
            raise ValueError(f"Cannot delete built-in template '{name}'")

        custom_path = self.custom_dir / f"{name}.md"
        if custom_path.exists():
            custom_path.unlink()
            return True

        return False

    def template_exists(self, name: str) -> bool:
        """Check if a template exists."""
        builtin_path = self.builtin_dir / f"{name}.md"
        custom_path = self.custom_dir / f"{name}.md"
        return builtin_path.exists() or custom_path.exists()

    def get_template_path(self, name: str) -> Optional[Path]:
        """Get the path to a template file."""
        builtin_path = self.builtin_dir / f"{name}.md"
        if builtin_path.exists():
            return builtin_path

        custom_path = self.custom_dir / f"{name}.md"
        if custom_path.exists():
            return custom_path

        return None
