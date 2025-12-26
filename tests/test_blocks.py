"""Tests for block references and sections functionality."""

import pytest

from gpgnotes.blocks import (
    Heading,
    BlockRef,
    extract_headings,
    find_heading,
    extract_block_refs,
    find_block,
    generate_block_id,
    add_block_id,
    get_block_context,
    get_section_content,
    render_table_of_contents,
    validate_section_link,
    validate_block_link,
)


class TestHeading:
    """Test Heading dataclass."""

    def test_heading_creation(self):
        """Test creating a Heading."""
        heading = Heading(level=1, text="My Heading", line_num=5, slug="my-heading")
        assert heading.level == 1
        assert heading.text == "My Heading"
        assert str(heading) == "# My Heading"

    def test_heading_levels(self):
        """Test different heading levels."""
        for level in range(1, 7):
            heading = Heading(level=level, text="Test", line_num=0, slug="test")
            assert str(heading) == f"{'#' * level} Test"


class TestExtractHeadings:
    """Test heading extraction."""

    def test_extract_single_heading(self):
        """Test extracting single heading."""
        content = "# Main Title\n\nSome content."
        headings = extract_headings(content)

        assert len(headings) == 1
        assert headings[0].level == 1
        assert headings[0].text == "Main Title"
        assert headings[0].slug == "main-title"

    def test_extract_multiple_headings(self):
        """Test extracting multiple headings."""
        content = """
# Title
## Section 1
### Subsection 1.1
## Section 2
        """
        headings = extract_headings(content)

        assert len(headings) == 4
        assert headings[0].level == 1
        assert headings[1].level == 2
        assert headings[2].level == 3
        assert headings[3].level == 2

    def test_extract_heading_with_special_chars(self):
        """Test extracting heading with special characters."""
        content = "## API Design (v2.0) - Final"
        headings = extract_headings(content)

        assert len(headings) == 1
        assert headings[0].text == "API Design (v2.0) - Final"
        assert headings[0].slug == "api-design-v20-final"

    def test_extract_no_headings(self):
        """Test content with no headings."""
        content = "Just plain text\nwith no headings."
        headings = extract_headings(content)

        assert len(headings) == 0

    def test_extract_heading_line_numbers(self):
        """Test heading line numbers are correct."""
        content = "Line 0\n# Heading 1\nLine 2\n## Heading 2\nLine 4"
        headings = extract_headings(content)

        assert headings[0].line_num == 1
        assert headings[1].line_num == 3


class TestFindHeading:
    """Test finding headings by slug."""

    def test_find_existing_heading(self):
        """Test finding an existing heading."""
        content = "# Title\n## Section\nContent"
        line_num = find_heading(content, "Section")

        assert line_num == 1

    def test_find_heading_case_insensitive(self):
        """Test finding heading is case-insensitive."""
        content = "# Title\n## My Section\nContent"
        line_num = find_heading(content, "my-section")

        assert line_num == 1

    def test_find_nonexistent_heading(self):
        """Test finding nonexistent heading."""
        content = "# Title\nContent"
        line_num = find_heading(content, "Nonexistent")

        assert line_num is None


class TestBlockRef:
    """Test BlockRef dataclass."""

    def test_block_ref_creation(self):
        """Test creating a BlockRef."""
        block = BlockRef(block_id="abc123", line_num=10, content="Some text")
        assert block.block_id == "abc123"
        assert block.line_num == 10
        assert str(block) == "^abc123"


class TestExtractBlockRefs:
    """Test block reference extraction."""

    def test_extract_single_block_ref(self):
        """Test extracting single block reference."""
        content = "This is important text. ^abc123"
        blocks = extract_block_refs(content)

        assert len(blocks) == 1
        assert blocks[0].block_id == "abc123"
        assert blocks[0].content == "This is important text."

    def test_extract_multiple_block_refs(self):
        """Test extracting multiple block references."""
        content = """
First block. ^abc123
Second block. ^def456
Third block. ^789xyz
        """
        blocks = extract_block_refs(content)

        assert len(blocks) == 3
        assert [b.block_id for b in blocks] == ["abc123", "def456", "789xyz"]

    def test_extract_no_block_refs(self):
        """Test content with no block references."""
        content = "Regular text without any block references."
        blocks = extract_block_refs(content)

        assert len(blocks) == 0

    def test_extract_block_ref_line_numbers(self):
        """Test block reference line numbers."""
        content = "Line 0\nBlock 1 ^aaa\nLine 2\nBlock 2 ^bbb"
        blocks = extract_block_refs(content)

        assert blocks[0].line_num == 1
        assert blocks[1].line_num == 3


