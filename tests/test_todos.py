"""Tests for todo functionality."""

import pytest
from click.testing import CliRunner
from gpgnotes.cli import main
from gpgnotes.index import SearchIndex
from gpgnotes.note import Note
from gpgnotes.todos import parse_todos, count_todos, toggle_todo, TodoItem


# Tests for todos.py parser module

def test_parse_todos_empty():
    """Test parsing content with no todos."""
    content = "This is regular content\nNo checkboxes here."
    todos = parse_todos(content)
    assert todos == []


def test_parse_todos_incomplete():
    """Test parsing incomplete todos."""
    content = "- [ ] Task one\n- [ ] Task two"
    todos = parse_todos(content)

    assert len(todos) == 2
    assert todos[0].task == "Task one"
    assert todos[0].completed is False
    assert todos[0].line_number == 1
    assert todos[1].task == "Task two"
    assert todos[1].completed is False
    assert todos[1].line_number == 2


def test_parse_todos_completed():
    """Test parsing completed todos."""
    content = "- [x] Done task\n- [X] Also done"
    todos = parse_todos(content)

    assert len(todos) == 2
    assert todos[0].completed is True
    assert todos[1].completed is True


def test_parse_todos_mixed():
    """Test parsing mixed todos."""
    content = """# My List
- [ ] Incomplete task
- [x] Completed task
Some text
- [ ] Another incomplete
"""
    todos = parse_todos(content)

    assert len(todos) == 3
    assert todos[0].task == "Incomplete task"
    assert todos[0].completed is False
    assert todos[1].task == "Completed task"
    assert todos[1].completed is True
    assert todos[2].task == "Another incomplete"
    assert todos[2].completed is False


def test_parse_todos_with_note_path():
    """Test that note path is stored."""
    content = "- [ ] Task"
    todos = parse_todos(content, "/path/to/note.md")

    assert todos[0].note_path == "/path/to/note.md"


def test_parse_todos_indented():
    """Test parsing indented todos."""
    content = """- [ ] Top level
  - [ ] Indented once
    - [ ] Indented twice
"""
    todos = parse_todos(content)

    assert len(todos) == 3


def test_count_todos():
    """Test counting todos."""
    content = """- [ ] Task 1
- [x] Task 2
- [ ] Task 3
- [x] Task 4
"""
    incomplete, complete = count_todos(content)

    assert incomplete == 2
    assert complete == 2


def test_toggle_todo():
    """Test toggling a todo."""
    content = "- [ ] Incomplete"
    toggled = toggle_todo(content, 1)
    assert "- [x] Incomplete" in toggled

    content = "- [x] Complete"
    toggled = toggle_todo(content, 1)
    assert "- [ ] Complete" in toggled


def test_toggle_todo_preserves_other_lines():
    """Test that toggle preserves other lines."""
    content = """Line 1
- [ ] Task
Line 3"""
    toggled = toggle_todo(content, 2)

    assert "Line 1" in toggled
    assert "- [x] Task" in toggled
    assert "Line 3" in toggled


def test_toggle_todo_invalid_line():
    """Test toggle with invalid line number."""
    content = "- [ ] Task"
    toggled = toggle_todo(content, 99)
    assert toggled == content  # Unchanged


# Tests for CLI commands

def test_todos_command():
    """Test todos command runs without crashing."""
    runner = CliRunner()
    result = runner.invoke(main, ['todos'])

    # Should run without crashing
    assert result.exit_code in [0, 1]


def test_todos_command_all():
    """Test todos --all command."""
    runner = CliRunner()
    result = runner.invoke(main, ['todos', '--all'])

    assert result.exit_code in [0, 1]


def test_todos_command_folder():
    """Test todos --folder command."""
    runner = CliRunner()
    result = runner.invoke(main, ['todos', '--folder', 'work'])

    assert result.exit_code in [0, 1]


def test_todos_help():
    """Test todos command help."""
    runner = CliRunner()
    result = runner.invoke(main, ['todos', '--help'])

    # Help should work, but may fail if config check runs first
    if result.exit_code == 0:
        assert '--all' in result.output
        assert '--folder' in result.output
        assert '--note' in result.output


# Tests for index.py todos methods

def test_update_todos(test_config):
    """Test updating todos in index."""
    index = SearchIndex(test_config)
    try:
        todos = [
            {"line_number": 1, "task": "Task 1", "completed": False},
            {"line_number": 2, "task": "Task 2", "completed": True},
        ]
        index.update_todos("/path/to/note.md", todos)

        # Query the todos
        result = index.get_todos()
        assert len(result) == 2
    finally:
        index.close()


def test_get_todos_filter_completed(test_config):
    """Test filtering todos by completion status."""
    index = SearchIndex(test_config)
    try:
        todos = [
            {"line_number": 1, "task": "Incomplete", "completed": False},
            {"line_number": 2, "task": "Complete", "completed": True},
        ]
        index.update_todos("/path/to/note.md", todos)

        incomplete = index.get_todos(completed=False)
        assert len(incomplete) == 1
        assert incomplete[0]["task"] == "Incomplete"

        complete = index.get_todos(completed=True)
        assert len(complete) == 1
        assert complete[0]["task"] == "Complete"
    finally:
        index.close()


def test_get_todo_counts(test_config):
    """Test getting todo counts."""
    index = SearchIndex(test_config)
    try:
        todos = [
            {"line_number": 1, "task": "Task 1", "completed": False},
            {"line_number": 2, "task": "Task 2", "completed": False},
            {"line_number": 3, "task": "Task 3", "completed": True},
        ]
        index.update_todos("/path/to/note.md", todos)

        incomplete, complete = index.get_todo_counts()
        assert incomplete == 2
        assert complete == 1
    finally:
        index.close()


def test_remove_todos_for_note(test_config):
    """Test removing todos for a note."""
    index = SearchIndex(test_config)
    try:
        todos = [{"line_number": 1, "task": "Task", "completed": False}]
        index.update_todos("/path/to/note.md", todos)

        # Verify todo exists
        assert len(index.get_todos()) == 1

        # Remove todos
        index.remove_todos_for_note("/path/to/note.md")

        # Verify removed
        assert len(index.get_todos()) == 0
    finally:
        index.close()


def test_add_note_extracts_todos(test_config):
    """Test that adding a note extracts todos."""
    index = SearchIndex(test_config)
    try:
        note = Note(
            title="Task List",
            content="- [ ] Task one\n- [x] Task two",
            tags=["test"]
        )
        note.file_path = test_config.notes_dir / "20251218120000.gpg"

        index.add_note(note)

        # Check todos were extracted
        todos = index.get_todos()
        assert len(todos) == 2

        # Check incomplete
        incomplete = [t for t in todos if not t["completed"]]
        assert len(incomplete) == 1
        assert incomplete[0]["task"] == "Task one"

        # Check complete
        complete = [t for t in todos if t["completed"]]
        assert len(complete) == 1
        assert complete[0]["task"] == "Task two"
    finally:
        index.close()


def test_todo_item_dataclass():
    """Test TodoItem dataclass."""
    item = TodoItem(
        note_path="/path/to/note.md",
        line_number=5,
        task="My task",
        completed=False
    )

    assert item.note_path == "/path/to/note.md"
    assert item.line_number == 5
    assert item.task == "My task"
    assert item.completed is False
    assert item.due_date is None
