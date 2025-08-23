#!/usr/bin/env python3
"""
Tests for CLI module
"""

import os
import tempfile
from unittest.mock import patch

import pytest

from github_inventory.cli import create_parser


class TestCLIParser:
    """Test CLI argument parsing and environment variable loading"""

    def test_default_values_without_env(self):
        """Test default values when no environment variables are set"""
        with patch.dict(os.environ, {}, clear=True):
            # Also patch load_dotenv to ensure no .env file is loaded
            with patch("github_inventory.cli.load_dotenv"):
                parser = create_parser()
                args = parser.parse_args([])

                assert args.user == "hsb3"
                assert args.owned_csv == "docs/hsb3/repos.csv"
                assert args.starred_csv == "docs/hsb3/starred_repos.csv"
                assert args.report_md == "docs/hsb3/README.md"

    def test_environment_variable_loading(self):
        """Test that environment variables are properly loaded"""
        env_vars = {
            "GITHUB_USERNAME": "testuser",
            "OWNED_REPOS_CSV": "test_owned.csv",
            "STARRED_REPOS_CSV": "test_starred.csv",
            "REPORT_OUTPUT_MD": "test_report.md",
        }

        with patch.dict(os.environ, env_vars):
            parser = create_parser()
            args = parser.parse_args([])

            assert args.user == "testuser"
            assert args.owned_csv == "test_owned.csv"
            assert args.starred_csv == "test_starred.csv"
            assert args.report_md == "test_report.md"

    def test_command_line_overrides_env(self):
        """Test that command line arguments override environment variables"""
        env_vars = {"GITHUB_USERNAME": "envuser", "OWNED_REPOS_CSV": "env_owned.csv"}

        with patch.dict(os.environ, env_vars):
            parser = create_parser()
            args = parser.parse_args(
                ["--user", "cliuser", "--owned-csv", "cli_owned.csv"]
            )

            assert args.user == "cliuser"
            assert args.owned_csv == "cli_owned.csv"

    def test_boolean_flags(self):
        """Test boolean flag arguments"""
        parser = create_parser()

        # Test default values
        args = parser.parse_args([])
        assert not args.owned_only
        assert not args.starred_only
        assert not args.report_only
        assert not args.no_report
        assert args.limit is None

        # Test setting flags
        args = parser.parse_args(["--owned-only", "--no-report"])
        assert args.owned_only
        assert not args.starred_only
        assert not args.report_only
        assert args.no_report

    def test_limit_parameter(self):
        """Test limit parameter functionality"""
        parser = create_parser()

        # Test default limit
        args = parser.parse_args([])
        assert args.limit is None

        # Test setting limit
        args = parser.parse_args(["--limit", "50"])
        assert args.limit == 50

        # Test zero limit
        args = parser.parse_args(["--limit", "0"])
        assert args.limit == 0

    def test_batch_parameters(self):
        """Test batch processing parameters"""
        parser = create_parser()

        # Test default values
        args = parser.parse_args([])
        assert args.batch is False
        assert args.config is None

        # Test batch flag (uses default configs)
        args = parser.parse_args(["--batch"])
        assert args.batch is True
        assert args.config is None

        # Test custom config file
        args = parser.parse_args(["--config", "config.json"])
        assert args.batch is False
        assert args.config == "config.json"

    def test_dotenv_file_loading(self):
        """Test loading from .env file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = os.path.join(temp_dir, ".env")
            with open(env_file, "w") as f:
                f.write("GITHUB_USERNAME=fileuser\n")
                f.write("OWNED_REPOS_CSV=file_owned.csv\n")

            # Mock load_dotenv to load our test file
            def mock_load_dotenv():
                os.environ["GITHUB_USERNAME"] = "fileuser"
                os.environ["OWNED_REPOS_CSV"] = "file_owned.csv"

            with patch(
                "github_inventory.cli.load_dotenv", side_effect=mock_load_dotenv
            ):
                with patch.dict(os.environ, {}, clear=False):
                    parser = create_parser()
                    args = parser.parse_args([])

                    assert args.user == "fileuser"
                    assert args.owned_csv == "file_owned.csv"


class TestCLIIntegration:
    """Integration tests for CLI functionality"""

    def test_help_output(self, capsys):
        """Test that help output is generated without errors"""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["--help"])

        captured = capsys.readouterr()
        assert "GitHub Repository Inventory Tool" in captured.out
        assert "--user" in captured.out
        assert "--owned-only" in captured.out

    def test_version_output(self, capsys):
        """Test version output"""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

        captured = capsys.readouterr()
        assert "github_inventory 0.1.0" in captured.out
