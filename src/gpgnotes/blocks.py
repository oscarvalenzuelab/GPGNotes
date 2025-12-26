"""Block references and section linking for notes."""

import re
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from .links import slugify


@dataclass
class Heading:
    """Represents a heading in a note."""

    level: int  # 1-6 for H1-H6
    text: str  # Heading text without # markers
    line_num: int  # Line number in note
    slug: str  # URL-safe slug for linking

    def __str__(self) -> str:
        """String representation."""
        return f"{'#' * self.level} {self.text}"


@dataclass
class BlockRef:
    """Represents a block reference."""

    block_id: str  # Unique identifier (e.g., "abc123")
    line_num: int  # Line number in note
    content: str  # Content of the block

    def __str__(self) -> str:
        """String representation."""
        return f"^{self.block_id}"


def extract_headings(content: str) -> List[Heading]:
    """Extract all headings from markdown content.

    Args:
        content: Markdown content

    Returns:
        List of Heading objects
    """
    headings = []
    lines = content.split("\n")

    for i, line in enumerate(lines):
        # Match markdown headings (# Heading)
        match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            slug = slugify(text)

            headings.append(Heading(level=level, text=text, line_num=i, slug=slug))

    return headings


def find_heading(content: str, section: str) -> Optional[int]:
    """Find line number for a heading by slug.

    Args:
        content: Note content
        section: Heading slug to find

    Returns:
        Line number or None if not found
    """
    target_slug = slugify(section)
    headings = extract_headings(content)

    for heading in headings:
        if heading.slug == target_slug:
            return heading.line_num

    return None


def extract_block_refs(content: str) -> List[BlockRef]:
    """Extract all block references from content.

    Block references have format: ^abc123 at end of line

    Args:
        content: Note content

    Returns:
        List of BlockRef objects
    """
    block_refs = []
    lines = content.split("\n")

    for i, line in enumerate(lines):
        # Match block ID at end of line
        match = re.search(r"\^([a-f0-9]+)\s*$", line)
        if match:
            block_id = match.group(1)
            # Get content without the block ID
            content_text = line[: match.start()].strip()

            block_refs.append(
                BlockRef(block_id=block_id, line_num=i, content=content_text)
            )

    return block_refs


def find_block(content: str, block_id: str) -> Optional[int]:
    """Find line number for a block ID.

    Args:
        content: Note content
        block_id: Block ID to find

    Returns:
        Line number or None if not found
    """
    blocks = extract_block_refs(content)

    for block in blocks:
        if block.block_id == block_id:
            return block.line_num

    return None


def generate_block_id() -> str:
    """Generate unique 6-character block ID.

    Returns:
        Hexadecimal block ID (e.g., "a1b2c3")
    """
    return secrets.token_hex(3)


def add_block_id(content: str, line_num: int) -> Tuple[str, str]:
    """Add block ID to specific line.

    Args:
        content: Note content
        line_num: Line number to add block ID to (0-indexed)

    Returns:
        Tuple of (updated_content, block_id)

    Raises:
        ValueError: If line number is invalid
    """
    lines = content.split("\n")

    if line_num < 0 or line_num >= len(lines):
        raise ValueError(f"Invalid line number: {line_num}")

    # Check if line already has a block ID
    existing_match = re.search(r"\^([a-f0-9]+)\s*$", lines[line_num])
    if existing_match:
        # Return existing block ID
        return content, existing_match.group(1)

    # Generate new block ID
    block_id = generate_block_id()

    # Add block ID to end of line
    lines[line_num] = f"{lines[line_num]} ^{block_id}"

    return "\n".join(lines), block_id


def get_block_context(content: str, block_id: str, context_lines: int = 2) -> str:
    """Get block content with surrounding context.

    Args:
        content: Note content
        block_id: Block ID to find
        context_lines: Number of lines to include before/after

    Returns:
        Block content with context
    """
    line_num = find_block(content, block_id)
    if line_num is None:
        return ""

    lines = content.split("\n")
    start = max(0, line_num - context_lines)
    end = min(len(lines), line_num + context_lines + 1)

    context_text = "\n".join(lines[start:end])
    return context_text


def get_section_content(content: str, section: str) -> Optional[str]:
    """Get content of a specific section.

    Extracts all content from the heading to the next same-level heading.

    Args:
        content: Note content
        section: Section slug to find

    Returns:
        Section content or None if not found
    """
    line_num = find_heading(content, section)
    if line_num is None:
        return None

    lines = content.split("\n")
    headings = extract_headings(content)

    # Find the heading object
    target_heading = None
    for h in headings:
        if h.line_num == line_num:
            target_heading = h
            break

    if not target_heading:
        return None

    # Find end of section (next heading of same or higher level)
    end_line = len(lines)
    for h in headings:
        if h.line_num > line_num and h.level <= target_heading.level:
            end_line = h.line_num
            break

    # Extract section content
    section_lines = lines[line_num:end_line]
    return "\n".join(section_lines)


def render_table_of_contents(content: str) -> str:
    """Generate table of contents from headings.

    Args:
        content: Note content

    Returns:
        Formatted TOC
    """
    headings = extract_headings(content)

    if not headings:
        return "No headings found."

    toc_lines = []
    for heading in headings:
        indent = "  " * (heading.level - 1)
        toc_lines.append(f"{indent}{heading.level}. {heading.text}")

    return "\n".join(toc_lines)


def validate_section_link(content: str, section: str) -> bool:
    """Check if a section link is valid.

    Args:
        content: Note content
        section: Section slug

    Returns:
        True if section exists
    """
    return find_heading(content, section) is not None


def validate_block_link(content: str, block_id: str) -> bool:
    """Check if a block reference is valid.

    Args:
        content: Note content
        block_id: Block ID

    Returns:
        True if block exists
    """
    return find_block(content, block_id) is not None
