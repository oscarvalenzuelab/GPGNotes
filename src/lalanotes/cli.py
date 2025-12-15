"""Command-line interface for LalaNotes."""

import atexit
import subprocess
import sys
from pathlib import Path

import click
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import Config
from .index import SearchIndex
from .note import Note
from .storage import Storage
from .sync import GitSync
from .tagging import AutoTagger

console = Console()


def _background_sync():
    """Background sync and auto-tag function to run on exit."""
    try:
        config = Config()

        # Auto-tag recent notes if enabled
        if config.get("auto_tag"):
            storage = Storage(config)
            index = SearchIndex(config)
            tagger = AutoTagger()

            # Get recent notes (modified in last hour)
            from datetime import datetime, timedelta

            recent_files = []
            for file_path in storage.list_notes()[:10]:  # Check last 10 notes
                try:
                    note = storage.load_note(file_path)
                    # If modified in last hour and has no tags or few tags
                    if (
                        datetime.now() - note.modified < timedelta(hours=1)
                        and len(note.tags) < 3
                    ):
                        # Generate and add tags
                        auto_tags = tagger.extract_tags(note.content, note.title)
                        if auto_tags:
                            note.tags = list(set(note.tags + auto_tags))  # Merge tags
                            storage.save_note(note)
                            index.add_note(note)
                            recent_files.append(file_path)
                except Exception:
                    continue

            if recent_files:
                index.close()

        # Sync to git if enabled
        if config.get("auto_sync") and config.get("git_remote"):
            sync = GitSync(config)
            sync.sync("Auto-sync on exit")
    except Exception:
        # Silently fail - we're exiting anyway
        pass


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version="0.1.0")
def main(ctx):
    """LalaNotes - Encrypted note-taking with Git sync."""
    # Register exit handler for background sync
    atexit.register(_background_sync)

    # Check if this is first run (except for init and config commands)
    if ctx.invoked_subcommand not in ["init", "config", None]:
        config = Config()
        if not config.is_configured():
            console.print("[yellow]⚠ LalaNotes is not configured yet.[/yellow]")
            console.print("Run [cyan]notes init[/cyan] to set up your configuration.\n")
            sys.exit(1)

    if ctx.invoked_subcommand is None:
        # Interactive mode - check config first
        config = Config()
        if not config.is_configured():
            console.print("[yellow]⚠ LalaNotes is not configured yet.[/yellow]")
            console.print("Let's set it up now!\n")
            ctx.invoke(init)
            return
        interactive_mode()


@main.command()
def init():
    """Initialize LalaNotes with interactive setup."""
    console.print(
        Panel.fit(
            "[cyan]Welcome to LalaNotes![/cyan]\n\n"
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
            title="LalaNotes Ready!",
        )
    )


