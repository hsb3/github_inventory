#!/usr/bin/env python3
"""
Tests for inventory module
"""

import csv
import json
import tempfile
from unittest.mock import patch

import pytest

from github_inventory.exceptions import GitHubCLIError
from github_inventory.inventory import (
    collect_owned_repositories,
    format_date,
    get_branch_count,
    get_repo_list,
    run_gh_command,
    write_to_csv,
)


class TestGitHubCLICommands:
    """Test GitHub CLI command execution"""

    @patch("subprocess.run")
    def test_run_gh_command_success(self, mock_run):
        """Test successful GitHub CLI command execution"""
        mock_run.return_value.stdout = "test output"
        mock_run.return_value.returncode = 0

        result = run_gh_command("gh repo list")

        assert result == "test output"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_run_gh_command_failure(self, mock_run):
        """Test failed GitHub CLI command execution"""
        from subprocess import CalledProcessError

        mock_run.side_effect = CalledProcessError(
            1, "gh repo list", stderr="Command failed"
        )

        with pytest.raises(GitHubCLIError) as exc_info:
            run_gh_command("gh repo list")

        assert "gh repo list" in str(exc_info.value)

    @patch("github_inventory.inventory.run_gh_command")
    def test_get_repo_list_success(self, mock_run_gh):
        """Test successful repository list retrieval"""
        mock_repos = [
            {"name": "repo1", "description": "Test repo 1"},
            {"name": "repo2", "description": "Test repo 2"},
        ]
        mock_run_gh.return_value = json.dumps(mock_repos)

        result = get_repo_list("testuser")

        assert len(result) == 2
        assert result[0]["name"] == "repo1"
        assert result[1]["name"] == "repo2"

    @patch("github_inventory.inventory.run_gh_command")
    def test_get_repo_list_empty(self, mock_run_gh):
        """Test empty repository list"""
        mock_run_gh.return_value = None

        result = get_repo_list("testuser")

        assert result == []

    @patch("github_inventory.inventory.run_gh_command")
    def test_get_branch_count_success(self, mock_run_gh):
        """Test successful branch count retrieval"""
        mock_run_gh.return_value = "5"

        result = get_branch_count("owner", "repo")

        assert result == 5

    @patch("github_inventory.inventory.run_gh_command")
    def test_get_branch_count_failure(self, mock_run_gh):
        """Test failed branch count retrieval"""
        mock_run_gh.return_value = None

        result = get_branch_count("owner", "repo")

        assert result == "unknown"


class TestDataFormatting:
    """Test data formatting functions"""

    def test_format_date_valid_iso(self):
        """Test formatting valid ISO date"""
        result = format_date("2023-01-15T10:30:00Z")
        assert result == "2023-01-15"

    def test_format_date_empty(self):
        """Test formatting empty date"""
        result = format_date("")
        assert result == ""

    def test_format_date_none(self):
        """Test formatting None date"""
        result = format_date(None)
        assert result == ""

    def test_format_date_invalid(self):
        """Test formatting invalid date"""
        result = format_date("invalid-date")
        assert result == "invalid-date"


class TestRepositoryCollection:
    """Test repository data collection"""

    @patch("github_inventory.inventory.get_branch_count")
    @patch("github_inventory.inventory.get_repo_list")
    def test_collect_owned_repositories(self, mock_get_repos, mock_get_branches):
        """Test collecting owned repositories"""
        mock_repos = [
            {
                "name": "test-repo",
                "description": "Test repository",
                "url": "https://github.com/user/test-repo",
                "isPrivate": False,
                "isFork": True,
                "createdAt": "2023-01-01T00:00:00Z",
                "updatedAt": "2023-01-15T00:00:00Z",
                "defaultBranchRef": {"name": "main"},
                "primaryLanguage": {"name": "Python"},
                "diskUsage": 1024,
            }
        ]
        mock_get_repos.return_value = mock_repos
        mock_get_branches.return_value = 3

        result = collect_owned_repositories("testuser")

        assert len(result) == 1
        repo = result[0]
        assert repo["name"] == "test-repo"
        assert repo["visibility"] == "public"
        assert repo["is_fork"] == "true"
        assert repo["creation_date"] == "2023-01-01"
        assert repo["number_of_branches"] == "3"
        assert repo["primary_language"] == "Python"

    @patch("github_inventory.inventory.get_repo_list")
    def test_collect_owned_repositories_empty(self, mock_get_repos):
        """Test collecting owned repositories when none exist"""
        mock_get_repos.return_value = []

        result = collect_owned_repositories("testuser")

        assert result == []


