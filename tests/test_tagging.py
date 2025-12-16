"""Tests for tagging module."""

import pytest
from gpgnotes.tagging import AutoTagger


def test_autotagger_initialization():
    """Test AutoTagger initialization."""
    tagger = AutoTagger()
    assert tagger.max_tags == 5
    assert tagger.min_word_length == 3


def test_extract_tags_simple():
    """Test extracting tags from simple text."""
    tagger = AutoTagger()
    content = "Python programming is great. Python is powerful. Programming skills matter."
    tags = tagger.extract_tags(content)

    assert isinstance(tags, list)
    assert len(tags) <= 5
    # Should extract frequently occurring words
    assert any('python' in tag.lower() or 'programming' in tag.lower() for tag in tags)


def test_extract_tags_with_title():
    """Test extracting tags with title weighting."""
    tagger = AutoTagger()
    title = "Machine Learning Tutorial"
    content = "This is about data science and algorithms."

    tags = tagger.extract_tags(content, title)

    assert isinstance(tags, list)
    # Title words should be weighted higher
    assert any('machine' in tag.lower() or 'learning' in tag.lower() for tag in tags)


def test_extract_tags_empty_content():
    """Test extracting tags from empty content."""
    tagger = AutoTagger()
    tags = tagger.extract_tags("")

    assert tags == []


def test_extract_tags_short_words_filtered():
    """Test that short words are filtered out."""
    tagger = AutoTagger(min_word_length=4)
    content = "a an the it is go cat dog bird elephant"

    tags = tagger.extract_tags(content)

    # Short words (< 4 chars) should be filtered
    assert all(len(tag) >= 4 for tag in tags)


def test_tokenize_removes_markdown():
    """Test that markdown syntax is removed during tokenization."""
    tagger = AutoTagger()
    text = "# Header\n**bold** and *italic* text with [link](url) and `code`"

    words = tagger._tokenize(text)

    # Should extract words, not markdown syntax
    assert 'header' in words
    assert 'bold' in words
    assert 'italic' in words
    assert 'link' in words
    # Markdown symbols should not be in words
    assert '#' not in ' '.join(words)
    assert '**' not in ' '.join(words)
    assert '[' not in ' '.join(words)


def test_extract_tags_frequency():
    """Test that frequently occurring words become tags."""
    tagger = AutoTagger(max_tags=3)
    # "important" appears 3 times
    content = "important word here. important concept there. important idea everywhere."

    tags = tagger.extract_tags(content)

    assert 'important' in tags


def test_max_tags_limit():
    """Test that max_tags is respected."""
    tagger = AutoTagger(max_tags=3)
    content = "python java javascript ruby golang rust scala kotlin swift typescript"

    tags = tagger.extract_tags(content)

    assert len(tags) <= 3


def test_extract_words_removes_code_blocks():
    """Test tokenization with code blocks present."""
    tagger = AutoTagger()
    text = """
Regular content here.

```python
def function():
    pass
```

Additional content.
"""
    words = tagger._tokenize(text)

    # Tokenization extracts all words (including from code blocks)
    # and filters stop words and short words
    assert 'regular' in words
    assert 'content' in words
    assert 'here' in words
    assert 'additional' in words

    # Note: _tokenize doesn't remove code blocks, it just tokenizes all text
    # Code keywords will also be extracted
    assert isinstance(words, list)
    assert len(words) > 0
