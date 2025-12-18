"""Todo list parser and manager for extracting tasks from notes."""

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TodoItem:
    """Represents a single todo item extracted from a note."""

    note_path: str
    line_number: int
    task: str
    completed: bool
    due_date: Optional[str] = None  # Future enhancement


# Regex patterns for todo items
# Matches: - [ ] task text OR - [x] task text OR - [X] task text
TODO_PATTERN = re.compile(r"^(\s*)-\s*\[([ xX])\]\s*(.+)$", re.MULTILINE)


def parse_todos(content: str, note_path: str = "") -> List[TodoItem]:
    """
    Parse markdown content and extract todo items.

    Args:
        content: The markdown content to parse
        note_path: The path to the source note (for reference)

    Returns:
        List of TodoItem objects found in the content
    """
    todos = []
    lines = content.split("\n")

    for line_num, line in enumerate(lines, start=1):
        match = TODO_PATTERN.match(line)
        if match:
            checkbox = match.group(2)
            task_text = match.group(3).strip()

            todo = TodoItem(
                note_path=note_path,
                line_number=line_num,
                task=task_text,
                completed=checkbox.lower() == "x",
            )
            todos.append(todo)

    return todos


def count_todos(content: str) -> tuple:
    """
    Count completed and incomplete todos in content.

    Args:
        content: The markdown content to parse

    Returns:
        Tuple of (incomplete_count, completed_count)
    """
    todos = parse_todos(content)
    completed = sum(1 for t in todos if t.completed)
    incomplete = len(todos) - completed
    return incomplete, completed


def toggle_todo(content: str, line_number: int) -> str:
    """
    Toggle a todo item at the specified line number.

    Args:
        content: The markdown content
        line_number: The 1-indexed line number to toggle

    Returns:
        The modified content with the todo toggled
    """
    lines = content.split("\n")

    if line_number < 1 or line_number > len(lines):
        return content

    line = lines[line_number - 1]
    match = TODO_PATTERN.match(line)

    if match:
        indent = match.group(1)
        checkbox = match.group(2)
        task_text = match.group(3)

        # Toggle the checkbox
        new_checkbox = " " if checkbox.lower() == "x" else "x"
        lines[line_number - 1] = f"{indent}- [{new_checkbox}] {task_text}"

    return "\n".join(lines)


def format_todo_display(todo: TodoItem, show_line: bool = True) -> str:
    """
    Format a todo item for display.

    Args:
        todo: The TodoItem to format
        show_line: Whether to show the line number

    Returns:
        Formatted string representation
    """
    checkbox = "☑" if todo.completed else "☐"
    line_info = f"Line {todo.line_number}: " if show_line else ""
    return f"  {checkbox} {line_info}{todo.task}"