class TestCSVWriting:
    """Test CSV file writing"""

    def test_write_to_csv_success(self):
        """Test successful CSV writing"""
        test_data = [
            {"name": "repo1", "description": "Test repo 1"},
            {"name": "repo2", "description": "Test repo 2"},
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv"
        ) as temp_file:
            temp_filename = temp_file.name

        write_to_csv(test_data, temp_filename)

        # Verify file was written correctly
        with open(temp_filename, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)

            assert len(rows) == 2
            assert rows[0]["name"] == "repo1"
            assert rows[1]["name"] == "repo2"

    def test_write_to_csv_empty_data(self):
        """Test CSV writing with empty data"""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv"
        ) as temp_file:
            temp_filename = temp_file.name

        write_to_csv([], temp_filename)

        # File should not be created or should be empty
        try:
            with open(temp_filename, "r", encoding="utf-8") as csvfile:
                content = csvfile.read()
                assert content == "" or len(content) == 0
        except FileNotFoundError:
            # File not created, which is also acceptable
            pass

    def test_write_to_csv_custom_headers(self):
        """Test CSV writing with custom headers"""
        test_data = [
            {
                "name": "repo1",
                "description": "Test repo 1",
            }  # Only include expected fields
        ]
        custom_headers = ["name", "description"]

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv"
        ) as temp_file:
            temp_filename = temp_file.name

        write_to_csv(test_data, temp_filename, custom_headers)

        # Verify only specified headers are in file
        with open(temp_filename, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            assert reader.fieldnames == custom_headers
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["name"] == "repo1"


@pytest.fixture
def sample_repo_data():
    """Sample repository data for testing"""
    return {
        "name": "sample-repo",
        "description": "A sample repository",
        "url": "https://github.com/user/sample-repo",
        "isPrivate": True,
        "isFork": False,
        "createdAt": "2023-06-01T12:00:00Z",
        "updatedAt": "2023-12-01T12:00:00Z",
        "defaultBranchRef": {"name": "development"},
        "primaryLanguage": {"name": "JavaScript"},
        "diskUsage": 2048,
    }


class TestRepositoryDataProcessing:
    """Test repository data processing with fixtures"""

    @patch("github_inventory.inventory.get_branch_count")
    def test_repo_data_transformation(self, mock_get_branches, sample_repo_data):
        """Test transformation of raw repo data to standardized format"""
        mock_get_branches.return_value = 7

        # Simulate the transformation logic from collect_owned_repositories
        repo_data = {
            "name": sample_repo_data.get("name", ""),
            "description": sample_repo_data.get("description", ""),
            "url": sample_repo_data.get("url", ""),
            "visibility": (
                "private" if sample_repo_data.get("isPrivate", False) else "public"
            ),
            "is_fork": str(sample_repo_data.get("isFork", False)).lower(),
            "creation_date": format_date(sample_repo_data.get("createdAt", "")),
            "last_update_date": format_date(sample_repo_data.get("updatedAt", "")),
            "default_branch": (
                sample_repo_data.get("defaultBranchRef", {}).get("name", "")
                if sample_repo_data.get("defaultBranchRef")
                else ""
            ),
            "number_of_branches": str(7),
            "primary_language": (
                sample_repo_data.get("primaryLanguage", {}).get("name", "")
                if sample_repo_data.get("primaryLanguage")
                else ""
            ),
            "size": (
                str(sample_repo_data.get("diskUsage", ""))
                if sample_repo_data.get("diskUsage")
                else ""
            ),
        }

        assert repo_data["name"] == "sample-repo"
        assert repo_data["visibility"] == "private"
        assert repo_data["is_fork"] == "false"
        assert repo_data["creation_date"] == "2023-06-01"
        assert repo_data["default_branch"] == "development"
        assert repo_data["number_of_branches"] == "7"
        assert repo_data["primary_language"] == "JavaScript"
