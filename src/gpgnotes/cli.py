"""Command-line interface for GPGNotes."""

import atexit
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import click
from prompt_toolkit import PromptSession, prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .config import Config
from .daily import DailyNoteManager
from .history import VersionHistory, parse_diff_output
from .index import SearchIndex
from .note import Note
from .storage import Storage
from .sync import GitSync
from .tagging import AutoTagger
from .templates import TemplateEngine, TemplateManager

console = Console()


def _paginate_results(items, page_size=20):
    """Interactive pagination for result lists.

    Yields pages of items and handles user navigation.
    Returns the action chosen by user: 'next', 'prev', 'quit', or page number.
    """
    total_items = len(items)
    total_pages = (total_items + page_size - 1) // page_size
    current_page = 1

    while True:
        # Calculate slice for current page
        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, total_items)
        page_items = items[start_idx:end_idx]

        # Yield the current page
        yield {
            "items": page_items,
            "page": current_page,
            "total_pages": total_pages,
            "total_items": total_items,
            "start_idx": start_idx,
            "end_idx": end_idx,
        }

        # Check if we need pagination controls
        if total_pages <= 1:
            break

        # Show pagination controls
        console.print(
            f"\n[dim]Page {current_page} of {total_pages} ({start_idx + 1}-{end_idx} of {total_items} items)[/dim]"
        )
        console.print(
            "[dim]Commands: [n]ext, [p]rev, [number] to jump to page, [q]uit pagination[/dim]"
        )

        try:
            choice = prompt("\nAction: ").strip().lower()

            if choice in ["q", "quit", ""]:
                break
            elif choice in ["n", "next"]:
                if current_page < total_pages:
                    current_page += 1
                else:
                    console.print("[yellow]Already on last page[/yellow]")
            elif choice in ["p", "prev", "previous"]:
                if current_page > 1:
                    current_page -= 1
                else:
                    console.print("[yellow]Already on first page[/yellow]")
            elif choice.isdigit():
                page_num = int(choice)
                if 1 <= page_num <= total_pages:
                    current_page = page_num
                else:
                    console.print(f"[yellow]Invalid page number. Enter 1-{total_pages}[/yellow]")
            else:
                console.print("[yellow]Invalid command. Use n, p, number, or q[/yellow]")
        except (KeyboardInterrupt, EOFError):
            break


def _sync_in_background(config: Config, message: str):
    """Run git sync in background thread."""

    def _do_sync():
        try:
            sync = GitSync(config)
            sync.sync(message)
        except Exception:
            # Silently fail - don't interrupt user
            pass

    thread = threading.Thread(target=_do_sync, daemon=True)
    thread.start()


def _find_note(query: str, config: Config) -> Optional[Path]:
    """Find a note by ID or search query with interactive selection."""
    storage = Storage(config)
    index = SearchIndex(config)

    try:
        # Check if query is a note ID (14 digits)
        if query.isdigit() and len(query) == 14:
            try:
                return storage.find_by_id(query)
            except FileNotFoundError:
                console.print(f"[yellow]No note found with ID: {query}[/yellow]")
                return None

        # Otherwise, search by query
        results = index.search(query)
        if not results:
            console.print(f"[yellow]No notes found matching '{query}'[/yellow]")
            return None

        # If single result, return it
        if len(results) == 1:
            return Path(results[0][0])

        # Multiple results - show interactive selection
        console.print(f"[yellow]Found {len(results)} notes:[/yellow]\n")

        table = Table(show_header=True)
        table.add_column("#", style="cyan", width=3)
        table.add_column("ID", style="cyan", width=14)
        table.add_column("Title", style="green", width=40)
        table.add_column("Modified", style="yellow", width=16)

        notes = []
        for i, result in enumerate(results[:10], 1):
            try:
                note = storage.load_note(Path(result[0]))
                notes.append(note)
                table.add_row(
                    str(i),
                    note.note_id,
                    note.title[:38] + "..." if len(note.title) > 38 else note.title,
                    note.modified.strftime("%Y-%m-%d %H:%M"),
                )
            except Exception:
                continue

        console.print(table)

        # Prompt for selection
        try:
            choice = prompt("\nSelect note number (or 'c' to cancel): ")
            if choice.lower() == "c":
                console.print("[yellow]Cancelled[/yellow]")
                return None

            idx = int(choice) - 1
            if 0 <= idx < len(notes):
                return notes[idx].file_path
            else:
                console.print("[red]Invalid selection[/red]")
                return None
        except (ValueError, KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Cancelled[/yellow]")
            return None

    finally:
        index.close()


def _background_sync():
    """Background sync function to run on exit.

    Note: Auto-tagging is done immediately when notes are created/imported,
    so we only need to handle git sync here.
    """
    try:
        # Clear sys.argv to avoid Click parsing issues during exit
        import sys

        original_argv = sys.argv[:]
        sys.argv = [sys.argv[0]] if sys.argv else []

        try:
            config = Config()

            # Sync to git if enabled
            if config.get("auto_sync") and config.get("git_remote"):
                sync = GitSync(config)
                sync.sync("Auto-sync on exit")
        finally:
            # Always restore sys.argv
            sys.argv = original_argv
    except Exception:
        # Silently fail - we're exiting anyway
        pass


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version="0.2.7")
def main(ctx):
    """GPGNotes - Encrypted note-taking with Git sync."""
    # Register exit handler for background sync
    atexit.register(_background_sync)

    # Check if this is first run (except for init and config commands)
    if ctx.invoked_subcommand not in ["init", "config", None]:
        config = Config()
        if not config.is_configured():
            console.print("[yellow]⚠ GPGNotes is not configured yet.[/yellow]")
            console.print("Run [cyan]notes init[/cyan] to set up your configuration.\n")
            sys.exit(1)

    if ctx.invoked_subcommand is None:
        # Interactive mode - check config first
        config = Config()
        if not config.is_configured():
            console.print("[yellow]⚠ GPGNotes is not configured yet.[/yellow]")
            console.print("Let's set it up now!\n")
            ctx.invoke(init)
            return
        interactive_mode()


@main.command()
def init():
    """Initialize GPGNotes with interactive setup."""
    console.print(
        Panel.fit(
            "[cyan]Welcome to GPGNotes![/cyan]\n\n"
            "Let's set up your encrypted note-taking environment.\n"
            "You'll need a GPG key for encryption.",
            title="Initial Setup",
        )
    )

    cfg = Config()
    from .encryption import Encryption

    # Step 1: List and select GPG key
    console.print("\n[bold]Step 1: GPG Key Setup[/bold]")
    enc = Encryption()
    keys = enc.list_keys()

    if not keys:
        console.print("[red]✗ No GPG keys found![/red]")
        console.print("\nYou need to create a GPG key first:")
        console.print("  [cyan]gpg --full-generate-key[/cyan]\n")
        console.print("Then run [cyan]notes init[/cyan] again.")
        sys.exit(1)

    console.print(f"\n[green]Found {len(keys)} GPG key(s):[/green]")
    for i, key in enumerate(keys, 1):
        console.print(f"  {i}. {key['keyid']}: {key['uids'][0]}")

    # Ask user to select a key
    while True:
        try:
            choice = prompt("\nSelect a key number (or enter key ID): ")
            if choice.isdigit() and 1 <= int(choice) <= len(keys):
                selected_key = keys[int(choice) - 1]["keyid"]
                break
            else:
                # User entered key ID directly
                if any(choice in key["keyid"] for key in keys):
                    selected_key = choice
                    break
                console.print("[red]Invalid selection. Try again.[/red]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Setup cancelled.[/yellow]")
            sys.exit(0)

    cfg.set("gpg_key", selected_key)
    console.print(f"[green]✓[/green] GPG key set: {selected_key}")

    # Test encryption/decryption
    console.print("\n[bold]Testing encryption...[/bold]")
    try:
        enc_test = Encryption(selected_key)
        test_content = "Test note content"
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".gpg", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        enc_test.encrypt(test_content, tmp_path)
        decrypted = enc_test.decrypt(tmp_path)
        tmp_path.unlink()

        if decrypted == test_content:
            console.print("[green]✓[/green] Encryption test passed!")
        else:
            console.print("[red]✗[/red] Encryption test failed!")
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Encryption test failed: {e}")
        console.print("\nMake sure you can access your GPG key.")
        sys.exit(1)

    # Step 2: Editor selection
    console.print("\n[bold]Step 2: Editor Selection[/bold]")

    # Detect available editors
    import shutil

    available_editors = []
    for editor in ["vim", "vi", "nano", "emacs", "code", "nvim"]:
        if shutil.which(editor):
            available_editors.append(editor)

    if available_editors:
        console.print(f"Available editors: {', '.join(available_editors)}")
        default_editor = available_editors[0]  # Use first available
    else:
        default_editor = cfg.get("editor", "nano")

    editor = prompt(f"Text editor [{default_editor}]: ") or default_editor
    cfg.set("editor", editor)
    console.print(f"[green]✓[/green] Editor set to: {editor}")

    # Step 3: Git remote (optional)
    console.print("\n[bold]Step 3: Git Sync (Optional)[/bold]")
    console.print("Enter your private Git repository URL for syncing notes.")
    console.print("Example: git@github.com:username/notes.git")
    console.print("Leave empty to skip for now.\n")

    git_remote = prompt("Git remote URL [skip]: ").strip()
    if git_remote:
        cfg.set("git_remote", git_remote)
        console.print("[green]✓[/green] Git remote set")

        # Initialize Git repo
        try:
            sync = GitSync(cfg)
            sync.init_repo()
            console.print("[green]✓[/green] Git repository initialized")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Warning: Could not initialize Git: {e}")
    else:
        console.print(
            "[yellow]⚠[/yellow] Git sync skipped (you can set it later with: notes config --git-remote URL)"
        )

    # Step 4: Final settings
    console.print("\n[bold]Step 4: Additional Settings[/bold]")

    auto_sync_input = prompt("Enable auto-sync after each change? [Y/n]: ").lower()
    auto_sync = auto_sync_input != "n"
    cfg.set("auto_sync", auto_sync)

    auto_tag_input = prompt("Enable automatic tag generation? [Y/n]: ").lower()
    auto_tag = auto_tag_input != "n"
    cfg.set("auto_tag", auto_tag)

    # Create directories
    cfg.ensure_dirs()

    # Summary
    console.print("\n" + "=" * 60)
    console.print(
        Panel.fit(
            f"""[green]✓ Setup Complete![/green]

GPG Key: {selected_key}
Editor: {editor}
Git Remote: {git_remote or "[dim]not configured[/dim]"}
Auto-sync: {"[green]enabled[/green]" if auto_sync else "[red]disabled[/red]"}
Auto-tag: {"[green]enabled[/green]" if auto_tag else "[red]disabled[/red]"}

Notes directory: {cfg.notes_dir}
Config file: {cfg.config_file}

You're ready to start! Try:
  [cyan]notes new "My First Note"[/cyan]
  [cyan]notes list[/cyan]
  [cyan]notes search "keyword"[/cyan]
""",
            title="GPGNotes Ready!",
        )
    )


