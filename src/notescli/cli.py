"""Command-line interface for NotesCLI."""

import sys
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from datetime import datetime

from .config import Config
from .storage import Storage
from .note import Note
from .sync import GitSync
from .index import SearchIndex
from .tagging import AutoTagger


console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version="0.1.0")
def main(ctx):
    """NotesCLI - Encrypted note-taking with Git sync."""
    if ctx.invoked_subcommand is None:
        # Interactive mode
        interactive_mode()


@main.command()
@click.argument('title', required=False)
@click.option('--tags', '-t', help='Comma-separated tags')
def new(title, tags):
    """Create a new note."""
    config = Config()

    # Check if GPG key is configured
    if not config.get('gpg_key'):
        console.print("[red]Error: GPG key not configured. Run 'notes config' first.[/red]")
        sys.exit(1)

    # Get title if not provided
    if not title:
        title = prompt("Note title: ")

    if not title:
        console.print("[red]Title cannot be empty[/red]")
        sys.exit(1)

    # Parse tags
    tag_list = [t.strip() for t in tags.split(',')] if tags else []

    # Create note with minimal content
    note = Note(title=title, content="", tags=tag_list)

    # Save and get path
    storage = Storage(config)
    file_path = storage.save_note(note)

    # Now edit it
    try:
        note = storage.edit_note(file_path)

        # Auto-tag if enabled
        if config.get('auto_tag') and not tag_list:
            tagger = AutoTagger()
            auto_tags = tagger.extract_tags(note.content, note.title)
            note.tags = auto_tags
            storage.save_note(note)

        # Index the note
        index = SearchIndex(config)
        index.add_note(note)
        index.close()

        # Sync if enabled
        if config.get('auto_sync'):
            sync = GitSync(config)
            sync.sync(f"Add note: {note.title}")

        console.print(f"[green]✓[/green] Note created: {note.title}")
        if note.tags:
            console.print(f"[blue]Tags:[/blue] {', '.join(note.tags)}")

    except Exception as e:
        console.print(f"[red]Error creating note: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument('query', required=False)
@click.option('--tag', '-t', help='Search by tag')
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
                    ', '.join(note.tags),
                    note.modified.strftime('%Y-%m-%d %H:%M')
                )
            except Exception:
                continue

        console.print(table)

    finally:
        index.close()


@main.command()
@click.argument('query')
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
        if config.get('auto_sync'):
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

    if not config.get('git_remote'):
        console.print("[red]Error: Git remote not configured. Run 'notes config' first.[/red]")
        sys.exit(1)

    git_sync = GitSync(config)

    with console.status("[bold blue]Syncing..."):
        if git_sync.sync():
            console.print("[green]✓[/green] Notes synced successfully")
        else:
            console.print("[yellow]No changes to sync[/yellow]")


@main.command()
@click.option('--editor', help='Set default editor')
@click.option('--git-remote', help='Set Git remote URL')
@click.option('--gpg-key', help='Set GPG key ID')
@click.option('--auto-sync/--no-auto-sync', default=None, help='Enable/disable auto-sync')
@click.option('--auto-tag/--no-auto-tag', default=None, help='Enable/disable auto-tagging')
@click.option('--show', is_flag=True, help='Show current configuration')
def config(editor, git_remote, gpg_key, auto_sync, auto_tag, show):
    """Configure NotesCLI."""
    cfg = Config()

    if show:
        # Display current config
        console.print(Panel.fit(
            f"""[cyan]Configuration[/cyan]

Editor: {cfg.get('editor')}
Git Remote: {cfg.get('git_remote') or '[dim]not configured[/dim]'}
GPG Key: {cfg.get('gpg_key') or '[dim]not configured[/dim]'}
Auto-sync: {'[green]enabled[/green]' if cfg.get('auto_sync') else '[red]disabled[/red]'}
Auto-tag: {'[green]enabled[/green]' if cfg.get('auto_tag') else '[red]disabled[/red]'}

Config file: {cfg.config_file}
Notes directory: {cfg.notes_dir}
""",
            title="NotesCLI Configuration"
        ))
        return

    # Update config values
    if editor:
        cfg.set('editor', editor)
        console.print(f"[green]✓[/green] Editor set to: {editor}")

    if git_remote:
        cfg.set('git_remote', git_remote)
        console.print(f"[green]✓[/green] Git remote set to: {git_remote}")

        # Initialize repo with remote
        sync = GitSync(cfg)
        sync.init_repo()

    if gpg_key:
        # Verify key exists
        from .encryption import Encryption
        enc = Encryption()
        keys = enc.list_keys()

        if not any(gpg_key in key['keyid'] or gpg_key in key['uids'][0] for key in keys):
            console.print(f"[red]Warning: GPG key '{gpg_key}' not found in keyring[/red]")
            console.print("Available keys:")
            for key in keys:
                console.print(f"  - {key['keyid']}: {key['uids'][0]}")

        cfg.set('gpg_key', gpg_key)
        console.print(f"[green]✓[/green] GPG key set to: {gpg_key}")

    if auto_sync is not None:
        cfg.set('auto_sync', auto_sync)
        status = "enabled" if auto_sync else "disabled"
        console.print(f"[green]✓[/green] Auto-sync {status}")

    if auto_tag is not None:
        cfg.set('auto_tag', auto_tag)
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
    console.print(Panel.fit(
        "[cyan]NotesCLI[/cyan] - Interactive Mode\n\n"
        "Type to search, or use commands:\n"
        "  [green]new[/green] - Create new note\n"
        "  [green]list[/green] - List all notes\n"
        "  [green]tags[/green] - Show all tags\n"
        "  [green]sync[/green] - Sync with Git\n"
        "  [green]config[/green] - Configuration\n"
        "  [green]exit[/green] - Exit",
        title="Welcome"
    ))

    config = Config()
    commands = WordCompleter(['new', 'list', 'tags', 'sync', 'config', 'exit'])

    while True:
        try:
            user_input = prompt("notes> ", completer=commands)

            if not user_input:
                continue

            if user_input == 'exit':
                break
            elif user_input == 'new':
                ctx = click.Context(new)
                ctx.invoke(new)
            elif user_input == 'list':
                ctx = click.Context(list)
                ctx.invoke(list)
            elif user_input == 'tags':
                ctx = click.Context(tags)
                ctx.invoke(tags)
            elif user_input == 'sync':
                ctx = click.Context(sync)
                ctx.invoke(sync)
            elif user_input == 'config':
                ctx = click.Context(config, obj={'show': True})
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


if __name__ == '__main__':
    main()
