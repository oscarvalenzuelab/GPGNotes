"""Automatic tag generation for notes."""

import re
from collections import Counter
from typing import List, Set

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


class AutoTagger:
    """Generates tags automatically from note content."""

    # Common English stop words
    STOP_WORDS = {
        "the",
        "be",
        "to",
        "of",
        "and",
        "a",
        "in",
        "that",
        "have",
        "i",
        "it",
        "for",
        "not",
        "on",
        "with",
        "he",
        "as",
        "you",
        "do",
        "at",
        "this",
        "but",
        "his",
        "by",
        "from",
        "they",
        "we",
        "say",
        "her",
        "she",
        "or",
        "an",
        "will",
        "my",
        "one",
        "all",
        "would",
        "there",
        "their",
        "what",
        "so",
        "up",
        "out",
        "if",
        "about",
        "who",
        "get",
        "which",
        "go",
        "me",
        "when",
        "make",
        "can",
        "like",
        "time",
        "no",
        "just",
        "him",
        "know",
        "take",
        "people",
        "into",
        "year",
        "your",
        "good",
        "some",
        "could",
        "them",
        "see",
        "other",
        "than",
        "then",
        "now",
        "look",
        "only",
        "come",
        "its",
        "over",
        "think",
        "also",
        "back",
        "after",
        "use",
        "two",
        "how",
        "our",
        "work",
        "first",
        "well",
        "way",
        "even",
        "new",
        "want",
        "because",
        "any",
        "these",
        "give",
        "day",
        "most",
        "us",
        "is",
        "was",
        "are",
        "been",
        "has",
        "had",
        "were",
        "said",
        "did",
    }

    def __init__(self, max_tags: int = 5, min_word_length: int = 3):
        """Initialize auto-tagger."""
        self.max_tags = max_tags
        self.min_word_length = min_word_length

    def extract_tags(self, content: str, title: str = "") -> List[str]:
        """
        Extract tags from content using TF-IDF.

        Args:
            content: The note content
            title: The note title (given higher weight)

        Returns:
            List of extracted tags
        """
        # Combine title and content, giving title more weight
        weighted_text = f"{title} {title} {title} {content}"

        # Clean and tokenize
        words = self._tokenize(weighted_text)

        if not words:
            return []

        # Use simple frequency-based extraction
        tags = self._extract_by_frequency(words)

        return tags[: self.max_tags]

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize and clean text."""
        # Convert to lowercase
        text = text.lower()

        # Remove special characters and keep only words
        words = re.findall(r"\b[a-z]+\b", text)

        # Filter out stop words and short words
        words = [w for w in words if w not in self.STOP_WORDS and len(w) >= self.min_word_length]

        return words

    def _extract_by_frequency(self, words: List[str]) -> List[str]:
        """Extract tags based on word frequency."""
        # Count word frequencies
        counter = Counter(words)

        # Get most common words
        most_common = counter.most_common(self.max_tags * 2)

        # Filter out words that appear only once
        tags = [word for word, count in most_common if count > 1]

        # If we don't have enough tags, add some single-occurrence words
        if len(tags) < self.max_tags:
            single_words = [word for word, count in most_common if count == 1]
            tags.extend(single_words[: self.max_tags - len(tags)])

        return tags

    def extract_tags_tfidf(self, content: str, title: str, corpus: List[str]) -> List[str]:
        """
        Extract tags using TF-IDF across a corpus of documents.

        This method is more accurate but requires multiple documents.

        Args:
            content: The note content
            title: The note title
            corpus: List of other document contents for comparison

        Returns:
            List of extracted tags
        """
        if not corpus:
            return self.extract_tags(content, title)

        # Combine current document with corpus
        weighted_text = f"{title} {title} {title} {content}"
        documents = [weighted_text] + corpus

        # Create TF-IDF vectorizer
        vectorizer = TfidfVectorizer(
            max_features=100,
            stop_words=list(self.STOP_WORDS),
            min_df=1,
            ngram_range=(1, 2),  # Include bigrams
        )

        try:
            # Fit and transform
            tfidf_matrix = vectorizer.fit_transform(documents)

            # Get feature names
            feature_names = vectorizer.get_feature_names_out()

            # Get scores for first document (our target)
            scores = tfidf_matrix[0].toarray()[0]

            # Get top scoring terms
            top_indices = np.argsort(scores)[::-1][: self.max_tags]
            tags = [feature_names[i].replace(" ", "-") for i in top_indices if scores[i] > 0]

            return tags

        except Exception:
            # Fall back to simple extraction if TF-IDF fails
            return self.extract_tags(content, title)

    def suggest_tags(self, partial: str, existing_tags: Set[str]) -> List[str]:
        """
        Suggest tags based on partial input.

        Args:
            partial: Partial tag string
            existing_tags: Set of existing tags from other notes

        Returns:
            List of suggested tags
        """
        if not partial:
            return sorted(existing_tags)[:10]

        partial = partial.lower()

        # Find matching tags
        matches = [tag for tag in existing_tags if tag.startswith(partial)]

        return sorted(matches)[:10]
