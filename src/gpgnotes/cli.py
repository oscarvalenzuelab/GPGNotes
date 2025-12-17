"""Command-line interface for GPGNotes."""

import atexit
import sys
import threading
from pathlib import Path
from typing import Optional

import click
from prompt_toolkit import PromptSession, prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
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
    """Background sync and auto-tag function to run on exit."""
    try:
        # Clear sys.argv to avoid Click parsing issues during exit
        import sys

        original_argv = sys.argv[:]
        sys.argv = [sys.argv[0]] if sys.argv else []

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
                    if datetime.now() - note.modified < timedelta(hours=1) and len(note.tags) < 3:
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

        # Restore sys.argv
        sys.argv = original_argv
    except Exception:
        # Silently fail - we're exiting anyway
        pass


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version="0.1.6")
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
        table.add_column("ID", style="cyan", width=14)
        table.add_column("Title", style="green", width=25)
        table.add_column("Preview", style="white", width=35)
        table.add_column("Tags", style="blue", width=15)
        table.add_column("Modified", style="yellow", width=16)

        for file_path in results[:20]:
            try:
                note = storage.load_note(Path(file_path))

                # Create content preview (first 80 chars)
                preview = note.content.replace("\n", " ").strip()
                if len(preview) > 80:
                    preview = preview[:77] + "..."

                table.add_row(
                    note.note_id,
                    note.title[:23] + "..." if len(note.title) > 23 else note.title,
                    preview,
                    ", ".join(note.tags[:2]) + ("..." if len(note.tags) > 2 else ""),
                    note.modified.strftime("%Y-%m-%d %H:%M"),
                )
            except Exception:
                continue

        console.print(table)

        if len(results) > 20:
            console.print(f"\n[dim]Showing 20 of {len(results)} results[/dim]")

        console.print("\n[dim]Tip: Use 'notes open <ID>' to open a note[/dim]")

    finally:
        index.close()


@main.command()
@click.argument("note_id")
def open(note_id):
    """Open a note by ID (use 'notes search' to find IDs)."""
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


@main.command()
def list():
    """List all notes."""
    config = Config()
    storage = Storage(config)

    try:
        file_paths = storage.list_notes()[:50]

        if not file_paths:
            console.print("[yellow]No notes found[/yellow]")
            return

        table = Table(title="All Notes")
        table.add_column("ID", style="cyan", width=14)
        table.add_column("Title", style="green", width=40)
        table.add_column("Tags", style="blue", width=20)
        table.add_column("Modified", style="yellow", width=16)

        for file_path in file_paths:
            try:
                note = storage.load_note(file_path)
                table.add_row(
                    note.note_id,
                    note.title[:38] + "..." if len(note.title) > 38 else note.title,
                    ", ".join(note.tags[:3]),
                    note.modified.strftime("%Y-%m-%d %H:%M"),
                )
            except Exception:
                continue

        console.print(table)

        if len(file_paths) >= 50:
            console.print("\n[dim]Showing first 50 notes[/dim]")

        console.print("\n[dim]Tip: Use 'notes open <ID>' to open a note[/dim]")

    except Exception as e:
        console.print(f"[red]Error listing notes: {e}[/red]")


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

            # Rebuild index to include any pulled notes
            with console.status("[bold blue]Rebuilding index..."):
                storage = Storage(config)
                index = SearchIndex(config)
                notes = []
                for file_path in storage.list_notes():
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
    "--llm-provider",
    help="Set LLM provider (openai, claude, ollama)",
)
@click.option("--llm-model", help="Set LLM model name")
@click.option("--llm-key", help="Set LLM API key (encrypted with GPG)")
@click.option("--show", is_flag=True, help="Show current configuration")
def config(
    editor, git_remote, gpg_key, auto_sync, auto_tag, llm_provider, llm_model, llm_key, show
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
            llm_provider,
            llm_model,
            llm_key,
            show,
        ]
    ):
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
            plain_dir = config.config_dir / "plain"
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
            return
        elif format == "docx":
            output_path = Path(output).expanduser()
            with console.status("[bold blue]Exporting to DOCX..."):
                export_docx(note, output_path)
            console.print(f"[green]✓[/green] Exported to: {output_path}")
            return

        # Output to file or stdout (for text-based formats)
        if output:
            output_path = Path(output).expanduser()
            output_path.write_text(content, encoding="utf-8")
            console.print(f"[green]✓[/green] Exported to: {output_path}")
        else:
            console.print(content)

    except MissingDependencyError as e:
        console.print(f"[red]Error:[/red] {e}")
    except ExportError as e:
        console.print(f"[red]Export error:[/red] {e}")
    except Exception as e:
        console.print(f"[red]Error exporting notes: {e}[/red]")


