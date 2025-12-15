"""Text helper for spell checking and text enhancement."""

import re
from typing import List, Tuple, Optional
from pathlib import Path


class TextHelper:
    """Provides spell checking and text enhancement features."""

    def __init__(self):
        """Initialize text helper with spell checker."""
        self._spell = None

    def _get_spell_checker(self):
        """Lazy load spell checker."""
        if self._spell is None:
            try:
                from spellchecker import SpellChecker
                self._spell = SpellChecker()
            except ImportError:
                # Spell checker not available
                self._spell = False
        return self._spell if self._spell is not False else None

    def check_spelling(self, text: str) -> List[Tuple[str, List[str]]]:
        """
        Check spelling in text.

        Args:
            text: The text to check

        Returns:
            List of (misspelled_word, suggestions) tuples
        """
        spell = self._get_spell_checker()
        if not spell:
            return []

        # Extract words (excluding markdown syntax, code blocks, links)
        words = self._extract_words(text)

        # Find misspelled words
        misspelled = spell.unknown(words)

        # Get corrections
        results = []
        for word in misspelled:
            candidates = spell.candidates(word)
            if candidates:
                suggestions = list(candidates)[:5]  # Top 5 suggestions
                results.append((word, suggestions))

        return results

    def _extract_words(self, text: str) -> List[str]:
        """Extract words from text, excluding markdown syntax."""
        # Remove code blocks
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`[^`]+`', '', text)

        # Remove links
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

        # Remove markdown headers, bold, italic
        text = re.sub(r'#+\s*', '', text)
        text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^\*]+)\*', r'\1', text)

        # Remove YAML frontmatter
        text = re.sub(r'^---[\s\S]*?---', '', text)

        # Extract words (letters only, minimum 2 characters)
        words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())

        return words

    def check_file(self, file_path: Path) -> List[Tuple[str, List[str]]]:
        """
        Check spelling in a file.

        Args:
            file_path: Path to the file

        Returns:
            List of (misspelled_word, suggestions) tuples
        """
        with open(file_path, 'r') as f:
            text = f.read()

        return self.check_spelling(text)

    def is_available(self) -> bool:
        """Check if spell checker is available."""
        return self._get_spell_checker() is not None


class WordCompleter:
    """Provides word completion based on existing notes."""

    def __init__(self):
        """Initialize word completer."""
        self.words = set()

    def add_text(self, text: str):
        """Add words from text to completion dictionary."""
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        self.words.update(words)

    def add_note(self, note):
        """Add words from note to completion dictionary."""
        self.add_text(note.title)
        self.add_text(note.content)
        for tag in note.tags:
            self.add_text(tag)

    def complete(self, prefix: str, limit: int = 10) -> List[str]:
        """
        Get word completions for prefix.

        Args:
            prefix: The prefix to complete
            limit: Maximum number of suggestions

        Returns:
            List of word suggestions
        """
        if len(prefix) < 2:
            return []

        prefix = prefix.lower()
        matches = [w for w in self.words if w.startswith(prefix)]

        # Sort by length (shorter first) and alphabetically
        matches.sort(key=lambda x: (len(x), x))

        return matches[:limit]

    def build_from_notes(self, storage):
        """Build completion dictionary from all notes."""
        for file_path in storage.list_notes():
            try:
                note = storage.load_note(file_path)
                self.add_note(note)
            except Exception:
                continue