@main.command()
@click.argument("title", required=False)
@click.option("--tags", "-t", help="Comma-separated tags")
def new(title, tags):
    """Create a new note."""
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

    # Create note with minimal content
    note = Note(title=title, content="", tags=tag_list)

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

        # Sync if enabled
        if config.get("auto_sync"):
            sync = GitSync(config)
            sync.sync(f"Add note: {note.title}")

        console.print(f"[green]✓[/green] Note created: {note.title}")
        if note.tags:
            console.print(f"[blue]Tags:[/blue] {', '.join(note.tags)}")

    except Exception as e:
        console.print(f"[red]Error creating note: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("query", required=False)
@click.option("--tag", "-t", help="Search by tag")
def search(query, tag):
    """Search notes."""
    config = Config()
    index = SearchIndex(config)

    try:
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

        # Load and display notes
        storage = Storage(config)
        table = Table(title="Search Results")
        table.add_column("#", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Tags", style="blue")
        table.add_column("Modified", style="yellow")

        for i, file_path in enumerate(results[:20], 1):
            try:
                note = storage.load_note(Path(file_path))
                table.add_row(
                    str(i),
                    note.title,
                    ", ".join(note.tags),
                    note.modified.strftime("%Y-%m-%d %H:%M"),
                )
            except Exception:
                continue

        console.print(table)

    finally:
        index.close()


@main.command()
@click.argument("query")
def edit(query):
    """Edit a note by title or search query."""
    config = Config()
    storage = Storage(config)
    index = SearchIndex(config)

    try:
        # Try to find note
        results = index.search(query)

        if not results:
            console.print(f"[yellow]No note found matching '{query}'[/yellow]")
            return

        file_path = Path(results[0][0])

        # Edit note
        note = storage.edit_note(file_path)

        # Re-index
        index.add_note(note)

        # Sync if enabled
        if config.get("auto_sync"):
            sync = GitSync(config)
            sync.sync(f"Update note: {note.title}")

        console.print(f"[green]✓[/green] Note updated: {note.title}")

    except Exception as e:
        console.print(f"[red]Error editing note: {e}[/red]")
    finally:
        index.close()


@main.command()
def list():
    """List all notes."""
    config = Config()
    index = SearchIndex(config)

    try:
        results = index.list_all(limit=50)

        if not results:
            console.print("[yellow]No notes found[/yellow]")
            return

        table = Table(title="All Notes")
        table.add_column("#", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Modified", style="yellow")

        for i, (file_path, title, modified) in enumerate(results, 1):
            table.add_row(str(i), title, modified[:16])

        console.print(table)

    finally:
        index.close()


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
def sync():
    """Sync notes with Git remote."""
    config = Config()

    if not config.get("git_remote"):
        console.print("[red]Error: Git remote not configured. Run 'notes config' first.[/red]")
        sys.exit(1)

    git_sync = GitSync(config)

    with console.status("[bold blue]Syncing..."):
        if git_sync.sync():
            console.print("[green]✓[/green] Notes synced successfully")
        else:
            console.print("[yellow]No changes to sync[/yellow]")


@main.command()
@click.option("--editor", help="Set default editor")
@click.option("--git-remote", help="Set Git remote URL")
@click.option("--gpg-key", help="Set GPG key ID")
@click.option("--auto-sync/--no-auto-sync", default=None, help="Enable/disable auto-sync")
@click.option("--auto-tag/--no-auto-tag", default=None, help="Enable/disable auto-tagging")
@click.option("--show", is_flag=True, help="Show current configuration")
def config(editor, git_remote, gpg_key, auto_sync, auto_tag, show):
    """Configure LalaNotes."""
    cfg = Config()

    if show:
        # Display current config
        console.print(
            Panel.fit(
                f"""[cyan]Configuration[/cyan]

Editor: {cfg.get("editor")}
Git Remote: {cfg.get("git_remote") or "[dim]not configured[/dim]"}
GPG Key: {cfg.get("gpg_key") or "[dim]not configured[/dim]"}
Auto-sync: {"[green]enabled[/green]" if cfg.get("auto_sync") else "[red]disabled[/red]"}
Auto-tag: {"[green]enabled[/green]" if cfg.get("auto_tag") else "[red]disabled[/red]"}

Config file: {cfg.config_file}
Notes directory: {cfg.notes_dir}
""",
                title="LalaNotes Configuration",
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

    if not any([editor, git_remote, gpg_key, auto_sync is not None, auto_tag is not None, show]):
        console.print("Use --help to see available options")


@main.command()
def reindex():
    """Rebuild search index from all notes."""
    config = Config()
    storage = Storage(config)
    index = SearchIndex(config)

    with console.status("[bold blue]Rebuilding index..."):
        notes = []
        for file_path in storage.list_notes():
            try:
                note = storage.load_note(file_path)
                notes.append(note)
            except Exception:
                continue

        index.rebuild_index(notes)
        index.close()

    console.print(f"[green]✓[/green] Indexed {len(notes)} notes")


def interactive_mode():
    """Interactive mode with fuzzy search."""
    console.print(
        Panel.fit(
            "[cyan]LalaNotes[/cyan] - Interactive Mode\n\n"
            "Type to search, or use commands:\n"
            "  [green]new[/green] - Create new note\n"
            "  [green]list[/green] - List all notes\n"
            "  [green]tags[/green] - Show all tags\n"
            "  [green]sync[/green] - Sync with Git\n"
            "  [green]config[/green] - Configuration\n"
            "  [green]exit[/green] - Exit",
            title="Welcome",
        )
    )

    config = Config()
    commands = WordCompleter(["new", "list", "tags", "sync", "config", "exit"])

    while True:
        try:
            user_input = prompt("notes> ", completer=commands)

            if not user_input:
                continue

            if user_input == "exit":
                break
            elif user_input == "new":
                ctx = click.Context(new)
                ctx.invoke(new)
            elif user_input == "list":
                ctx = click.Context(list)
                ctx.invoke(list)
            elif user_input == "tags":
                ctx = click.Context(tags)
                ctx.invoke(tags)
            elif user_input == "sync":
                ctx = click.Context(sync)
                ctx.invoke(sync)
            elif user_input == "config":
                ctx = click.Context(config, obj={"show": True})
                ctx.invoke(config, show=True)
            else:
                # Treat as search query
                ctx = click.Context(search)
                ctx.invoke(search, query=user_input, tag=None)

        except KeyboardInterrupt:
            break
        except EOFError:
            break

    console.print("\n[cyan]Goodbye![/cyan]")


if __name__ == "__main__":
    main()
