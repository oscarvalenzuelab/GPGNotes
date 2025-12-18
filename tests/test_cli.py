"""Tests for CLI module."""

import pytest
from click.testing import CliRunner
from gpgnotes.cli import main


def test_cli_help():
    """Test CLI help command."""
    runner = CliRunner()
    result = runner.invoke(main, ['--help'])

    assert result.exit_code == 0
    assert 'GPGNotes' in result.output
    assert 'Encrypted note-taking' in result.output


def test_cli_version():
    """Test CLI version command."""
    runner = CliRunner()
    result = runner.invoke(main, ['--version'])

    assert result.exit_code == 0
    assert '0.3.1' in result.output


def test_config_show(test_config, monkeypatch):
    """Test config show command."""
    # Mock Config to use test config
    import gpgnotes.cli
    monkeypatch.setattr(gpgnotes.cli, 'Config', lambda: test_config)

    runner = CliRunner()
    result = runner.invoke(main, ['config', '--show'])

    assert result.exit_code == 0
    assert 'Configuration' in result.output


def test_reindex_command():
    """Test reindex command."""
    runner = CliRunner()
    # Will fail without proper config, but should not crash
    result = runner.invoke(main, ['reindex'])

    # Either succeeds or exits with proper error
    assert result.exit_code in [0, 1]


def test_list_command():
    """Test list command."""
    runner = CliRunner()
    result = runner.invoke(main, ['list'])

    # Should run without crashing
    assert result.exit_code in [0, 1]


def test_tags_command():
    """Test tags command."""
    runner = CliRunner()
    result = runner.invoke(main, ['tags'])

    # Should run without crashing
    assert result.exit_code in [0, 1]