@main.command(name="import")
@click.argument("files", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--title", "-t", help="Custom title for the imported note (single file only)")
@click.option("--tags", help="Comma-separated tags to add")
def import_file(files, title, tags):
    """Import external files as encrypted notes.

    Supported formats: .md, .txt, .rtf, .pdf, .docx

    Examples:
        notes import document.pdf
        notes import report.docx --title "Q4 Report" --tags work,quarterly
        notes import *.md
    """
    from .importer import ImportError as ImporterError
    from .importer import MissingDependencyError
    from .importer import import_file as do_import

    config = Config()

    # Check if GPG key is configured
    if not config.get("gpg_key"):
        console.print("[red]Error: GPG key not configured. Run 'notes init' first.[/red]")
        sys.exit(1)

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    # Validate title option with multiple files
    if title and len(files) > 1:
        console.print("[yellow]Warning: --title ignored when importing multiple files[/yellow]")
        title = None

    storage = Storage(config)
    index = SearchIndex(config)
    tagger = AutoTagger()

    imported_count = 0
    failed_count = 0

    try:
        for file_path_str in files:
            file_path = Path(file_path_str)

            try:
                # Import the file
                with console.status(f"[bold blue]Importing {file_path.name}..."):
                    note_title, content = do_import(file_path, title)

                # Create note
                note = Note(title=note_title, content=content, tags=tag_list.copy())

                # Auto-tag if enabled and no tags provided
                if config.get("auto_tag") and not tag_list:
                    auto_tags = tagger.extract_tags(content, note_title)
                    note.tags = auto_tags

                # Save note
                storage.save_note(note)
                index.add_note(note)

                console.print(f"[green]✓[/green] Imported: {file_path.name} → {note.title}")
                if note.tags:
                    console.print(f"  [blue]Tags:[/blue] {', '.join(note.tags)}")

                imported_count += 1

            except MissingDependencyError as e:
                console.print(f"[red]✗[/red] {file_path.name}: {e}")
                failed_count += 1
            except ImporterError as e:
                console.print(f"[red]✗[/red] {file_path.name}: {e}")
                failed_count += 1
            except Exception as e:
                console.print(f"[red]✗[/red] {file_path.name}: {e}")
                failed_count += 1

        # Summary
        if len(files) > 1:
            console.print(
                f"\n[cyan]Summary:[/cyan] {imported_count} imported, {failed_count} failed"
            )

        # Sync if enabled
        if imported_count > 0 and config.get("auto_sync"):
            _sync_in_background(config, f"Import {imported_count} file(s)")

    finally:
        index.close()


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


def interactive_mode():
    """Interactive mode with fuzzy search and command history."""
    cfg = Config()

    # Set up command history
    history_file = cfg.config_dir / "command_history"
    history = FileHistory(str(history_file))

    console.print(
        Panel.fit(
            "[cyan]GPGNotes[/cyan] - Interactive Mode\n\n"
            "Type to search, or use commands:\n"
            "  [green]new[/green] - Create new note\n"
            "  [green]list[/green] - List all notes\n"
            "  [green]open <ID>[/green] - Open a note\n"
            "  [green]delete <ID>[/green] - Delete a note\n"
            "  [green]import <file>[/green] - Import a file as note\n"
            "  [green]enhance <ID>[/green] - Enhance note with AI\n"
            "  [green]tags[/green] - Show all tags\n"
            "  [green]export <ID>[/green] - Export a note\n"
            "  [green]sync[/green] - Sync with Git\n"
            "  [green]config[/green] - Configuration\n"
            "  [green]history[/green] - Show command history\n"
            "  [green]help or ?[/green] - Show help\n"
            "  [green]exit[/green] - Exit\n\n"
            "[dim]Tip: Use Up/Down arrows to navigate command history[/dim]",
            title="Welcome",
        )
    )

    commands = WordCompleter(
        [
            "new",
            "list",
            "open",
            "delete",
            "import",
            "enhance",
            "tags",
            "export",
            "sync",
            "config",
            "history",
            "help",
            "exit",
        ]
    )

    # Create a session with history support
    session = PromptSession(history=history, completer=commands)

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
                        "  [green]new[/green] - Create new note\n"
                        "  [green]list[/green] - List all notes\n"
                        "  [green]open <ID>[/green] - Open a note by ID\n"
                        "  [green]delete <ID>[/green] - Delete a note by ID\n"
                        "  [green]import <file>[/green] - Import file (.md, .txt, .rtf, .pdf, .docx)\n"
                        "  [green]enhance <ID>[/green] - Enhance note with AI\n"
                        "  [green]tags[/green] - Show all tags\n"
                        "  [green]export <ID>[/green] - Export a note by ID\n"
                        "  [green]sync[/green] - Sync with Git\n"
                        "  [green]config[/green] - Configuration\n"
                        "  [green]history [N][/green] - Show last N commands (default: 20)\n"
                        "  [green]help or ?[/green] - Show this help\n"
                        "  [green]exit[/green] - Exit\n\n"
                        "[dim]Type text to search for notes and get their IDs[/dim]\n"
                        "[dim]Use Up/Down arrows to navigate command history[/dim]",
                        title="GPGNotes Help",
                    )
                )
            elif command == "new":
                ctx = click.Context(new)
                ctx.invoke(new)
            elif command == "list":
                ctx = click.Context(list)
                ctx.invoke(list)
            elif command == "open" and args:
                ctx = click.Context(open)
                ctx.invoke(open, note_id=args)
            elif command == "delete" and args:
                ctx = click.Context(delete)
                ctx.invoke(delete, note_id=args, yes=False)
            elif command == "import" and args:
                # Import supports file path as argument
                file_path = Path(args).expanduser()
                if not file_path.exists():
                    console.print(f"[red]Error: File not found: {args}[/red]")
                else:
                    ctx = click.Context(import_file)
                    ctx.invoke(import_file, files=(str(file_path),), title=None, tags=None)
            elif command == "tags":
                ctx = click.Context(tags)
                ctx.invoke(tags)
            elif command == "enhance" and args:
                ctx = click.Context(enhance)
                ctx.invoke(enhance, note_id=args, instructions=None, quick=False)
            elif command == "export" and args:
                ctx = click.Context(export)
                ctx.invoke(export, note_id=args, format="markdown", output=None)
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
                console.print("[yellow]Usage: import <file_path>[/yellow]")
                console.print("[dim]Supported: .md, .txt, .rtf, .pdf, .docx[/dim]")
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
