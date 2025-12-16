"""Tests for configuration module."""

import pytest
from pathlib import Path
from gpgnotes.config import Config


def test_config_initialization(test_config):
    """Test configuration initialization."""
    assert test_config.config_dir.exists()
    assert test_config.notes_dir.exists()


def test_config_default_values(test_config):
    """Test default configuration values."""
    assert test_config.get('editor') in ['nano', 'vim', 'vi']
    assert test_config.get('auto_sync') is True
    assert test_config.get('auto_tag') is True
    assert test_config.get('git_remote') == ""
    assert test_config.get('gpg_key') == ""


def test_config_set_and_get(test_config):
    """Test setting and getting configuration values."""
    test_config.set('editor', 'vim')
    assert test_config.get('editor') == 'vim'

    test_config.set('gpg_key', 'TEST123')
    assert test_config.get('gpg_key') == 'TEST123'


def test_config_save_and_load(temp_dir):
    """Test saving and loading configuration."""
    config = Config(config_dir=temp_dir / ".lalanotes")
    config.set('editor', 'emacs')
    config.set('gpg_key', 'TESTKEY')

    # Load new instance from same directory
    config2 = Config(config_dir=temp_dir / ".lalanotes")
    assert config2.get('editor') == 'emacs'
    assert config2.get('gpg_key') == 'TESTKEY'


def test_config_is_configured(test_config):
    """Test is_configured method."""
    assert not test_config.is_configured()

    test_config.set('gpg_key', 'TESTKEY')
    assert test_config.is_configured()


def test_config_is_first_run(temp_dir):
    """Test is_first_run method."""
    config = Config(config_dir=temp_dir / ".lalanotes")
    assert config.is_first_run()

    config.save()
    assert not config.is_first_run()


def test_config_ensure_dirs(temp_dir):
    """Test directory creation."""
    config_dir = temp_dir / ".lalanotes"
    config = Config(config_dir=config_dir)
    config.ensure_dirs()

    assert config_dir.exists()
    assert (config_dir / "notes").exists()
