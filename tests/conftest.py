"""Pytest configuration and fixtures."""

import pytest
import tempfile
from pathlib import Path
from gpgnotes.config import Config


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_config(temp_dir):
    """Create a test configuration."""
    config = Config(config_dir=temp_dir / ".lalanotes")
    config.ensure_dirs()
    return config


@pytest.fixture
def mock_gpg_key():
    """Mock GPG key ID for testing."""
    return "TESTKEY123456789"
