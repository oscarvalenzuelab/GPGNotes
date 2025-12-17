# Contributing to GPGNotes

Thank you for your interest in contributing to GPGNotes! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and considerate in all interactions. We aim to maintain a welcoming environment for all contributors.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- GPG (GnuPG) installed on your system
- Git

### Development Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/GPGNotes.git
   cd GPGNotes
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. (Optional) Install LLM dependencies for AI features:
   ```bash
   pip install -e ".[llm]"
   ```

## Development Workflow

### Code Style

This project uses [ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Check for linting issues
ruff check src/

# Auto-fix linting issues
ruff check --fix src/

# Check formatting
ruff format --check src/

# Apply formatting
ruff format src/
```

Configuration is in `pyproject.toml`. Key settings:
- Line length: 100 characters
- Python target: 3.8+

### Type Checking

We use [mypy](https://mypy-lang.org/) for type checking:

```bash
mypy src/gpgnotes --ignore-missing-imports
```

Type hints are encouraged but not strictly required for all code.

### Running Tests

Tests are written using [pytest](https://pytest.org/):

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_note.py

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_note.py::test_function_name
```

All tests must pass before submitting a pull request.

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-export-pdf` - New features
- `fix/encryption-error` - Bug fixes
- `docs/update-readme` - Documentation changes
- `refactor/simplify-storage` - Code refactoring

### Commit Messages

Write clear, concise commit messages:
- Use present tense ("Add feature" not "Added feature")
- First line should be 50 characters or less
- Reference issue numbers when applicable (`Fix #123`)

Example:
```
Add PDF export functionality

- Implement PDF conversion using reportlab
- Add --format pdf option to export command
- Update documentation

Closes #42
```

### Pull Request Process

1. Create a new branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit them

3. Ensure all tests pass and code is properly formatted:
   ```bash
   ruff check src/
   ruff format src/
   pytest
   ```

4. Push your branch and create a pull request:
   ```bash
   git push origin feature/your-feature-name
   ```

5. Fill out the pull request template with:
   - Description of changes
   - Related issue numbers
   - Testing performed

6. Wait for review and address any feedback

## What to Contribute

### Good First Issues

Look for issues labeled `good first issue` - these are suitable for newcomers.

### Feature Requests

Before implementing new features:
1. Check existing issues to avoid duplicates
2. Open an issue to discuss the feature
3. Wait for feedback before starting implementation

### Bug Reports

When reporting bugs, include:
- Python version
- Operating system
- GPG version
- Steps to reproduce
- Expected vs actual behavior
- Error messages/tracebacks

## Project Structure

```
GPGNotes/
├── src/gpgnotes/        # Main package
│   ├── cli.py           # Command-line interface
│   ├── config.py        # Configuration management
│   ├── encryption.py    # GPG encryption/decryption
│   ├── index.py         # SQLite search index
│   ├── llm.py           # LLM integration
│   ├── note.py          # Note model
│   ├── storage.py       # File storage
│   ├── sync.py          # Git synchronization
│   └── tagging.py       # Auto-tagging with TF-IDF
├── tests/               # Test suite
├── .github/workflows/   # CI/CD pipelines
└── pyproject.toml       # Project configuration
```

## Security

- Never commit API keys or secrets
- Be careful with GPG key handling in tests
- Report security vulnerabilities privately (see [SECURITY.md](SECURITY.md))

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

## Questions?

Feel free to open an issue for any questions about contributing.