@main.command()
@click.argument("title", required=False)
@click.option("--tags", "-t", help="Comma-separated tags")
@click.option("--template", help="Template to use")
@click.option("--var", multiple=True, help="Template variable in key=value format")
def new(title, tags, template, var):
    """Create a new note, optionally from a template.

    Examples:
        notes new "Team Meeting"                    # Blank note
        notes new "Sprint Planning" --template meeting --var project="Backend"
        notes new "Bug Fix" --template bug
    """
    config = Config()

    # Check if GPG key is configured
    if not config.get("gpg_key"):
        console.print("[red]Error: GPG key not configured. Run 'notes config' first.[/red]")
        sys.exit(1)

    # Get title if not provided
    if not title:
        title = prompt("Note title: ")

    if not title:
        console.print("[red]Title cannot be empty[/red]")
        sys.exit(1)

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    # Initialize template manager
    templates_dir = config.config_dir / "templates"
    template_mgr = TemplateManager(templates_dir)

    # Handle template if specified
    content = ""
    if template:
        template_content = template_mgr.get_template(template)
        if not template_content:
            console.print(f"[red]Error: Template '{template}' not found[/red]")
            console.print("[yellow]Use 'notes templates' to list available templates[/yellow]")
            sys.exit(1)

        # Parse variables
        variables = TemplateEngine.parse_variables(list(var))
        variables["title"] = title

        # Check for missing required variables
        required_vars = TemplateEngine.extract_variables(template_content)
        missing_vars = [v for v in required_vars if v not in variables]

        # Prompt for missing variables
        for var_name in missing_vars:
            value = prompt(f"Enter value for '{var_name}' [optional]: ").strip()
            if value:
                variables[var_name] = value

        # Render template
        content = TemplateEngine.render(template_content, variables)

    # Create note
    note = Note(title=title, content=content, tags=tag_list)

    # Save and get path
    storage = Storage(config)
    file_path = storage.save_note(note)

    # Now edit it
    try:
        note = storage.edit_note(file_path)

        # Auto-tag if enabled
        if config.get("auto_tag") and not tag_list:
            tagger = AutoTagger()
            auto_tags = tagger.extract_tags(note.content, note.title)
            note.tags = auto_tags
            storage.save_note(note)

        # Index the note
        index = SearchIndex(config)
        index.add_note(note)
        index.close()

        # Sync if enabled (background)
        if config.get("auto_sync"):
            _sync_in_background(config, f"Add note: {note.title}")

        console.print(f"[green]✓[/green] Note created: {note.title}")
        if note.tags:
            console.print(f"[blue]Tags:[/blue] {', '.join(note.tags)}")

    except Exception as e:
        console.print(f"[red]Error creating note: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("query", required=False)
@click.option("--tag", "-t", help="Search by tag")
@click.option("--page-size", "-n", default=20, help="Items per page (default: 20)")
@click.option("--no-pagination", is_flag=True, help="Disable pagination, show all results")
def search(query, tag, page_size, no_pagination):
    """Search notes with pagination."""
    from datetime import datetime

    config = Config()
    index = SearchIndex(config)
    storage = Storage(config)

    try:
        # Get file paths from index
        if tag:
            # Search by tag
            results = index.search_by_tag(tag)
        elif query:
            # Full-text search
            results = index.search(query)
            results = [r[0] for r in results]  # Extract file paths
        else:
            # List all notes
            results = index.list_all()
            results = [r[0] for r in results]  # Extract file paths

        if not results:
            console.print("[yellow]No notes found[/yellow]")
            index.close()
            return

        # Get metadata from index for all results (fast, no decryption)
        notes_metadata = []
        for file_path_str in results:
            # Query index for metadata
            cursor = index.conn.execute(
                "SELECT title, tags, modified FROM notes_fts WHERE file_path = ?",
                (file_path_str,),
            )
            row = cursor.fetchone()
            if row:
                notes_metadata.append(
                    {
                        "file_path": file_path_str,
                        "title": row["title"],
                        "tags": row["tags"].split() if row["tags"] else [],
                        "modified": row["modified"],
                    }
                )

        if not notes_metadata:
            console.print("[yellow]No notes found[/yellow]")
            return

        def build_search_table(notes_page, table_title):
            """Build a table for a page of search results."""
            table = Table(title=table_title)
            table.add_column("ID", style="cyan", width=14)
            table.add_column("Title", style="green", width=25)
            table.add_column("Preview", style="white", width=35)
            table.add_column("Tags", style="blue", width=15)
            table.add_column("Modified", style="yellow", width=16)

            for note_meta in notes_page:
                # Extract ID from file path
                file_path = Path(note_meta["file_path"])
                note_id = Note.extract_id_from_path(file_path)

                # Parse datetime
                modified_dt = datetime.fromisoformat(note_meta["modified"])

                # Only decrypt for preview (current page only)
                preview = ""
                try:
                    note = storage.load_note(file_path)
                    preview = note.content.replace("\n", " ").strip()
                    if len(preview) > 80:
                        preview = preview[:77] + "..."
                except Exception:
                    preview = "[error loading preview]"

                table.add_row(
                    note_id,
                    note_meta["title"][:23] + "..."
                    if len(note_meta["title"]) > 23
                    else note_meta["title"],
                    preview,
                    ", ".join(note_meta["tags"][:2])
                    + ("..." if len(note_meta["tags"]) > 2 else ""),
                    modified_dt.strftime("%Y-%m-%d %H:%M"),
                )

            return table

        # Build title
        if query:
            table_title = f"Search: '{query}'"
        elif tag:
            table_title = f"Tagged: '{tag}'"
        else:
            table_title = "All Notes"

        # Use pagination or show all
        if no_pagination or len(notes_metadata) <= page_size:
            # Show all results
            table = build_search_table(notes_metadata, table_title)
            console.print(table)
        else:
            # Use pagination
            paginator = _paginate_results(notes_metadata, page_size)
            for page_info in paginator:
                # Clear screen for better UX
                console.clear()

                # Build and display table for current page
                page_title = f"{table_title} (Page {page_info['page']}/{page_info['total_pages']})"
                table = build_search_table(page_info["items"], page_title)
                console.print(table)

        console.print("\n[dim]Tip: Use 'notes open <ID>' to open a note[/dim]")

    finally:
        index.close()


@main.command()
@click.argument("note_id", required=False)
@click.option("--last", "-l", is_flag=True, help="Open most recently modified note")
def open(note_id, last):
    """Open a note by ID, title, or use --last for most recent.

    Examples:
        notes open 20251216120000      # By ID
        notes open "meeting"           # By title (fuzzy match)
        notes open --last              # Most recent note
    """
    config = Config()
    storage = Storage(config)
    index = SearchIndex(config)

    try:
        # Sync before opening to get latest version
        if config.get("auto_sync") and config.get("git_remote"):
            with console.status("[bold blue]Syncing before opening..."):
                git_sync = GitSync(config)
                git_sync.init_repo()
                if git_sync.has_remote():
                    git_sync.pull()

            # Rebuild index to reflect any pulled changes
            notes = []
            for file_path_item in storage.list_notes():
                try:
                    note_item = storage.load_note(file_path_item)
                    notes.append(note_item)
                except Exception:
                    continue
            index.rebuild_index(notes)

        # Handle --last flag
        if last:
            note_files = list(storage.list_notes())
            if not note_files:
                console.print("[yellow]No notes found[/yellow]")
                return

            # Load all notes and find most recent
            notes_with_dates = []
            for file_path_item in note_files:
                try:
                    note_item = storage.load_note(file_path_item)
                    notes_with_dates.append((file_path_item, note_item))
                except Exception:
                    continue

            if not notes_with_dates:
                console.print("[yellow]No notes found[/yellow]")
                return

            # Sort by modified date descending
            notes_with_dates.sort(key=lambda x: x[1].modified, reverse=True)
            file_path, _ = notes_with_dates[0]

        elif note_id:
            # Check if it's a valid ID format
            if note_id.isdigit() and len(note_id) == 14:
                # Find note by ID
                try:
                    file_path = storage.find_by_id(note_id)
                except FileNotFoundError:
                    console.print(f"[red]Error: Note with ID '{note_id}' not found[/red]")
                    return
            else:
                # Try fuzzy matching by title
                file_path = _find_note_by_title(storage, note_id)
                if not file_path:
                    return
        else:
            console.print("[yellow]Usage: notes open <ID or title> or notes open --last[/yellow]")
            return

        # Edit note
        note = storage.edit_note(file_path)

        # Re-index
        index.add_note(note)

        # Sync after editing (synchronous, not background)
        if config.get("auto_sync") and config.get("git_remote"):
            with console.status("[bold blue]Syncing changes..."):
                git_sync = GitSync(config)
                git_sync.sync(f"Update note: {note.title}")

        console.print(f"[green]✓[/green] Note updated: {note.title}")

    except Exception as e:
        console.print(f"[red]Error opening note: {e}[/red]")
    finally:
        index.close()


def _find_note_by_title(storage: Storage, query: str) -> Optional[Path]:
    """Find a note by fuzzy matching the title.

    Returns the file path if a single match or user selects one,
    None if no match or user cancels.
    """
    query_lower = query.lower()
    matches = []

    for file_path in storage.list_notes():
        try:
            note = storage.load_note(file_path)
            if query_lower in note.title.lower():
                matches.append((file_path, note))
        except Exception:
            continue

    if not matches:
        console.print(f"[yellow]No notes matching '{query}'[/yellow]")
        console.print("[dim]Tip: Use 'notes search <query>' for full-text search[/dim]")
        return None

    if len(matches) == 1:
        return matches[0][0]

    # Multiple matches - let user choose
    console.print(f"\n[cyan]Multiple notes match '{query}':[/cyan]\n")
    for i, (_, note) in enumerate(matches[:10], 1):
        note_id = note.modified.strftime("%Y%m%d%H%M%S")
        console.print(f"  [{i}] {note.title} [dim]({note_id})[/dim]")

    if len(matches) > 10:
        console.print(f"  [dim]... and {len(matches) - 10} more[/dim]")

    console.print()
    try:
        choice = prompt("Select note (number) or press Enter to cancel: ").strip()
        if not choice:
            return None
        idx = int(choice) - 1
        if 0 <= idx < len(matches):
            return matches[idx][0]
        else:
            console.print("[red]Invalid selection[/red]")
            return None
    except (ValueError, KeyboardInterrupt, EOFError):
        return None


@main.command("list")
@click.option("--preview", "-p", is_flag=True, help="Show first line of content")
@click.option(
    "--sort",
    "-s",
    type=click.Choice(["modified", "created", "title"]),
    default="modified",
    help="Sort order (default: modified)",
)
@click.option("--page-size", "-n", default=20, help="Items per page (default: 20)")
@click.option("--tag", "-t", help="Filter by tag")
@click.option("--no-pagination", is_flag=True, help="Disable pagination, show all results")
def list_cmd(preview, sort, page_size, tag, no_pagination):
    """List all notes with optional filtering and sorting.

    Examples:
        notes list                    # Default: sorted by modified, paginated
        notes list --preview          # Show content preview
        notes list --sort title       # Sort alphabetically
        notes list --tag work         # Filter by tag
        notes list -n 10              # Show 10 items per page
        notes list --no-pagination    # Show all results at once
    """
    from datetime import datetime
    from pathlib import Path

    from .index import SearchIndex

    config = Config()
    storage = Storage(config)

    try:
        # Use index for fast metadata retrieval (no decryption!)
        search_index = SearchIndex(config)
        notes_metadata = search_index.get_all_metadata(sort_by=sort, tag_filter=tag)
        search_index.close()

        if not notes_metadata:
            if tag:
                console.print(f"[yellow]No notes found with tag '{tag}'[/yellow]")
            else:
                console.print("[yellow]No notes found[/yellow]")
            return

        def build_table(notes_page, table_title):
            """Build a table for a page of notes."""
            table = Table(title=table_title)
            table.add_column("ID", style="cyan", width=14, no_wrap=True)
            table.add_column("Type", style="magenta", width=5, no_wrap=True)
            title_width = 28 if preview else 40
            tags_width = 18 if preview else 25
            table.add_column("Title", style="green", width=title_width, no_wrap=True)
            table.add_column("Tags", style="blue", width=tags_width, no_wrap=True)
            table.add_column("Modified", style="yellow", width=16, no_wrap=True)
            if preview:
                table.add_column("Preview", style="dim", width=35, no_wrap=True)

            for note_meta in notes_page:
                # Extract ID from file path
                file_path = Path(note_meta["file_path"])
                note_id = Note.extract_id_from_path(file_path)

                # Parse datetime
                modified_dt = datetime.fromisoformat(note_meta["modified"])

                # Determine type indicator
                is_plain = note_meta.get("is_plain", False)
                type_indicator = "📄" if is_plain else "🔒"

                # Truncate title and tags to fit columns
                title_text = note_meta["title"]
                if len(title_text) > title_width - 3:
                    title_text = title_text[: title_width - 3] + "..."

                tags_text = ", ".join(note_meta["tags"][:3])
                if len(tags_text) > tags_width - 3:
                    tags_text = tags_text[: tags_width - 3] + "..."

                row = [
                    note_id,
                    type_indicator,
                    title_text,
                    tags_text,
                    modified_dt.strftime("%Y-%m-%d %H:%M"),
                ]

                if preview:
                    # Only decrypt if preview is requested for current page
                    try:
                        note = storage.load_note(file_path)
                        # Get first non-empty line of content
                        first_line = ""
                        for line in note.content.split("\n"):
                            line = line.strip()
                            if line and not line.startswith("#"):
                                first_line = line[:32] + "..." if len(line) > 32 else line
                                break
                        row.append(first_line)
                    except Exception:
                        row.append("[error]")

                table.add_row(*row)

            return table

        # Build title
        table_title = "All Notes"
        if tag:
            table_title = f"Notes tagged '{tag}'"

        # Use pagination or show all
        if no_pagination or len(notes_metadata) <= page_size:
            # Show all results
            table = build_table(notes_metadata, table_title)
            console.print(table)
        else:
            # Use pagination
            paginator = _paginate_results(notes_metadata, page_size)
            for page_info in paginator:
                # Clear screen for better UX (optional)
                console.clear()

                # Build and display table for current page
                page_title = f"{table_title} (Page {page_info['page']}/{page_info['total_pages']})"
                table = build_table(page_info["items"], page_title)
                console.print(table)

        console.print("\n[dim]Tip: Use 'notes open <ID>' or 'notes open <title>' to open[/dim]")

    except Exception as e:
        console.print(f"[red]Error listing notes: {e}[/red]")


@main.command()
@click.option("--limit", "-n", default=5, help="Number of recent notes (default: 5)")
def recent(limit):
    """Show recently modified notes (shortcut for 'list --sort modified').

    Examples:
        notes recent        # Show 5 most recent
        notes recent -n 10  # Show 10 most recent
    """
    # Delegate to list command with defaults
    ctx = click.Context(list_cmd)
    ctx.invoke(
        list_cmd, preview=False, sort="modified", page_size=limit, tag=None, no_pagination=True
    )


@main.command()
def tags():
    """List all tags."""
    config = Config()
    storage = Storage(config)

    # Collect all tags
    all_tags = {}
    for file_path in storage.list_notes():
        try:
            note = storage.load_note(file_path)
            for tag in note.tags:
                all_tags[tag] = all_tags.get(tag, 0) + 1
        except Exception:
            continue

    if not all_tags:
        console.print("[yellow]No tags found[/yellow]")
        return

    # Display tags
    table = Table(title="All Tags")
    table.add_column("Tag", style="blue")
    table.add_column("Count", style="cyan")

    for tag, count in sorted(all_tags.items(), key=lambda x: x[1], reverse=True):
        table.add_row(tag, str(count))

    console.print(table)


@main.command()
@click.argument("note_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def delete(note_id, yes):
    """Delete a note by ID (use 'notes search' to find IDs)."""
    config = Config()
    storage = Storage(config)
    index = SearchIndex(config)

    try:
        # Validate ID format
        if not (note_id.isdigit() and len(note_id) == 14):
            console.print(f"[red]Error: Invalid note ID '{note_id}'[/red]")
            console.print("[yellow]Tip: Use 'notes search <query>' to find note IDs[/yellow]")
            return

        # Find note by ID
        try:
            file_path = storage.find_by_id(note_id)
        except FileNotFoundError:
            console.print(f"[red]Error: Note with ID '{note_id}' not found[/red]")
            return

        note = storage.load_note(file_path)

        # Show note info
        console.print(
            Panel.fit(
                f"[bold red]Delete Note?[/bold red]\n\n"
                f"ID: {note.note_id}\n"
                f"Title: {note.title}\n"
                f"Modified: {note.modified.strftime('%Y-%m-%d %H:%M')}\n"
                f"Tags: {', '.join(note.tags) if note.tags else 'none'}",
                border_style="red",
            )
        )

        # Confirm deletion
        if not yes:
            confirm = prompt("Type 'yes' to confirm deletion: ")
            if confirm.lower() != "yes":
                console.print("[yellow]Deletion cancelled[/yellow]")
                return

        # Delete file
        file_path.unlink()

        # Remove from index
        index.remove_note(str(file_path))

        # Sync if enabled (background)
        if config.get("auto_sync"):
            _sync_in_background(config, f"Delete note: {note.title}")

        console.print(f"[green]✓[/green] Note deleted: {note.title}")

    except Exception as e:
        console.print(f"[red]Error deleting note: {e}[/red]")
    finally:
        index.close()


@main.command()
def sync():
    """Sync notes with Git remote."""
    config = Config()

    if not config.get("git_remote"):
        console.print("[red]Error: Git remote not configured. Run 'notes config' first.[/red]")
        sys.exit(1)

    git_sync = GitSync(config)

    with console.status("[bold blue]Syncing..."):
        result = git_sync.sync()
        if result:
            console.print("[green]✓[/green] Notes synced successfully")

            # Rebuild index to include any pulled notes (including plain files)
            with console.status("[bold blue]Rebuilding index..."):
                storage = Storage(config)
                index = SearchIndex(config)
                notes = []
                for file_path in storage.list_notes(include_plain=True):
                    try:
                        note = storage.load_note(file_path)
                        notes.append(note)
                    except Exception:
                        continue
                index.rebuild_index(notes)
                index.close()

            if notes:
                console.print(f"[green]✓[/green] Indexed {len(notes)} notes")
        elif result is False:
            console.print("[yellow]⚠[/yellow] Sync completed with warnings (check for conflicts)")
        else:
            console.print("[yellow]No changes to sync[/yellow]")


@main.command()
@click.option("--editor", help="Set default editor")
@click.option("--git-remote", help="Set Git remote URL")
@click.option("--gpg-key", help="Set GPG key ID")
@click.option("--auto-sync/--no-auto-sync", default=None, help="Enable/disable auto-sync")
@click.option("--auto-tag/--no-auto-tag", default=None, help="Enable/disable auto-tagging")
@click.option(
    "--render-preview/--no-render-preview",
    default=None,
    help="Enable/disable markdown rendering by default",
)
@click.option(
    "--llm-provider",
    help="Set LLM provider (openai, claude, ollama)",
)
@click.option("--llm-model", help="Set LLM model name")
@click.option("--llm-key", help="Set LLM API key (encrypted with GPG)")
@click.option("--show", is_flag=True, help="Show current configuration")
def config(
    editor,
    git_remote,
    gpg_key,
    auto_sync,
    auto_tag,
    render_preview,
    llm_provider,
    llm_model,
    llm_key,
    show,
):
    """Configure GPGNotes."""
    cfg = Config()

    if show:
        # Get LLM config
        llm_prov = cfg.get("llm_provider") or "[dim]not configured[/dim]"
        llm_mod = cfg.get("llm_model") or "[dim]default[/dim]"

        # Check if API key is configured
        llm_key_status = "[dim]not set[/dim]"
        if llm_prov and llm_prov != "[dim]not configured[/dim]" and llm_prov != "ollama":
            api_key = cfg.get_secret(f"{llm_prov}_api_key")
            if api_key:
                llm_key_status = f"[green]set ({api_key[:8]}...)[/green]"
        elif llm_prov == "ollama":
            llm_key_status = "[dim]not required[/dim]"

        # Display current config
        console.print(
            Panel.fit(
                f"""[cyan]Configuration[/cyan]

Editor: {cfg.get("editor")}
Git Remote: {cfg.get("git_remote") or "[dim]not configured[/dim]"}
GPG Key: {cfg.get("gpg_key") or "[dim]not configured[/dim]"}
Auto-sync: {"[green]enabled[/green]" if cfg.get("auto_sync") else "[red]disabled[/red]"}
Auto-tag: {"[green]enabled[/green]" if cfg.get("auto_tag") else "[red]disabled[/red]"}
Render Preview: {"[green]enabled[/green]" if cfg.get("render_preview") else "[red]disabled[/red]"}

[bold]LLM Enhancement:[/bold]
Provider: {llm_prov}
Model: {llm_mod}
API Key: {llm_key_status}

Config file: {cfg.config_file}
Notes directory: {cfg.notes_dir}
Secrets file: {cfg._get_secrets_path()}
""",
                title="GPGNotes Configuration",
            )
        )
        return

    # Update config values
    if editor:
        cfg.set("editor", editor)
        console.print(f"[green]✓[/green] Editor set to: {editor}")

    if git_remote:
        cfg.set("git_remote", git_remote)
        console.print(f"[green]✓[/green] Git remote set to: {git_remote}")

        # Initialize repo with remote
        sync = GitSync(cfg)
        sync.init_repo()

    if gpg_key:
        # Verify key exists
        from .encryption import Encryption

        enc = Encryption()
        keys = enc.list_keys()

        if not any(gpg_key in key["keyid"] or gpg_key in key["uids"][0] for key in keys):
            console.print(f"[red]Warning: GPG key '{gpg_key}' not found in keyring[/red]")
            console.print("Available keys:")
            for key in keys:
                console.print(f"  - {key['keyid']}: {key['uids'][0]}")

        cfg.set("gpg_key", gpg_key)
        console.print(f"[green]✓[/green] GPG key set to: {gpg_key}")

    if auto_sync is not None:
        cfg.set("auto_sync", auto_sync)
        status = "enabled" if auto_sync else "disabled"
        console.print(f"[green]✓[/green] Auto-sync {status}")

    if auto_tag is not None:
        cfg.set("auto_tag", auto_tag)
        status = "enabled" if auto_tag else "disabled"
        console.print(f"[green]✓[/green] Auto-tagging {status}")

    if render_preview is not None:
        cfg.set("render_preview", render_preview)
        status = "enabled" if render_preview else "disabled"
        console.print(f"[green]✓[/green] Markdown rendering {status}")

    if llm_provider:
        valid_providers = ["openai", "claude", "ollama"]
        if llm_provider.lower() not in valid_providers:
            console.print(
                f"[red]Error:[/red] Invalid provider. Choose from: {', '.join(valid_providers)}"
            )
            return

        # Default models for each provider
        default_models = {
            "openai": "gpt-4o-mini",
            "claude": "claude-3-5-sonnet-20241022",
            "ollama": "llama3.1",
        }

        cfg.set("llm_provider", llm_provider.lower())
        console.print(f"[green]✓[/green] LLM provider set to: {llm_provider}")

        # Set default model for provider if user didn't specify a model
        if not llm_model:
            default_model = default_models[llm_provider.lower()]
            cfg.set("llm_model", default_model)
            console.print(f"[green]✓[/green] Model set to default: {default_model}")

        if llm_provider.lower() != "ollama":
            console.print(
                "[yellow]Remember to set API key with:[/yellow] notes config --llm-key YOUR_API_KEY"
            )

    if llm_model:
        cfg.set("llm_model", llm_model)
        console.print(f"[green]✓[/green] LLM model set to: {llm_model}")

    if llm_key:
        # Store API key securely
        provider = cfg.get("llm_provider")
        if not provider:
            console.print("[red]Error:[/red] Please set LLM provider first with --llm-provider")
            return

        if provider == "ollama":
            console.print("[yellow]Warning:[/yellow] Ollama doesn't require an API key")
            return

        # Encrypt and store the key
        try:
            cfg.set_secret(f"{provider}_api_key", llm_key)
            console.print(f"[green]✓[/green] API key for {provider} saved securely (GPG-encrypted)")
        except Exception as e:
            console.print(f"[red]Error saving API key:[/red] {e}")
            return

    if not any(
        [
            editor,
            git_remote,
            gpg_key,
            auto_sync is not None,
            auto_tag is not None,
            render_preview is not None,
            llm_provider,
            llm_model,
            llm_key,
            show,
        ]
    ):
        console.print("Use --help to see available options")


@main.command()
def reindex():
    """Rebuild search index from all notes (including plain files)."""
    config = Config()
    storage = Storage(config)
    index = SearchIndex(config)

    with console.status("[bold blue]Rebuilding index..."):
        notes = []
        # Include both encrypted and plain files
        for file_path in storage.list_notes(include_plain=True):
            try:
                note = storage.load_note(file_path)
                notes.append(note)
            except Exception:
                continue

        index.rebuild_index(notes)
        index.close()

    console.print(f"[green]✓[/green] Indexed {len(notes)} notes")


@main.command()
@click.argument("note_id")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["markdown", "text", "html", "json", "rtf", "pdf", "docx"]),
    default="markdown",
    help="Export format",
)
@click.option("--output", "-o", help="Output file path (required for pdf/docx)")
@click.option(
    "--plain",
    is_flag=True,
    help="Export to ~/.gpgnotes/plain/ folder (syncs with git as readable file)",
)
def export(note_id, format, output, plain):
    """Export a note by ID (use 'notes search' to find IDs).

    Supported formats: markdown, text, html, json, rtf, pdf, docx

    Use --plain to export to the plain/ folder within your notes directory.
    These files sync with git and are readable on GitHub.

    Note: pdf and docx formats require the --output option and
    optional dependencies (pip install gpgnotes[import]).
    """
    from .exporter import (
        ExportError,
        MissingDependencyError,
        export_docx,
        export_html,
        export_json,
        export_markdown,
        export_pdf,
        export_rtf,
        export_text,
    )
    from .git_sync import GitSync

    config = Config()
    storage = Storage(config)

    try:
        # Validate ID format
        if not (note_id.isdigit() and len(note_id) == 14):
            console.print(f"[red]Error: Invalid note ID '{note_id}'[/red]")
            console.print("[yellow]Tip: Use 'notes search <query>' to find note IDs[/yellow]")
            return

        # Find note by ID
        try:
            file_path = storage.find_by_id(note_id)
        except FileNotFoundError:
            console.print(f"[red]Error: Note with ID '{note_id}' not found[/red]")
            return

        note = storage.load_note(file_path)

        # Handle --plain flag: export to plain/ folder
        if plain:
            # Determine file extension based on format
            extensions = {
                "markdown": ".md",
                "text": ".txt",
                "html": ".html",
                "json": ".json",
                "rtf": ".rtf",
                "pdf": ".pdf",
                "docx": ".docx",
            }
            ext = extensions.get(format, ".md")

            # Create plain folder path mirroring the notes structure
            # Must be inside notes_dir so it's included in git sync
            plain_dir = config.notes_dir / "plain"
            # Use note's relative path (YYYY/MM/filename)
            rel_path = file_path.relative_to(config.notes_dir)
            # Change extension from .md.gpg to the export format
            plain_file = plain_dir / rel_path.with_suffix("").with_suffix(ext)
            plain_file.parent.mkdir(parents=True, exist_ok=True)
            output = str(plain_file)

        # Check if output is required for binary formats
        if format in ["pdf", "docx"] and not output:
            console.print(f"[red]Error: --output is required for {format} format[/red]")
            return

        # Generate export content
        if format == "markdown":
            content = export_markdown(note)
        elif format == "text":
            content = export_text(note)
        elif format == "html":
            content = export_html(note)
        elif format == "json":
            content = export_json(note)
        elif format == "rtf":
            content = export_rtf(note)
        elif format == "pdf":
            output_path = Path(output).expanduser()
            with console.status("[bold blue]Exporting to PDF..."):
                export_pdf(note, output_path)
            console.print(f"[green]✓[/green] Exported to: {output_path}")
            # Sync if exported to plain folder
            if plain and config.get("auto_sync") and config.get("git_remote"):
                with console.status("[bold blue]Syncing changes..."):
                    git_sync = GitSync(config)
                    git_sync.sync(f"Export note to plain: {note.title}")
            return
        elif format == "docx":
            output_path = Path(output).expanduser()
            with console.status("[bold blue]Exporting to DOCX..."):
                export_docx(note, output_path)
            console.print(f"[green]✓[/green] Exported to: {output_path}")
            # Sync if exported to plain folder
            if plain and config.get("auto_sync") and config.get("git_remote"):
                with console.status("[bold blue]Syncing changes..."):
                    git_sync = GitSync(config)
                    git_sync.sync(f"Export note to plain: {note.title}")
            return

        # Output to file or stdout (for text-based formats)
        if output:
            output_path = Path(output).expanduser()
            output_path.write_text(content, encoding="utf-8")
            console.print(f"[green]✓[/green] Exported to: {output_path}")
            # Sync if exported to plain folder
            if plain and config.get("auto_sync") and config.get("git_remote"):
                with console.status("[bold blue]Syncing changes..."):
                    git_sync = GitSync(config)
                    git_sync.sync(f"Export note to plain: {note.title}")
        else:
            console.print(content)

    except MissingDependencyError as e:
        console.print(f"[red]Error:[/red] {e}")
    except ExportError as e:
        console.print(f"[red]Export error:[/red] {e}")
    except Exception as e:
        console.print(f"[red]Error exporting notes: {e}[/red]")