class TestFindBlock:
    """Test finding blocks by ID."""

    def test_find_existing_block(self):
        """Test finding an existing block."""
        content = "Text line 1\nImportant block ^abc123\nText line 3"
        line_num = find_block(content, "abc123")

        assert line_num == 1

    def test_find_nonexistent_block(self):
        """Test finding nonexistent block."""
        content = "Text with no matching block ^aaa"
        line_num = find_block(content, "xyz999")

        assert line_num is None


class TestGenerateBlockId:
    """Test block ID generation."""

    def test_generate_block_id_format(self):
        """Test generated block ID format."""
        block_id = generate_block_id()

        assert len(block_id) == 6
        assert all(c in "0123456789abcdef" for c in block_id)

    def test_generate_unique_ids(self):
        """Test that generated IDs are unique."""
        ids = [generate_block_id() for _ in range(100)]

        # All should be unique
        assert len(set(ids)) == 100


class TestAddBlockId:
    """Test adding block IDs to lines."""

    def test_add_block_id_to_line(self):
        """Test adding block ID to a line."""
        content = "Line 1\nImportant line\nLine 3"
        new_content, block_id = add_block_id(content, 1)

        assert f"Important line ^{block_id}" in new_content
        assert len(block_id) == 6

    def test_add_block_id_invalid_line(self):
        """Test adding block ID to invalid line."""
        content = "Line 1\nLine 2"

        with pytest.raises(ValueError):
            add_block_id(content, 10)

    def test_add_block_id_existing(self):
        """Test adding block ID to line that already has one."""
        content = "Line 1\nExisting line ^abc123\nLine 3"
        new_content, block_id = add_block_id(content, 1)

        # Should return existing ID
        assert block_id == "abc123"
        # Content should not change
        assert new_content == content


class TestGetBlockContext:
    """Test getting block context."""

    def test_get_block_context(self):
        """Test getting context around a block."""
        content = """Line 1
Line 2
Important block ^abc123
Line 4
Line 5"""
        context = get_block_context(content, "abc123", context_lines=1)

        assert "Line 2" in context
        assert "Important block" in context
        assert "Line 4" in context
        assert "Line 1" not in context
        assert "Line 5" not in context

    def test_get_block_context_nonexistent(self):
        """Test getting context for nonexistent block."""
        content = "Some text"
        context = get_block_context(content, "xyz999")

        assert context == ""


class TestGetSectionContent:
    """Test getting section content."""

    def test_get_section_content(self):
        """Test getting content of a section."""
        content = """# Main Title
## Section 1
Content of section 1.
More content.
## Section 2
Content of section 2."""

        section = get_section_content(content, "section-1")

        assert section is not None
        assert "## Section 1" in section
        assert "Content of section 1" in section
        assert "## Section 2" not in section

    def test_get_section_content_last_section(self):
        """Test getting content of last section."""
        content = """# Title
## Last Section
This is the end."""

        section = get_section_content(content, "last-section")

        assert section is not None
        assert "This is the end." in section

    def test_get_section_content_nonexistent(self):
        """Test getting nonexistent section."""
        content = "# Title\nContent"
        section = get_section_content(content, "nonexistent")

        assert section is None


class TestRenderTableOfContents:
    """Test table of contents rendering."""

    def test_render_toc(self):
        """Test rendering table of contents."""
        content = """# Main Title
## Section 1
### Subsection 1.1
## Section 2"""

        toc = render_table_of_contents(content)

        assert "1. Main Title" in toc
        assert "2. Section 1" in toc
        assert "3. Subsection 1.1" in toc
        assert "2. Section 2" in toc

    def test_render_toc_no_headings(self):
        """Test rendering TOC with no headings."""
        content = "Plain text with no headings."
        toc = render_table_of_contents(content)

        assert "No headings found" in toc


class TestValidateLinks:
    """Test link validation."""

    def test_validate_section_link_valid(self):
        """Test validating valid section link."""
        content = "# Title\n## My Section\nContent"
        assert validate_section_link(content, "my-section") is True

    def test_validate_section_link_invalid(self):
        """Test validating invalid section link."""
        content = "# Title\nContent"
        assert validate_section_link(content, "nonexistent") is False

    def test_validate_block_link_valid(self):
        """Test validating valid block link."""
        content = "Text line ^abc123"
        assert validate_block_link(content, "abc123") is True

    def test_validate_block_link_invalid(self):
        """Test validating invalid block link."""
        content = "Text with no blocks"
        assert validate_block_link(content, "xyz999") is False
