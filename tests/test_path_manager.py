#!/usr/bin/env python3
"""
Tests for PathManager class
"""

import os
import tempfile
from unittest.mock import patch

from github_inventory.cli import PathManager


class TestPathManager:
    """Test PathManager functionality"""

    def test_init_with_username(self):
        """Test PathManager initialization with username"""
        with patch.object(PathManager, "_get_output_base", return_value="docs"):
            pm = PathManager("testuser")
            assert pm.username == "testuser"
            assert pm.output_base == "docs"

    @patch("os.path.exists")
    def test_get_output_base_development_mode(self, mock_exists):
        """Test output base determination in development mode"""
        mock_exists.side_effect = lambda path: path in [
            "pyproject.toml",
            "src/github_inventory",
        ]

        pm = PathManager("testuser")
        assert pm._get_output_base() == "docs"

    @patch("os.path.exists")
    @patch("os.makedirs")
    @patch("os.path.expanduser")
    def test_get_output_base_global_install(
        self, mock_expanduser, mock_makedirs, mock_exists
    ):
        """Test output base determination in global install mode"""
        mock_exists.return_value = False  # No development files
        mock_expanduser.return_value = "/home/user/.ghscan"

        pm = PathManager("testuser")
        output_base = pm._get_output_base()

        assert output_base == "/home/user/.ghscan"
        # makedirs may be called during both __init__ and _get_output_base
        assert mock_makedirs.call_count >= 1
        mock_makedirs.assert_called_with("/home/user/.ghscan", exist_ok=True)

    def test_get_owned_csv_path_default(self):
        """Test getting owned CSV path with default behavior"""
        with patch.object(PathManager, "_get_output_base", return_value="docs"):
            pm = PathManager("testuser")
            path = pm.get_owned_csv_path()
            assert path == "docs/testuser/repos.csv"

    def test_get_owned_csv_path_custom(self):
        """Test getting owned CSV path with custom path"""
        with patch.object(PathManager, "_get_output_base", return_value="docs"):
            pm = PathManager("testuser")
            path = pm.get_owned_csv_path("custom/path.csv")
            assert path == "custom/path.csv"

    def test_get_owned_csv_path_default_override(self):
        """Test getting owned CSV path when default path should be overridden"""
        with patch.object(PathManager, "_get_output_base", return_value="docs"):
            with patch.dict(os.environ, {"GITHUB_USERNAME": "hsb3"}):
                pm = PathManager("testuser")
                # This should be overridden because it contains default pattern
                path = pm.get_owned_csv_path("docs/hsb3/repos.csv")
                assert path == "docs/testuser/repos.csv"

    def test_get_starred_csv_path_default(self):
        """Test getting starred CSV path with default behavior"""
        with patch.object(PathManager, "_get_output_base", return_value="docs"):
            pm = PathManager("testuser")
            path = pm.get_starred_csv_path()
            assert path == "docs/testuser/starred_repos.csv"

    def test_get_starred_csv_path_custom(self):
        """Test getting starred CSV path with custom path"""
        with patch.object(PathManager, "_get_output_base", return_value="docs"):
            pm = PathManager("testuser")
            path = pm.get_starred_csv_path("custom/starred.csv")
            assert path == "custom/starred.csv"

    def test_get_report_md_path_default(self):
        """Test getting report markdown path with default behavior"""
        with patch.object(PathManager, "_get_output_base", return_value="docs"):
            pm = PathManager("testuser")
            path = pm.get_report_md_path()
            assert path == "docs/testuser/README.md"

    def test_get_report_md_path_custom(self):
        """Test getting report markdown path with custom path"""
        with patch.object(PathManager, "_get_output_base", return_value="docs"):
            pm = PathManager("testuser")
            path = pm.get_report_md_path("custom/report.md")
            assert path == "custom/report.md"

    @patch.dict(os.environ, {"GITHUB_USERNAME": "hsb3"})
    def test_is_default_path_detection(self):
        """Test detection of default path patterns"""
        with patch.object(PathManager, "_get_output_base", return_value="docs"):
            pm = PathManager("testuser")

            # These should be detected as default paths
            assert pm._is_default_path("docs/hsb3/repos.csv") is True
            assert pm._is_default_path("github_inventory_detailed.csv") is True
            assert pm._is_default_path("starred_repos.csv") is True
            assert pm._is_default_path("github_inventory_report.md") is True

            # These should not be detected as default paths
            assert pm._is_default_path("custom/path.csv") is False
            assert pm._is_default_path("my_repos.csv") is False

    @patch("os.makedirs")
    @patch("os.path.dirname")
    def test_ensure_output_directory(self, mock_dirname, mock_makedirs):
        """Test ensuring output directory exists"""
        with patch.object(PathManager, "_get_output_base", return_value="docs"):
            pm = PathManager("testuser")
            mock_dirname.return_value = "test/path"

            pm.ensure_output_directory("test/path/file.csv")

            mock_makedirs.assert_called_once_with("test/path", exist_ok=True)

    @patch("os.makedirs")
    @patch("os.path.dirname")
    def test_ensure_output_directory_current_dir(self, mock_dirname, mock_makedirs):
        """Test ensuring output directory when dirname is empty"""
        with patch.object(PathManager, "_get_output_base", return_value="docs"):
            pm = PathManager("testuser")
            mock_dirname.return_value = ""

            pm.ensure_output_directory("file.csv")

            mock_makedirs.assert_called_once_with(".", exist_ok=True)


class TestPathManagerIntegration:
    """Integration tests for PathManager with real file system operations"""

    def test_path_manager_with_temp_directory(self):
        """Test PathManager with temporary directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("os.path.expanduser", return_value=temp_dir):
                with patch("os.path.exists", return_value=False):  # Force global mode
                    pm = PathManager("testuser")

                    # Test path generation
                    owned_path = pm.get_owned_csv_path()
                    assert owned_path.startswith(temp_dir)
                    assert owned_path.endswith("testuser/repos.csv")

    def test_ensure_output_directory_real_filesystem(self):
        """Test directory creation with real filesystem"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(PathManager, "_get_output_base", return_value=temp_dir):
                pm = PathManager("testuser")

                test_file_path = os.path.join(temp_dir, "subdir", "test.csv")
                pm.ensure_output_directory(test_file_path)

                # Check that the subdirectory was created
                assert os.path.exists(os.path.join(temp_dir, "subdir"))