@main.command(name="import")
@click.argument("sources", nargs=-1, required=True)
@click.option("--title", "-t", help="Custom title for the imported note (single source only)")
@click.option("--tags", help="Comma-separated tags to add")
def import_file(sources, title, tags):
    """Import external files or URLs as encrypted notes.

    Supported formats: .md, .txt, .rtf, .pdf, .docx, URLs

    Examples:
        notes import document.pdf
        notes import report.docx --title "Q4 Report" --tags work,quarterly
        notes import https://example.com/article --title "Article"
        notes import *.md
    """
    from .importer import ImportError as ImporterError
    from .importer import MissingDependencyError, import_url
    from .importer import import_file as do_import
    from .llm import sanitize_for_gpg

    config = Config()

    # Check if GPG key is configured
    if not config.get("gpg_key"):
        console.print("[red]Error: GPG key not configured. Run 'notes init' first.[/red]")
        sys.exit(1)

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    # Add web-clip tag if importing URL
    if any(source.startswith(("http://", "https://")) for source in sources):
        if "web-clip" not in tag_list:
            tag_list.append("web-clip")

    # Validate title option with multiple sources
    if title and len(sources) > 1:
        console.print("[yellow]Warning: --title ignored when importing multiple sources[/yellow]")
        title = None

    storage = Storage(config)
    index = SearchIndex(config)
    tagger = AutoTagger()

    imported_count = 0
    failed_count = 0

    try:
        for source_str in sources:
            try:
                # Check if it's a URL
                if source_str.startswith(("http://", "https://")):
                    # Import URL
                    with console.status(f"[bold blue]Clipping {source_str}..."):
                        note_title, content = import_url(source_str, title)
                        # Sanitize content for GPG
                        content = sanitize_for_gpg(content)
                        note_title = sanitize_for_gpg(note_title)

                    source_name = source_str
                else:
                    # Import file
                    file_path = Path(source_str)

                    # Check if file exists
                    if not file_path.exists():
                        console.print(f"[red]✗[/red] File not found: {source_str}")
                        failed_count += 1
                        continue

                    with console.status(f"[bold blue]Importing {file_path.name}..."):
                        note_title, content = do_import(file_path, title)
                        # Sanitize content for GPG (convert smart quotes, etc.)
                        content = sanitize_for_gpg(content)
                        note_title = sanitize_for_gpg(note_title)

                    source_name = file_path.name

                # Create note
                note = Note(title=note_title, content=content, tags=tag_list.copy())

                # Auto-tag if enabled and no tags provided
                if config.get("auto_tag") and not tag_list:
                    auto_tags = tagger.extract_tags(content, note_title)
                    note.tags = auto_tags

                # Save note
                storage.save_note(note)
                index.add_note(note)

                console.print(f"[green]✓[/green] Imported: {source_name} → {note.title}")
                if note.tags:
                    console.print(f"  [blue]Tags:[/blue] {', '.join(note.tags)}")

                imported_count += 1

            except MissingDependencyError as e:
                console.print(f"[red]✗[/red] {source_str}: {e}")
                failed_count += 1
            except ImporterError as e:
                console.print(f"[red]✗[/red] {source_str}: {e}")
                failed_count += 1
            except Exception as e:
                console.print(f"[red]✗[/red] {source_str}: {e}")
                failed_count += 1

        # Summary
        if len(sources) > 1:
            console.print(
                f"\n[cyan]Summary:[/cyan] {imported_count} imported, {failed_count} failed"
            )

        # Sync if enabled
        if imported_count > 0 and config.get("auto_sync"):
            _sync_in_background(config, f"Import {imported_count} item(s)")

    finally:
        index.close()


