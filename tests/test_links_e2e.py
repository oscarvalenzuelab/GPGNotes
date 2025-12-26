"""End-to-end tests for wiki links feature."""

import pytest
from datetime import datetime
from pathlib import Path

from gpgnotes.config import Config
from gpgnotes.storage import Storage
from gpgnotes.index import SearchIndex
from gpgnotes.note import Note
from gpgnotes.links import LinkResolver, BacklinksManager, extract_wiki_links
from gpgnotes.blocks import add_block_id, extract_headings


@pytest.fixture
def setup_notes(tmp_path):
    """Set up a small knowledge base with linked notes."""
    config = Config(tmp_path)
    config.ensure_dirs()
    storage = Storage(config)
    index = SearchIndex(config)

    # Create a project plan note
    project = Note(
        title="Project Alpha",
        content="""# Project Alpha

## Overview
This is a major project for Q1 2025.

## Timeline
- Phase 1: January
- Phase 2: February
- Phase 3: March

## Resources
See [[Team Members]] and [[Budget 2025]] for details.

Important decision made here. ^decision1
""",
        tags=["project", "folder:work"],
    )
    project.file_path = config.notes_dir / project.get_relative_path()
    project.file_path.parent.mkdir(parents=True, exist_ok=True)
    storage.save_plain_note(project)
    index.add_note(project)

    # Create team members note
    team = Note(
        title="Team Members",
        content="""# Team Members

## Core Team
- Alice (Lead)
- Bob (Dev)
- Carol (Design)

Working on [[Project Alpha]].
""",
        tags=["team", "folder:work"],
    )
    team.file_path = config.notes_dir / team.get_relative_path()
    team.file_path.parent.mkdir(parents=True, exist_ok=True)
    storage.save_plain_note(team)
    index.add_note(team)

    # Create budget note
    budget = Note(
        title="Budget 2025",
        content="""# Budget 2025

Allocated $50k to [[Project Alpha#Timeline|the project timeline]].

Also funding [[Other Project]].
""",
        tags=["finance", "folder:work"],
    )
    budget.file_path = config.notes_dir / budget.get_relative_path()
    budget.file_path.parent.mkdir(parents=True, exist_ok=True)
    storage.save_plain_note(budget)
    index.add_note(budget)

    # Create meeting notes
    meeting = Note(
        title="Meeting Notes - Jan 15",
        content="""# Meeting Notes

Discussed Project Alpha timeline.

Reference: [[Project Alpha^decision1]]
""",
    )
    meeting.file_path = config.notes_dir / meeting.get_relative_path()
    meeting.file_path.parent.mkdir(parents=True, exist_ok=True)
    storage.save_plain_note(meeting)
    index.add_note(meeting)

    return config, storage, index


