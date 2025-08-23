#!/usr/bin/env python3
"""
Tests for --limit parameter functionality
"""

from unittest.mock import patch

from github_inventory.cli import create_parser
from github_inventory.inventory import (
    collect_owned_repositories,
    collect_starred_repositories,
    get_repo_list,
    get_starred_repos,
)


class TestLimitParameter:
    """Test --limit parameter functionality"""

    def test_cli_limit_parameter(self):
        """Test that CLI accepts --limit parameter"""
        parser = create_parser()
        args = parser.parse_args(["--limit", "25"])

        assert args.limit == 25

        # Test without limit
        args = parser.parse_args([])
        assert args.limit is None

    @patch("github_inventory.inventory.run_gh_command")
    def test_get_repo_list_with_limit(self, mock_run_gh):
        """Test that get_repo_list respects limit parameter"""
        mock_run_gh.return_value = "[]"

        # Test with limit
        get_repo_list("testuser", limit=50)
        mock_run_gh.assert_called_once()
        called_cmd = mock_run_gh.call_args[0][0]
        assert "--limit 50" in called_cmd

        # Test without limit
        mock_run_gh.reset_mock()
        get_repo_list("testuser")
        called_cmd = mock_run_gh.call_args[0][0]
        assert "--limit 1000" in called_cmd

    @patch("github_inventory.inventory.run_gh_command")
    def test_get_starred_repos_with_limit_authenticated_user(self, mock_run_gh):
        """Test that get_starred_repos respects limit for authenticated user"""
        mock_run_gh.return_value = "[]"

        # Test with limit (authenticated user)
        get_starred_repos(username=None, limit=30)
        mock_run_gh.assert_called_once()
        called_cmd = mock_run_gh.call_args[0][0]
        assert "user/starred" in called_cmd
        assert "[0:30]" in called_cmd

        # Test without limit (authenticated user)
        mock_run_gh.reset_mock()
        get_starred_repos(username=None)
        called_cmd = mock_run_gh.call_args[0][0]
        assert "user/starred" in called_cmd
        assert "--paginate" in called_cmd

    @patch("github_inventory.inventory.run_gh_command")
    def test_get_starred_repos_with_limit_specific_user(self, mock_run_gh):
        """Test that get_starred_repos respects limit for specific user"""
        mock_run_gh.return_value = "[]"

        # Test with limit (specific user)
        get_starred_repos(username="testuser", limit=25)
        mock_run_gh.assert_called_once()
        called_cmd = mock_run_gh.call_args[0][0]
        assert "users/testuser/starred" in called_cmd
        assert "[0:25]" in called_cmd

        # Test without limit (specific user)
        mock_run_gh.reset_mock()
        get_starred_repos(username="testuser")
        called_cmd = mock_run_gh.call_args[0][0]
        assert "users/testuser/starred" in called_cmd
        assert "--paginate" in called_cmd

    @patch("github_inventory.inventory.get_branch_count")
    @patch("github_inventory.inventory.get_repo_list")
    def test_collect_owned_repositories_with_limit(
        self, mock_get_repos, mock_get_branches
    ):
        """Test that collect_owned_repositories passes limit correctly"""
        mock_repos = [
            {
                "name": "test-repo",
                "description": "Test repository",
                "url": "https://github.com/user/test-repo",
                "isPrivate": False,
                "isFork": False,
                "createdAt": "2023-01-01T00:00:00Z",
                "updatedAt": "2023-01-15T00:00:00Z",
                "defaultBranchRef": {"name": "main"},
                "primaryLanguage": {"name": "Python"},
                "diskUsage": 1024,
            }
        ]
        mock_get_repos.return_value = mock_repos
        mock_get_branches.return_value = 2

        # Test with limit
        result = collect_owned_repositories("testuser", limit=10)
        mock_get_repos.assert_called_once_with("testuser", 10)
        assert len(result) == 1

        # Test without limit
        mock_get_repos.reset_mock()
        collect_owned_repositories("testuser")
        mock_get_repos.assert_called_once_with("testuser", None)

    @patch("github_inventory.inventory.get_branch_count")
    @patch("github_inventory.inventory.get_starred_repos")
    def test_collect_starred_repositories_with_limit(
        self, mock_get_starred, mock_get_branches
    ):
        """Test that collect_starred_repositories passes limit correctly"""
        mock_repos = [
            {
                "name": "starred-repo",
                "full_name": "owner/starred-repo",
                "owner": {"login": "owner"},
                "description": "A starred repository",
                "html_url": "https://github.com/owner/starred-repo",
                "private": False,
                "fork": False,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-15T00:00:00Z",
                "pushed_at": "2023-01-14T00:00:00Z",
                "default_branch": "main",
                "language": "JavaScript",
                "size": 2048,
                "stargazers_count": 100,
                "forks_count": 10,
                "watchers_count": 100,
                "open_issues_count": 5,
                "license": {"name": "MIT"},
                "topics": ["cli", "tool"],
                "homepage": "",
                "archived": False,
                "disabled": False,
            }
        ]
        mock_get_starred.return_value = mock_repos
        mock_get_branches.return_value = 3

        # Test with limit
        result = collect_starred_repositories("testuser", limit=15)
        mock_get_starred.assert_called_once_with("testuser", 15)
        assert len(result) == 1

        # Test without limit
        mock_get_starred.reset_mock()
        collect_starred_repositories("testuser")
        mock_get_starred.assert_called_once_with("testuser", None)

    @patch("github_inventory.cli.collect_starred_repositories")
    @patch("github_inventory.cli.collect_owned_repositories")
    def test_cli_integration_with_limit(self, mock_collect_owned, mock_collect_starred):
        """Test that CLI passes limit to collection functions"""
        import sys

        from github_inventory.cli import main

        # Mock the collections to return empty lists
        mock_collect_owned.return_value = []
        mock_collect_starred.return_value = []

        # Test with limit
        test_args = [
            "gh-inventory",
            "--user",
            "testuser",
            "--limit",
            "20",
            "--no-report",
        ]
        with patch.object(sys, "argv", test_args):
            try:
                main()
            except SystemExit:
                pass  # Expected for no data

        # Verify both functions were called with limit
        mock_collect_owned.assert_called_once_with("testuser", 20)
        mock_collect_starred.assert_called_once_with("testuser", 20)


class TestLimitEdgeCases:
    """Test edge cases for limit parameter"""

    def test_cli_limit_zero(self):
        """Test that limit of 0 is handled"""
        parser = create_parser()
        args = parser.parse_args(["--limit", "0"])
        assert args.limit == 0

    def test_cli_limit_negative(self):
        """Test that negative limit is handled"""
        parser = create_parser()
        args = parser.parse_args(["--limit", "-1"])
        assert args.limit == -1

    @patch("github_inventory.inventory.run_gh_command")
    def test_limit_edge_cases_in_commands(self, mock_run_gh):
        """Test edge cases in command generation"""
        mock_run_gh.return_value = "[]"

        # Test limit 0 - should still generate valid command
        get_repo_list("testuser", limit=0)
        called_cmd = mock_run_gh.call_args[0][0]
        assert "--limit 0" in called_cmd

        # Test very large limit
        mock_run_gh.reset_mock()
        get_repo_list("testuser", limit=9999)
        called_cmd = mock_run_gh.call_args[0][0]
        assert "--limit 9999" in called_cmd