@main.command()
@click.argument("url")
@click.option("--title", "-t", help="Custom title for the note")
@click.option("--tags", help="Comma-separated tags to add")
def clip(url, title, tags):
    """Clip a web page as a note (alias for 'import <url>').

    Examples:
        notes clip https://example.com/article
        notes clip https://example.com/article --title "Great Article"
        notes clip https://example.com/article --tags reading,tech
    """
    # Delegate to import command
    ctx = click.Context(import_file)
    ctx.invoke(import_file, sources=(url,), title=title, tags=tags)


@main.command()
@click.argument("note_id")
@click.option(
    "--instructions",
    "-i",
    help="Enhancement instructions (e.g., 'fix grammar', 'make more concise')",
)
@click.option("--quick", is_flag=True, help="Quick mode: auto-apply without interaction")
def enhance(note_id, instructions, quick):
    """Enhance note content using LLM assistance."""
    config = Config()
    storage = Storage(config)
    index = SearchIndex(config)

    try:
        # Check if LLM is configured
        if not config.get("llm_provider"):
            console.print("[red]Error: No LLM provider configured.[/red]")
            console.print(
                "\nTo set up LLM enhancement:\n"
                "  [cyan]notes config --llm-provider openai[/cyan]  # or claude, ollama\n"
                "  [cyan]notes config --llm-key YOUR_API_KEY[/cyan] # not needed for ollama\n"
            )
            return

        # Validate ID format
        if not (note_id.isdigit() and len(note_id) == 14):
            console.print(f"[red]Error: Invalid note ID '{note_id}'[/red]")
            console.print("[yellow]Tip: Use 'notes search <query>' to find note IDs[/yellow]")
            return

        # Find note by ID
        try:
            file_path = storage.find_by_id(note_id)
        except FileNotFoundError:
            console.print(f"[red]Error: Note with ID '{note_id}' not found[/red]")
            return

        # Load note
        note = storage.load_note(file_path)

        # Quick mode - non-interactive
        if quick:
            if not instructions:
                instructions = "Fix grammar and improve clarity"

            console.print(f"\n[bold blue]Enhancing note:[/bold blue] {note.title}")
            console.print(f"[bold blue]Instructions:[/bold blue] {instructions}\n")

            try:
                from .enhance import quick_enhance

                with console.status("[bold blue]Enhancing with LLM..."):
                    enhanced_note = quick_enhance(note, config, instructions)

                # Save the enhanced note
                storage.save_note(enhanced_note)
                index.add_note(enhanced_note)

                console.print("\n[green]✓ Note enhanced and saved[/green]")

                # Sync if enabled
                if config.get("auto_sync"):
                    _sync_in_background(config, f"Enhance note: {note.title}")

            except Exception as e:
                console.print(f"[red]Enhancement failed:[/red] {e}")
                return

        else:
            # Interactive mode
            from .enhance import EnhancementSession

            session = EnhancementSession(note, config)

            # Run interactive enhancement
            saved = session.enhance(instructions)

            if saved:
                # Save the enhanced note
                storage.save_note(note)
                index.add_note(note)

                console.print("\n[green]✓ Enhanced note saved[/green]")

                # Sync if enabled
                if config.get("auto_sync"):
                    _sync_in_background(config, f"Enhance note: {note.title}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
    finally:
        index.close()


@main.group()
def template():
    """Manage note templates."""
    pass


@template.command("list")
def template_list():
    """List all available templates."""
    config = Config()
    templates_dir = config.config_dir / "templates"
    template_mgr = TemplateManager(templates_dir)

    templates = template_mgr.list_templates()

    if not templates["builtin"] and not templates["custom"]:
        console.print("[yellow]No templates found[/yellow]")
        return

    # Display built-in templates
    if templates["builtin"]:
        console.print("\n[bold cyan]Built-in Templates:[/bold cyan]")
        for name in templates["builtin"]:
            console.print(f"  • {name}")

    # Display custom templates
    if templates["custom"]:
        console.print("\n[bold cyan]Custom Templates:[/bold cyan]")
        for name in templates["custom"]:
            console.print(f"  • {name}")

    console.print(
        "\n[dim]Use 'notes new \"Title\" --template <name>' to create a note from a template[/dim]"
    )


@template.command("show")
@click.argument("name")
def template_show(name):
    """Show template content."""
    config = Config()
    templates_dir = config.config_dir / "templates"
    template_mgr = TemplateManager(templates_dir)

    content = template_mgr.get_template(name)
    if not content:
        console.print(f"[red]Error: Template '{name}' not found[/red]")
        return

    # Extract variables
    variables = TemplateEngine.extract_variables(content)

    console.print(f"\n[bold cyan]Template: {name}[/bold cyan]")
    if variables:
        console.print(f"[dim]Variables: {', '.join(variables)}[/dim]\n")
    else:
        console.print("[dim]No custom variables[/dim]\n")

    console.print(content)


@template.command("create")
@click.argument("name")
@click.option("--from-note", help="Create template from existing note ID")
def template_create(name, from_note):
    """Create a new custom template."""
    config = Config()
    templates_dir = config.config_dir / "templates"
    template_mgr = TemplateManager(templates_dir)

    # Check if template already exists
    if template_mgr.template_exists(name):
        console.print(f"[red]Error: Template '{name}' already exists[/red]")
        console.print("[yellow]Use 'notes template edit' to modify existing templates[/yellow]")
        return

    if from_note:
        # Create template from existing note
        storage = Storage(config)
        try:
            file_path = storage.find_by_id(from_note)
            note = storage.load_note(file_path)

            # Convert note to template format
            content = f"""---
title: "{{{{title}}}}"
tags: {note.tags}
---

{note.content}
"""
            template_mgr.save_template(name, content)
            console.print(f"[green]✓[/green] Template '{name}' created from note {from_note}")

        except FileNotFoundError:
            console.print(f"[red]Error: Note with ID '{from_note}' not found[/red]")
            return
    else:
        # Create template interactively
        console.print(f"[cyan]Creating template '{name}'[/cyan]")
        console.print("[dim]Enter template content (Ctrl+D or Ctrl+Z when done):[/dim]\n")

        try:
            lines = []
            while True:
                try:
                    line = input()
                    lines.append(line)
                except EOFError:
                    break

            content = "\n".join(lines)

            if not content.strip():
                console.print("[yellow]Template content cannot be empty[/yellow]")
                return

            template_mgr.save_template(name, content)
            console.print(f"\n[green]✓[/green] Template '{name}' created")

            # Show variables found
            variables = TemplateEngine.extract_variables(content)
            if variables:
                console.print(f"[blue]Variables found:[/blue] {', '.join(variables)}")

        except KeyboardInterrupt:
            console.print("\n[yellow]Template creation cancelled[/yellow]")


@template.command("edit")
@click.argument("name")
def template_edit(name):
    """Edit a template."""
    config = Config()
    templates_dir = config.config_dir / "templates"
    template_mgr = TemplateManager(templates_dir)

    template_path = template_mgr.get_template_path(name)
    if not template_path:
        console.print(f"[red]Error: Template '{name}' not found[/red]")
        return

    # Check if it's a built-in template
    if template_path.parent.name == "builtin":
        console.print(f"[yellow]Cannot edit built-in template '{name}'[/yellow]")
        console.print(
            f"[dim]Tip: Create a custom version with 'notes template create {name} --from-note <id>'[/dim]"
        )
        return

    # Open in editor
    import subprocess

    editor = config.get("editor", "nano")
    try:
        subprocess.run([editor, str(template_path)], check=True)
        console.print(f"[green]✓[/green] Template '{name}' updated")
    except subprocess.CalledProcessError:
        console.print("[red]Error editing template[/red]")
    except FileNotFoundError:
        console.print(f"[red]Editor '{editor}' not found[/red]")


@template.command("delete")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def template_delete(name, yes):
    """Delete a custom template."""
    config = Config()
    templates_dir = config.config_dir / "templates"
    template_mgr = TemplateManager(templates_dir)

    try:
        # Confirm deletion
        if not yes:
            confirm = prompt(f"Delete template '{name}'? Type 'yes' to confirm: ")
            if confirm.lower() != "yes":
                console.print("[yellow]Deletion cancelled[/yellow]")
                return

        if template_mgr.delete_template(name):
            console.print(f"[green]✓[/green] Template '{name}' deleted")
        else:
            console.print(f"[red]Error: Template '{name}' not found[/red]")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")


# Alias for template list
@main.command("templates")
def templates_alias():
    """List all available templates (alias for 'template list')."""
    ctx = click.Context(template_list)
    ctx.invoke(template_list)


# =============================================================================
# Daily Notes (Captain's Log)
# =============================================================================


@main.group(invoke_without_command=True)
@click.pass_context
def daily(ctx):
    """Manage daily notes (Captain's Log).

    Examples:
        notes daily add "Fixed the auth bug"       # Add entry
        notes daily add "Started deployment" -t    # Entry with timestamp
        notes daily show                           # View today's entries
        notes daily summary --month                # Monthly summary
    """
    config = Config()

    # Check if GPG key is configured
    if not config.get("gpg_key"):
        console.print("[red]Error: GPG key not configured. Run 'notes init' first.[/red]")
        sys.exit(1)

    # Store config in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["config"] = config

    if ctx.invoked_subcommand is None:
        # No subcommand - show today's entries
        manager = DailyNoteManager(config)
        note = manager.get_daily_note(datetime.now())

        if note:
            console.print(Panel(Markdown(note.content), title=note.title))
            console.print(f"\n[dim]Entries: {manager.count_entries(note)}[/dim]")
        else:
            console.print("[yellow]No entries for today yet.[/yellow]")
            console.print("[dim]Use 'notes daily add \"your entry\"' to add one.[/dim]")


@daily.command("add")
@click.argument("entry")
@click.option("--time", "-t", is_flag=True, help="Add timestamp prefix to entry")
@click.pass_context
def daily_add(ctx, entry, time):
    """Add an entry to today's daily note.

    Examples:
        notes daily add "Fixed the auth bug"
        notes daily add "Started deployment" --time
    """
    config = ctx.obj["config"]
    manager = DailyNoteManager(config)
    note = manager.get_or_create_daily_note(datetime.now())
    manager.append_entry(note, entry, with_time=time)

    console.print(f"[green]✓[/green] Added to {note.title}")

    # Sync if enabled
    if config.get("auto_sync"):
        _sync_in_background(config, f"Daily entry: {entry[:30]}...")


@daily.command("show")
@click.option("--date", "-d", help="Date to show (YYYY-MM-DD), defaults to today")
@click.option("--week", "-w", is_flag=True, help="Show this week's entries")
@click.pass_context
def daily_show(ctx, date, week):
    """View daily note entries."""
    config = ctx.obj["config"]
    manager = DailyNoteManager(config)

    if week:
        # Show week's entries
        notes = manager.get_notes_for_week(datetime.now())
        if not notes:
            console.print("[yellow]No entries found for this week.[/yellow]")
            return

        for note in notes:
            console.print(Panel(Markdown(note.content), title=note.title))
            console.print()
    else:
        # Show specific day
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                console.print("[red]Error: Invalid date format. Use YYYY-MM-DD[/red]")
                return
        else:
            target_date = datetime.now()

        note = manager.get_daily_note(target_date)

        if note:
            console.print(Panel(Markdown(note.content), title=note.title))
            console.print(f"\n[dim]Entries: {manager.count_entries(note)}[/dim]")
        else:
            date_str = target_date.strftime("%Y-%m-%d")
            console.print(f"[yellow]No entries for {date_str}.[/yellow]")


@daily.command("summary")
@click.option("--month", "-m", is_flag=True, help="Generate monthly summary")
@click.option("--week", "-w", is_flag=True, help="Generate weekly summary")
@click.option("--year", type=int, help="Year for summary (default: current)")
@click.option("--month-num", type=int, help="Month number 1-12 (default: current)")
@click.option("--save", "-s", is_flag=True, help="Save summary as a new note")
@click.pass_context
def daily_summary(ctx, month, week, year, month_num, save):
    """Generate summary from daily notes.

    Examples:
        notes daily summary --month              # Current month summary
        notes daily summary --week               # Current week summary
        notes daily summary --month --year 2025 --month-num 11  # Nov 2025
    """
    config = ctx.obj["config"]
    manager = DailyNoteManager(config)

    now = datetime.now()

    if week:
        notes = manager.get_notes_for_week(now)
        period_type = f"Week of {(now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')}"
    else:
        # Default to month
        target_year = year or now.year
        target_month = month_num or now.month
        notes = manager.get_notes_for_month(target_year, target_month)
        period_type = f"{datetime(target_year, target_month, 1).strftime('%B %Y')}"

    if not notes:
        console.print(f"[yellow]No daily notes found for {period_type}.[/yellow]")
        return

    with console.status(f"[bold blue]Generating summary for {period_type}..."):
        summary = manager.generate_summary(notes, period_type)

    console.print(Panel(Markdown(summary), title=f"Summary: {period_type}"))

    if save:
        # Save as a new note
        from .note import Note as NoteClass

        summary_note = NoteClass(
            title=f"Summary: {period_type}",
            content=summary,
            tags=["summary", "daily", "auto-generated"],
        )
        storage = Storage(config)
        storage.save_note(summary_note)

        index = SearchIndex(config)
        index.add_note(summary_note)
        index.close()

        console.print(f"\n[green]✓[/green] Summary saved as note: {summary_note.note_id}")


@main.command("today")
def today_cmd():
    """Open today's daily note in editor.

    Creates the note if it doesn't exist.
    """
    config = Config()

    # Check if GPG key is configured
    if not config.get("gpg_key"):
        console.print("[red]Error: GPG key not configured. Run 'notes init' first.[/red]")
        sys.exit(1)

    manager = DailyNoteManager(config)
    note = manager.get_or_create_daily_note(datetime.now())

    # Edit the note
    storage = Storage(config)
    note = storage.edit_note(note.file_path)

    # Update index
    index = SearchIndex(config)
    index.add_note(note)
    index.close()

    console.print(f"[green]✓[/green] Updated: {note.title}")

    # Sync if enabled
    if config.get("auto_sync"):
        _sync_in_background(config, f"Update daily: {note.title}")


@main.command("yesterday")
def yesterday_cmd():
    """Open yesterday's daily note in editor.

    Creates the note if it doesn't exist.
    """
    config = Config()

    # Check if GPG key is configured
    if not config.get("gpg_key"):
        console.print("[red]Error: GPG key not configured. Run 'notes init' first.[/red]")
        sys.exit(1)

    manager = DailyNoteManager(config)
    yesterday = datetime.now() - timedelta(days=1)
    note = manager.get_or_create_daily_note(yesterday)

    # Edit the note
    storage = Storage(config)
    note = storage.edit_note(note.file_path)

    # Update index
    index = SearchIndex(config)
    index.add_note(note)
    index.close()

    console.print(f"[green]✓[/green] Updated: {note.title}")

    # Sync if enabled
    if config.get("auto_sync"):
        _sync_in_background(config, f"Update daily: {note.title}")


@main.command("history")
@click.argument("note_id")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed history")
def history_cmd(note_id, verbose):
    """Show version history for a note.

    Examples:
        notes history 20251216120000         # Show history
        notes history 20251216120000 -v      # Show verbose history
    """
    config = Config()
    storage = Storage(config)

    try:
        # Find note
        file_path = storage.find_by_id(note_id)
        note = storage.load_note(file_path)

        # Get version history
        history_mgr = VersionHistory(config.notes_dir)
        versions = history_mgr.get_history(file_path)

        if not versions:
            console.print(f"[yellow]No history found for note '{note.title}'[/yellow]")
            console.print("[dim]Note may not be committed to Git yet[/dim]")
            return

        # Display history
        console.print(f"\n[bold cyan]Version History:[/bold cyan] {note.title}\n")

        table = Table(show_header=True)
        table.add_column("#", style="cyan", width=4)
        table.add_column("Date", style="yellow", width=19)
        table.add_column("Message", style="white", width=50)
        if verbose:
            table.add_column("Commit", style="dim", width=8)
            table.add_column("Author", style="green", width=20)

        for version in versions:
            row = [
                str(version.number) + (" *" if version.is_current else ""),
                version.date.strftime("%Y-%m-%d %H:%M:%S"),
                version.message[:47] + "..." if len(version.message) > 47 else version.message,
            ]
            if verbose:
                row.append(version.commit)
                row.append(
                    version.author[:17] + "..." if len(version.author) > 17 else version.author
                )

            table.add_row(*row)

        console.print(table)
        console.print(f"\n[dim]Total versions: {len(versions)}[/dim]")
        console.print("[dim]* = current version[/dim]\n")
        console.print(f"[dim]Use 'notes show {note_id} -v N' to view version N[/dim]")
        console.print(f"[dim]Use 'notes diff {note_id}' to compare versions[/dim]")
        console.print(f"[dim]Use 'notes restore {note_id} -v N' to restore version N[/dim]")

    except FileNotFoundError:
        console.print(f"[red]Error: Note with ID '{note_id}' not found[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@main.command("show")
@click.argument("note_id")
@click.option("--version", "-v", type=int, help="Show specific version")
@click.option("--at", help="Show version at date (YYYY-MM-DD)")
@click.option("--render", "-r", is_flag=True, help="Render markdown with formatting")
@click.option("--raw", is_flag=True, help="Force raw markdown output")
def show_cmd(note_id, version, at, render, raw):
    """Show note content, optionally at specific version.

    Examples:
        notes show 20251216120000              # Show current version
        notes show 20251216120000 -v 3         # Show version 3
        notes show 20251216120000 --at 2025-12-15
        notes show 20251216120000 --render     # Show with markdown rendering
    """
    config = Config()
    storage = Storage(config)

    try:
        # Find note
        file_path = storage.find_by_id(note_id)
        note = storage.load_note(file_path)

        # Get version if specified
        content = None
        title_suffix = ""

        if version or at:
            history_mgr = VersionHistory(config.notes_dir)
            commit = None

            if version:
                commit = history_mgr.get_version_by_number(file_path, version)
                if not commit:
                    console.print(f"[red]Error: Version {version} not found[/red]")
                    return
                title_suffix = f" [dim](Version {version})[/dim]"
            elif at:
                commit = history_mgr.get_file_at_date(file_path, at)
                if not commit:
                    console.print(f"[red]Error: No version found at date {at}[/red]")
                    return
                title_suffix = f" [dim](Version at {at})[/dim]"

            # Get historical content
            content_bytes = history_mgr.get_version_content(file_path, commit)

            # Decrypt if encrypted
            if file_path.suffix == ".gpg":
                import tempfile

                from .encryption import Encryption

                encryption = Encryption(config.get("gpg_key"))
                with tempfile.NamedTemporaryFile(suffix=".gpg", delete=False) as tmp:
                    tmp.write(content_bytes)
                    tmp_path = Path(tmp.name)

                try:
                    content = encryption.decrypt(tmp_path)
                finally:
                    tmp_path.unlink()
            else:
                content = content_bytes.decode("utf-8")
        else:
            # Use current content
            content = note.content

        # Determine if we should render
        should_render = render or (config.get("render_preview") and not raw)

        if should_render:
            # Render with markdown
            console.print(
                Panel(
                    f"[bold cyan]{note.title}[/bold cyan]{title_suffix}",
                    subtitle=f"Modified: {note.modified.strftime('%Y-%m-%d %H:%M')}"
                    if not title_suffix
                    else None,
                    border_style="cyan",
                )
            )
            console.print()
            md = Markdown(content)
            console.print(md)
        else:
            # Raw output
            console.print(f"\n[bold cyan]{note.title}[/bold cyan]{title_suffix}\n")
            console.print(content)

    except FileNotFoundError:
        console.print(f"[red]Error: Note with ID '{note_id}' not found[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@main.command("diff")
@click.argument("note_id")
@click.option("--from-ver", "-f", type=int, help="From version (default: previous)")
@click.option("--to-ver", "-t", type=int, help="To version (default: current)")
def diff_cmd(note_id, from_ver, to_ver):
    """Compare note versions.

    Examples:
        notes diff 20251216120000              # Compare current with previous
        notes diff 20251216120000 -f 2 -t 4    # Compare version 2 to 4
    """
    config = Config()
    storage = Storage(config)

    try:
        # Find note
        file_path = storage.find_by_id(note_id)
        note = storage.load_note(file_path)

        history_mgr = VersionHistory(config.notes_dir)
        versions = history_mgr.get_history(file_path)

        if len(versions) < 2:
            console.print("[yellow]Note has only one version, nothing to compare[/yellow]")
            return

        # Determine versions to compare
        if from_ver is None and to_ver is None:
            # Default: compare current with previous
            from_commit = versions[1].commit
            to_commit = versions[0].commit
            from_label = f"Version {versions[1].number}"
            to_label = f"Version {versions[0].number} (current)"
        else:
            from_commit = history_mgr.get_version_by_number(
                file_path, from_ver or versions[-1].number
            )
            to_commit = history_mgr.get_version_by_number(file_path, to_ver or versions[0].number)

            if not from_commit or not to_commit:
                console.print("[red]Error: Invalid version numbers[/red]")
                return

            from_label = f"Version {from_ver or versions[-1].number}"
            to_label = f"Version {to_ver or versions[0].number}"

        # Create decrypt function if needed
        decrypt_func = None
        if file_path.suffix == ".gpg":
            import tempfile

            from .encryption import Encryption

            encryption = Encryption(config.get("gpg_key"))

            def decrypt_func(content_bytes: bytes) -> str:
                """Helper to decrypt content bytes."""
                with tempfile.NamedTemporaryFile(suffix=".gpg", delete=False) as tmp:
                    tmp.write(content_bytes)
                    tmp_path = Path(tmp.name)

                try:
                    return encryption.decrypt(tmp_path)
                finally:
                    tmp_path.unlink()

        # Get diff
        diff_output = history_mgr.diff_versions(file_path, from_commit, to_commit, decrypt_func)

        if not diff_output:
            console.print("[yellow]No differences found[/yellow]")
            return

        # Parse and display diff
        console.print(f"\n[bold cyan]Comparing:[/bold cyan] {note.title}")
        console.print(f"[dim]{from_label} → {to_label}[/dim]\n")

        parsed_diff = parse_diff_output(diff_output)
        for change_type, line in parsed_diff:
            if change_type == "add":
                console.print(f"[green]+ {line}[/green]")
            elif change_type == "del":
                console.print(f"[red]- {line}[/red]")
            elif change_type == "hdr":
                console.print(f"[dim]{line}[/dim]")
            else:
                console.print(f"  {line}")

    except FileNotFoundError:
        console.print(f"[red]Error: Note with ID '{note_id}' not found[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@main.command("preview")
@click.argument("note_id")
def preview_cmd(note_id):
    """Show note with markdown rendering (alias for 'show --render').

    Examples:
        notes preview 20251216120000
    """
    config = Config()
    storage = Storage(config)

    try:
        # Find note
        file_path = storage.find_by_id(note_id)
        note = storage.load_note(file_path)

        # Render with markdown
        console.print(
            Panel(
                f"[bold cyan]{note.title}[/bold cyan]",
                subtitle=f"Modified: {note.modified.strftime('%Y-%m-%d %H:%M')}",
                border_style="cyan",
            )
        )
        console.print()

        # Render markdown content
        md = Markdown(note.content)
        console.print(md)

        console.print(f"\n[dim]ID: {note.note_id}[/dim]")
        if note.tags:
            console.print(f"[dim]Tags: {', '.join(note.tags)}[/dim]")

    except FileNotFoundError:
        console.print(f"[red]Error: Note with ID '{note_id}' not found[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@main.command("restore")
@click.argument("note_id")
@click.option("--version", "-v", type=int, required=True, help="Version to restore")
@click.option("--preview", is_flag=True, help="Preview version before restoring")
def restore_cmd(note_id, version, preview):
    """Restore note to a previous version (non-destructive).

    Examples:
        notes restore 20251216120000 -v 3          # Restore to version 3
        notes restore 20251216120000 -v 3 --preview
    """
    config = Config()
    storage = Storage(config)

    try:
        # Find note
        file_path = storage.find_by_id(note_id)
        note = storage.load_note(file_path)

        history_mgr = VersionHistory(config.notes_dir)
        commit = history_mgr.get_version_by_number(file_path, version)

        if not commit:
            console.print(f"[red]Error: Version {version} not found[/red]")
            console.print("[dim]Use 'notes history <id>' to see available versions[/dim]")
            return

        # Get historical content
        content_bytes = history_mgr.get_version_content(file_path, commit)

        # Decrypt if encrypted
        if file_path.suffix == ".gpg":
            import tempfile

            from .encryption import Encryption

            encryption = Encryption(config.get("gpg_key"))
            with tempfile.NamedTemporaryFile(suffix=".gpg", delete=False) as tmp:
                tmp.write(content_bytes)
                tmp_path = Path(tmp.name)

            try:
                content = encryption.decrypt(tmp_path)
            finally:
                tmp_path.unlink()
        else:
            content = content_bytes.decode("utf-8")

        if preview:
            # Just show the content
            console.print(
                f"\n[bold cyan]Preview:[/bold cyan] {note.title} [dim](Version {version})[/dim]\n"
            )
            console.print(content)
            console.print(f"\n[dim]Use 'notes restore {note_id} -v {version}' to restore[/dim]")
        else:
            # Restore the version
            note.content = content
            storage.save_note(note)

            # Re-index
            index = SearchIndex(config)
            index.add_note(note)
            index.close()

            # Sync if enabled
            if config.get("auto_sync"):
                _sync_in_background(config, f"Restore note '{note.title}' to version {version}")

            console.print(f"[green]✓[/green] Note restored to version {version}")
            console.print(
                f"[dim]This created a new version. Use 'notes history {note_id}' to see it.[/dim]"
            )

    except FileNotFoundError:
        console.print(f"[red]Error: Note with ID '{note_id}' not found[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


class NotesCompleter(Completer):
    """Custom completer that provides note titles after certain commands."""

    COMMANDS = [
        "new",
        "list",
        "recent",
        "open",
        "delete",
        "import",
        "clip",
        "enhance",
        "tags",
        "templates",
        "export",
        "sync",
        "config",
        "history",
        "daily",
        "today",
        "yesterday",
        "help",
        "exit",
    ]

    # Commands that accept note titles as arguments
    NOTE_COMMANDS = ["open", "delete", "enhance", "export"]

    def __init__(self, storage: Storage):
        self.storage = storage
        self._note_cache = None
        self._cache_time = None

    def _get_note_titles(self):
        """Get note titles with caching."""
        import time

        # Cache for 5 seconds
        if self._cache_time and time.time() - self._cache_time < 5:
            return self._note_cache

        titles = []
        for file_path in self.storage.list_notes():
            try:
                note = self.storage.load_note(file_path)
                titles.append((note.title, note.note_id))
            except Exception:
                continue

        self._note_cache = titles
        self._cache_time = time.time()
        return titles

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        words = text.split()

        if len(words) == 0 or (len(words) == 1 and not text.endswith(" ")):
            # Complete command
            word = words[0] if words else ""
            for cmd in self.COMMANDS:
                if cmd.startswith(word.lower()):
                    yield Completion(cmd, start_position=-len(word))

        elif len(words) >= 1 and text.endswith(" ") or len(words) >= 2:
            # Complete argument
            cmd = words[0].lower()
            if cmd in self.NOTE_COMMANDS:
                # Complete with note titles
                partial = words[1] if len(words) > 1 and not text.endswith(" ") else ""
                partial_lower = partial.lower()

                for title, note_id in self._get_note_titles():
                    if partial_lower in title.lower() or partial_lower in note_id:
                        # Show title, complete with ID for reliability
                        display = f"{title} ({note_id})"
                        yield Completion(
                            note_id,
                            start_position=-len(partial),
                            display=display,
                            display_meta="note",
                        )


def interactive_mode():
    """Interactive mode with fuzzy search and command history."""
    cfg = Config()
    storage = Storage(cfg)

    # Set up command history
    history_file = cfg.config_dir / "command_history"
    history = FileHistory(str(history_file))

    console.print(
        Panel.fit(
            "[cyan]GPGNotes[/cyan] - Interactive Mode\n\n"
            "Type to search, or use commands:\n"
            "  [green]new[/green] - Create new note\n"
            "  [green]list[/green] - List all notes\n"
            "  [green]recent[/green] - Show recent notes\n"
            "  [green]open <ID|title>[/green] - Open a note\n"
            "  [green]delete <ID>[/green] - Delete a note\n"
            "  [green]import <file|URL>[/green] - Import file/URL as note\n"
            "  [green]clip <URL>[/green] - Clip web page as note\n"
            "  [green]enhance <ID>[/green] - Enhance note with AI\n"
            '  [green]daily "entry"[/green] - Quick daily log entry\n'
            "  [green]today[/green] - Open today's daily note\n"
            "  [green]yesterday[/green] - Open yesterday's note\n"
            "  [green]tags[/green] - Show all tags\n"
            "  [green]templates[/green] - List note templates\n"
            "  [green]export <ID>[/green] - Export a note\n"
            "  [green]sync[/green] - Sync with Git\n"
            "  [green]config[/green] - Configuration\n"
            "  [green]history[/green] - Show command history\n"
            "  [green]help or ?[/green] - Show help\n"
            "  [green]exit[/green] - Exit\n\n"
            "[dim]Tip: Use Tab to autocomplete note titles after open/delete/export[/dim]",
            title="Welcome",
        )
    )

    # Create completer with note title support
    completer = NotesCompleter(storage)

    # Create a session with history support
    session = PromptSession(history=history, completer=completer)

    while True:
        try:
            user_input = session.prompt("notes> ").strip()

            if not user_input:
                continue

            # Parse command and arguments
            parts = user_input.split(maxsplit=1)
            command = parts[0]
            args = parts[1] if len(parts) > 1 else None

            if command == "exit":
                break
            elif command in ["help", "?"]:
                # Show help panel
                console.print(
                    Panel.fit(
                        "[cyan]Available Commands:[/cyan]\n\n"
                        '  [green]new "Title"[/green] - Create new note\n'
                        '  [green]new "Title" --template bug[/green] - Create from template\n'
                        "  [green]list[/green] - List all notes (--preview, --sort, --tag)\n"
                        "  [green]recent[/green] - Show recent notes\n"
                        "  [green]open <ID|title>[/green] - Open a note by ID or title\n"
                        "  [green]delete <ID>[/green] - Delete a note by ID\n"
                        "  [green]import <file|URL>[/green] - Import file or URL as note\n"
                        "  [green]clip <URL>[/green] - Clip web page as note\n"
                        "  [green]enhance <ID>[/green] - Enhance note with AI\n"
                        '  [green]daily "entry"[/green] - Quick daily log entry\n'
                        "  [green]daily[/green] - Show today's daily entries\n"
                        "  [green]today[/green] - Open today's daily note\n"
                        "  [green]yesterday[/green] - Open yesterday's note\n"
                        "  [green]tags[/green] - Show all tags\n"
                        "  [green]templates[/green] - List available templates\n"
                        "  [green]templates <name>[/green] - Show template content\n"
                        "  [green]export <ID>[/green] - Export a note by ID\n"
                        "  [green]sync[/green] - Sync with Git\n"
                        "  [green]config[/green] - Configuration\n"
                        "  [green]history [N][/green] - Show last N commands (default: 20)\n"
                        "  [green]help or ?[/green] - Show this help\n"
                        "  [green]exit[/green] - Exit\n\n"
                        "[dim]Type text to search for notes[/dim]\n"
                        "[dim]Use Tab to autocomplete note titles[/dim]",
                        title="GPGNotes Help",
                    )
                )
            elif command == "new":
                ctx = click.Context(new)
                # Parse title and options
                title = None
                template = None
                tags = None
                if args:
                    import shlex

                    # Try to parse with shlex for proper quote handling
                    try:
                        parts = shlex.split(args)
                    except ValueError:
                        parts = args.split()

                    # First non-option argument is the title
                    i = 0
                    while i < len(parts):
                        part = parts[i]
                        if part == "--template" and i + 1 < len(parts):
                            template = parts[i + 1]
                            i += 2
                        elif part == "-t" and i + 1 < len(parts):
                            tags = parts[i + 1]
                            i += 2
                        elif part == "--tags" and i + 1 < len(parts):
                            tags = parts[i + 1]
                            i += 2
                        elif not part.startswith("-") and title is None:
                            title = part
                            i += 1
                        else:
                            i += 1

                ctx.invoke(new, title=title, tags=tags, template=template, var=())
            elif command == "list":
                ctx = click.Context(list_cmd)
                ctx.invoke(
                    list_cmd,
                    preview=False,
                    sort="modified",
                    page_size=20,
                    tag=None,
                    no_pagination=False,
                )
            elif command == "recent":
                ctx = click.Context(list_cmd)
                ctx.invoke(
                    list_cmd,
                    preview=False,
                    sort="modified",
                    page_size=5,
                    tag=None,
                    no_pagination=True,
                )
            elif command == "open" and args:
                ctx = click.Context(open)
                ctx.invoke(open, note_id=args, last=False)
            elif command == "delete" and args:
                ctx = click.Context(delete)
                ctx.invoke(delete, note_id=args, yes=False)
            elif command == "import" and args:
                # Import supports file path or URL as argument
                if args.startswith(("http://", "https://")):
                    # URL import
                    ctx = click.Context(import_file)
                    ctx.invoke(import_file, sources=(args,), title=None, tags=None)
                else:
                    # File import
                    file_path = Path(args).expanduser()
                    if not file_path.exists():
                        console.print(f"[red]Error: File not found: {args}[/red]")
                    else:
                        ctx = click.Context(import_file)
                        ctx.invoke(import_file, sources=(str(file_path),), title=None, tags=None)
            elif command == "clip" and args:
                # Clip URL
                ctx = click.Context(clip)
                ctx.invoke(clip, url=args, title=None, tags=None)
            elif command == "tags":
                ctx = click.Context(tags)
                ctx.invoke(tags)
            elif command == "templates":
                if args:
                    # Show specific template
                    ctx = click.Context(template_show)
                    ctx.invoke(template_show, name=args)
                else:
                    # List all templates
                    ctx = click.Context(templates_alias)
                    ctx.invoke(templates_alias)
            elif command == "enhance" and args:
                ctx = click.Context(enhance)
                ctx.invoke(enhance, note_id=args, instructions=None, quick=False)
            elif command == "export" and args:
                ctx = click.Context(export)
                ctx.invoke(export, note_id=args, format="markdown", output=None, plain=False)
            elif command == "sync":
                ctx = click.Context(sync)
                ctx.invoke(sync)
            elif command == "config":
                ctx = click.Context(config)
                ctx.invoke(
                    config,
                    editor=None,
                    git_remote=None,
                    gpg_key=None,
                    auto_sync=None,
                    auto_tag=None,
                    render_preview=None,
                    llm_provider=None,
                    llm_model=None,
                    llm_key=None,
                    show=True,
                )
            elif command == "history":
                # Show command history
                try:
                    limit = int(args) if args else 20
                except ValueError:
                    limit = 20

                # Read history from file
                history_entries = list(history.load_history_strings())
                if not history_entries:
                    console.print("[yellow]No command history yet[/yellow]")
                else:
                    # Show most recent commands (history is stored newest first)
                    recent = history_entries[:limit]
                    console.print(f"\n[cyan]Last {len(recent)} commands:[/cyan]\n")
                    for i, cmd in enumerate(reversed(recent), 1):
                        console.print(f"  {i:3}  {cmd}")
                    console.print()
            elif command in ["open", "delete", "enhance", "export"] and not args:
                console.print(f"[yellow]Usage: {command} <ID>[/yellow]")
                console.print("[dim]Tip: Use search to find note IDs[/dim]")
            elif command == "import" and not args:
                console.print("[yellow]Usage: import <file_path|URL>[/yellow]")
                console.print("[dim]Supported: .md, .txt, .rtf, .pdf, .docx, URLs[/dim]")
            elif command == "clip" and not args:
                console.print("[yellow]Usage: clip <URL>[/yellow]")
                console.print("[dim]Example: clip https://example.com/article[/dim]")
            elif command == "daily":
                if args:
                    # Quick entry mode - use add subcommand
                    ctx = click.Context(daily_add)
                    ctx.obj = {"config": Config()}
                    ctx.invoke(daily_add, entry=args, time=False)
                else:
                    # Show today's entries
                    ctx = click.Context(daily)
                    ctx.invoke(daily)
            elif command == "today":
                ctx = click.Context(today_cmd)
                ctx.invoke(today_cmd)
            elif command == "yesterday":
                ctx = click.Context(yesterday_cmd)
                ctx.invoke(yesterday_cmd)
            else:
                # Treat as search query
                ctx = click.Context(search)
                ctx.invoke(search, query=user_input, tag=None, page_size=20, no_pagination=False)

        except KeyboardInterrupt:
            break
        except EOFError:
            break

    console.print("\n[cyan]Goodbye![/cyan]")


if __name__ == "__main__":
    main()