class TestWikiLinksE2E:
    """End-to-end tests for the complete wiki links workflow."""

    def test_link_extraction_workflow(self, setup_notes):
        """Test complete workflow of extracting and resolving links."""
        config, storage, index = setup_notes

        # Load the project note
        results = index.search("Project Alpha")
        assert len(results) > 0

        project_path = Path(results[0][0])
        project = storage.load_note(project_path)

        # Extract links
        links = extract_wiki_links(project.content)
        assert len(links) == 2  # Team Members and Budget 2025

        # Verify link details
        assert links[0].target == "Team Members"
        assert links[1].target == "Budget 2025"

        # Resolve links
        resolver = LinkResolver(config)
        team_note = resolver.resolve_link("Team Members", storage)
        assert team_note is not None
        assert team_note.title == "Team Members"

        budget_note = resolver.resolve_link("Budget 2025", storage)
        assert budget_note is not None
        assert budget_note.title == "Budget 2025"

        index.close()

    def test_backlinks_workflow(self, setup_notes):
        """Test complete backlinks workflow."""
        config, storage, index = setup_notes

        # Load Project Alpha
        results = index.search("Project Alpha")
        project_path = Path(results[0][0])
        project = storage.load_note(project_path)

        # Get backlinks
        backlinks = index.get_backlinks(project.note_id)

        # Should have backlinks from Team Members, Budget, and Meeting Notes
        assert len(backlinks) >= 2

        # Verify backlink sources
        source_titles = [bl["source_title"] for bl in backlinks]
        assert "Team Members" in source_titles
        assert "Budget 2025" in source_titles

        # Check backlink context
        for bl in backlinks:
            assert bl["context"]  # Should have context

        index.close()

    def test_section_links_workflow(self, setup_notes):
        """Test section link workflow."""
        config, storage, index = setup_notes

        # Load budget note which links to Project Alpha#Timeline
        results = index.search("Budget 2025")
        budget_path = Path(results[0][0])
        budget = storage.load_note(budget_path)

        # Extract links
        links = extract_wiki_links(budget.content)

        # Find the section link
        section_link = None
        for link in links:
            if link.section:
                section_link = link
                break

        assert section_link is not None
        assert section_link.target == "Project Alpha"
        assert section_link.section == "Timeline"
        assert section_link.alias == "the project timeline"

        # Verify the section exists in target note
        results = index.search("Project Alpha")
        project_path = Path(results[0][0])
        project = storage.load_note(project_path)

        headings = extract_headings(project.content)
        heading_slugs = [h.slug for h in headings]
        assert "timeline" in heading_slugs

        index.close()

    def test_block_reference_workflow(self, setup_notes):
        """Test block reference workflow."""
        config, storage, index = setup_notes

        # Load meeting notes which reference Project Alpha^decision1
        results = index.search("Meeting Notes")
        meeting_path = Path(results[0][0])
        meeting = storage.load_note(meeting_path)

        # Extract links
        links = extract_wiki_links(meeting.content)

        # Find block reference
        block_link = None
        for link in links:
            if link.block_id:
                block_link = link
                break

        assert block_link is not None
        assert block_link.target == "Project Alpha"
        assert block_link.block_id == "decision1"

        # Verify block exists in target note
        results = index.search("Project Alpha")
        project_path = Path(results[0][0])
        project = storage.load_note(project_path)

        assert "^decision1" in project.content

        index.close()

    def test_broken_links_detection(self, setup_notes):
        """Test broken link detection."""
        config, storage, index = setup_notes

        # Get all broken links
        broken = index.get_broken_links()

        # Should have at least one broken link (Other Project)
        assert len(broken) > 0

        # Check for the broken link to "Other Project"
        broken_targets = [bl["target_title"] for bl in broken]
        assert "Other Project" in broken_targets

        # Verify the source is Budget 2025
        other_project_link = next(bl for bl in broken if bl["target_title"] == "Other Project")
        assert other_project_link["source_title"] == "Budget 2025"

        index.close()

    def test_note_update_reindexes_links(self, setup_notes):
        """Test that updating a note reindexes its links."""
        config, storage, index = setup_notes

        # Load team members note
        results = index.search("Team Members")
        team_path = Path(results[0][0])
        team = storage.load_note(team_path)

        # Add a new link
        team.content += "\n\nSee also [[Budget 2025]] for funding."
        team.update_modified()
        storage.save_plain_note(team)
        index.add_note(team)

        # Check links were updated
        links = index.get_note_links(team.note_id)
        link_targets = [l["target_title"] for l in links]

        # Should now have links to both Project Alpha and Budget 2025
        assert "Project Alpha" in link_targets
        assert "Budget 2025" in link_targets

        index.close()

    def test_note_deletion_removes_links(self, setup_notes):
        """Test that deleting a note removes its links."""
        config, storage, index = setup_notes

        # Load team members note
        results = index.search("Team Members")
        team_path = Path(results[0][0])
        team = storage.load_note(team_path)
        team_id = team.note_id

        # Verify it has links
        links_before = index.get_note_links(team_id)
        assert len(links_before) > 0

        # Delete the note
        index.remove_note(team_path)

        # Verify links are gone
        links_after = index.get_note_links(team_id)
        assert len(links_after) == 0

        index.close()

    def test_full_knowledge_graph(self, setup_notes):
        """Test building a knowledge graph from links."""
        config, storage, index = setup_notes

        # Get all notes
        all_notes = index.get_all_metadata(limit=100)

        # Build adjacency map
        graph = {}
        for note_meta in all_notes:
            note_path = Path(note_meta["file_path"])
            if not note_path.exists():
                continue

            note = storage.load_note(note_path)
            note_id = note.note_id

            # Get outgoing links
            outgoing = index.get_note_links(note_id)
            # Get incoming links (backlinks)
            incoming = index.get_backlinks(note_id)

            graph[note.title] = {
                "id": note_id,
                "outgoing": [l["target_title"] for l in outgoing],
                "incoming": [l["source_title"] for l in incoming],
            }

        # Verify graph structure
        assert "Project Alpha" in graph
        assert "Team Members" in graph["Project Alpha"]["incoming"]
        assert "Budget 2025" in graph["Project Alpha"]["outgoing"]

        # Verify bidirectional linking
        assert "Project Alpha" in graph["Team Members"]["outgoing"]
        assert "Team Members" in graph["Project Alpha"]["incoming"]

        index.close()

    def test_unlinked_mentions(self, setup_notes):
        """Test finding unlinked mentions."""
        config, storage, index = setup_notes

        # Create a note that mentions "Project Alpha" without wiki link
        casual = Note(
            title="Casual Note",
            content="I was thinking about Project Alpha the other day.",
        )
        casual.file_path = config.notes_dir / casual.get_relative_path()
        casual.file_path.parent.mkdir(parents=True, exist_ok=True)
        storage.save_plain_note(casual)
        index.add_note(casual)

        # Load Project Alpha
        results = index.search("Project Alpha")
        project_path = Path(results[0][0])
        project = storage.load_note(project_path)

        # Find unlinked mentions
        manager = BacklinksManager(config)
        mentions = manager.find_unlinked_mentions(project, storage)

        # Should find the casual note
        assert len(mentions) > 0
        mention_titles = [m["title"] for m in mentions]
        assert "Casual Note" in mention_titles

        index.close()
