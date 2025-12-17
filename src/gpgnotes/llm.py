"""LLM provider abstraction for note enhancement."""

import importlib.util
from abc import ABC, abstractmethod
from typing import Optional


def sanitize_for_gpg(text: str) -> str:
    """
    Sanitize text to remove characters that can't be encoded in latin-1.

    GPG encryption uses latin-1 encoding, so we need to convert or remove
    Unicode characters (smart quotes, em dashes, etc.).

    Args:
        text: The text to sanitize

    Returns:
        Sanitized text safe for latin-1 encoding
    """
    # Common Unicode replacements (smart quotes, dashes, etc.)
    replacements = {
        "\u2018": "'",  # Left single quotation mark
        "\u2019": "'",  # Right single quotation mark
        "\u201c": '"',  # Left double quotation mark
        "\u201d": '"',  # Right double quotation mark
        "\u2013": "-",  # En dash
        "\u2014": "--",  # Em dash
        "\u2026": "...",  # Horizontal ellipsis
        "\u00a0": " ",  # Non-breaking space
        "\u2022": "*",  # Bullet
        "\u2023": ">",  # Triangular bullet
        "\u2043": "-",  # Hyphen bullet
        "\u00b7": "*",  # Middle dot
        "\u2212": "-",  # Minus sign
        "\u00ad": "",  # Soft hyphen (invisible)
        "\ufeff": "",  # BOM / zero-width no-break space
        "\u200b": "",  # Zero-width space
        "\u200c": "",  # Zero-width non-joiner
        "\u200d": "",  # Zero-width joiner
    }

    for unicode_char, replacement in replacements.items():
        text = text.replace(unicode_char, replacement)

    # Remove any remaining characters that can't be encoded in latin-1
    try:
        text.encode("latin-1")
    except UnicodeEncodeError:
        # Filter out non-encodable characters
        text = "".join(c if ord(c) < 256 else "?" for c in text)

    return text


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def enhance(self, content: str, instructions: str) -> str:
        """
        Enhance content using LLM.

        Args:
            content: The text to enhance
            instructions: Instructions for enhancement (e.g., "fix grammar", "make more concise")

        Returns:
            Enhanced text
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available and configured."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """Initialize OpenAI provider."""
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        """Lazy-load OpenAI client."""
        if self._client is None:
            try:
                import openai

                self._client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("OpenAI library not installed. Install with: pip install openai")
        return self._client

    def enhance(self, content: str, instructions: str) -> str:
        """Enhance content using OpenAI."""
        client = self._get_client()

        system_prompt = """You are a helpful writing assistant. Your task is to enhance the user's text according to their instructions while preserving the core meaning and structure. Be concise and direct in your improvements."""

        user_prompt = f"""Please enhance the following text according to these instructions: {instructions}

Original text:
{content}

Provide ONLY the enhanced text without explanations or meta-commentary."""

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,  # Lower temperature for more consistent enhancements
            )

            result = response.choices[0].message.content.strip()
            return sanitize_for_gpg(result)
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}")

    def is_available(self) -> bool:
        """Check if OpenAI is available."""
        return importlib.util.find_spec("openai") is not None and bool(self.api_key)


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        """Initialize Claude provider."""
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        """Lazy-load Anthropic client."""
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise RuntimeError(
                    "Anthropic library not installed. Install with: pip install anthropic"
                )
        return self._client

    def enhance(self, content: str, instructions: str) -> str:
        """Enhance content using Claude."""
        client = self._get_client()

        system_prompt = """You are a helpful writing assistant. Your task is to enhance the user's text according to their instructions while preserving the core meaning and structure. Be concise and direct in your improvements."""

        user_prompt = f"""Please enhance the following text according to these instructions: {instructions}

Original text:
{content}

Provide ONLY the enhanced text without explanations or meta-commentary."""

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            result = response.content[0].text.strip()
            return sanitize_for_gpg(result)
        except Exception as e:
            raise RuntimeError(f"Claude API error: {e}")

    def is_available(self) -> bool:
        """Check if Claude is available."""
        return importlib.util.find_spec("anthropic") is not None and bool(self.api_key)


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""

    def __init__(self, model: str = "llama3.1", base_url: str = "http://localhost:11434"):
        """Initialize Ollama provider."""
        self.model = model
        self.base_url = base_url
        self._client = None

    def _get_client(self):
        """Lazy-load Ollama client."""
        if self._client is None:
            try:
                import ollama

                self._client = ollama.Client(host=self.base_url)
            except ImportError:
                raise RuntimeError("Ollama library not installed. Install with: pip install ollama")
        return self._client

    def enhance(self, content: str, instructions: str) -> str:
        """Enhance content using Ollama."""
        client = self._get_client()

        system_prompt = """You are a helpful writing assistant. Your task is to enhance the user's text according to their instructions while preserving the core meaning and structure. Be concise and direct in your improvements."""

        user_prompt = f"""Please enhance the following text according to these instructions: {instructions}

Original text:
{content}

Provide ONLY the enhanced text without explanations or meta-commentary."""

        try:
            response = client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                options={"temperature": 0.3},
            )

            result = response["message"]["content"].strip()
            return sanitize_for_gpg(result)
        except Exception as e:
            raise RuntimeError(f"Ollama API error: {e}")

    def is_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            import ollama

            client = ollama.Client(host=self.base_url)
            # Try to list models to check if Ollama is running
            client.list()
            return True
        except Exception:
            return False


def get_provider(
    provider_name: str, api_key: Optional[str] = None, model: Optional[str] = None
) -> LLMProvider:
    """
    Factory function to get LLM provider instance.

    Args:
        provider_name: Name of provider ('openai', 'claude', 'ollama')
        api_key: API key for the provider (not needed for Ollama)
        model: Model name to use (optional, uses provider defaults)

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider is unknown or not properly configured
    """
    provider_name = provider_name.lower()

    if provider_name == "openai":
        if not api_key:
            raise ValueError("OpenAI requires an API key")
        return OpenAIProvider(api_key=api_key, model=model or "gpt-4o-mini")

    elif provider_name == "claude":
        if not api_key:
            raise ValueError("Claude requires an API key")
        return ClaudeProvider(api_key=api_key, model=model or "claude-3-5-sonnet-20241022")

    elif provider_name == "ollama":
        return OllamaProvider(model=model or "llama3.1")

    else:
        raise ValueError(f"Unknown provider: {provider_name}. Supported: openai, claude, ollama")
