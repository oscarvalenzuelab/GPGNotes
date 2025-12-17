# AI-Powered Note Enhancement

GPGNotes includes optional AI-powered note enhancement to improve your writing. This feature supports multiple LLM providers and uses a human-in-the-loop workflow for iterative refinement.

## Installation

**If installed with pip:**

```bash
pip install gpgnotes[llm]
```

**If installed with pipx:**

You need to inject the LLM dependencies into the GPGNotes virtual environment:

```bash
pipx inject gpgnotes openai anthropic ollama
```

Or inject only what you need:

```bash
pipx inject gpgnotes openai    # For OpenAI only
pipx inject gpgnotes ollama    # For Ollama only
```

## Supported Providers

- **OpenAI** (GPT-4, GPT-4o, GPT-4o-mini) - Cloud-based, requires API key
- **Ollama** (llama3.1, etc.) - Local LLM, no API key needed

## Setup

### OpenAI

```bash
notes config --llm-provider openai
notes config --llm-key sk-your-api-key-here
notes config --llm-model gpt-4o-mini  # Optional, defaults to gpt-4o-mini
```

API keys are encrypted with your GPG key and stored securely.

### Ollama (Local)

First, [install Ollama](https://ollama.ai/) and pull a model:

```bash
ollama pull llama3.1
```

Then configure GPGNotes:

```bash
notes config --llm-provider ollama
notes config --llm-model llama3.1  # Optional, defaults to llama3.1
```

## Usage

### Interactive Mode (Recommended)

```bash
notes enhance <note-id>
```

This opens an interactive workflow where you can:
- Choose from enhancement presets (grammar, clarity, conciseness, tone, structure)
- Provide custom instructions
- Iterate with new instructions to refine the output
- View diffs between original and enhanced versions
- Navigate version history (back/forward)
- Accept or reject changes

### Quick Mode (Auto-apply)

```bash
notes enhance <note-id> --instructions "Fix grammar and spelling" --quick
```

## Enhancement Presets

1. **Fix grammar and spelling** - Correct errors while maintaining tone
2. **Improve clarity** - Make text easier to understand
3. **Make more concise** - Remove redundancy
4. **Make more professional** - Formal, structured tone
5. **Make more casual** - Conversational tone
6. **Add structure** - Organize with bullet points and headings

## Security Note

- OpenAI API keys are encrypted with GPG before storage
- Ollama runs entirely locally (no data sent to external services)
- Note content is sent to the LLM provider for enhancement (except Ollama)
