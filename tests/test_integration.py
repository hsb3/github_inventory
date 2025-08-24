#!/usr/bin/env python3
"""
Integration tests for GitHub Inventory
Tests the complete workflow using realistic GitHub CLI responses
"""

import json
import tempfile
import os
from unittest.mock import patch, MagicMock
from pathlib import Path
import subprocess

import pytest

from github_inventory.inventory import (
    collect_owned_repositories,
    collect_starred_repositories,
    run_gh_command,
    get_repo_list,
    get_starred_repos,
    get_branch_count
)
from github_inventory.cli import main
from tests.fixtures.github_responses import (
    get_owned_repos_json,
    get_starred_repos_json,
    get_branch_count,
    get_error_response,
    SAMPLE_OWNED_REPOS_RESPONSE,
    SAMPLE_STARRED_REPOS_RESPONSE
)


class TestGitHubCLIIntegration:
    """Test GitHub CLI integration with realistic responses"""

    def test_collect_owned_repositories_integration(self):
        """Test complete owned repository collection workflow"""
        def mock_run_gh_command(cmd):
            # Mock different command types based on the command string
            if 'gh repo list' in cmd:
                return get_owned_repos_json()
            elif 'gh api repos/' in cmd and '/branches' in cmd:
                # Extract owner/repo from command for branch count
                # Format: gh api repos/{owner}/{repo}/branches --jq "length"
                parts = cmd.split('/')
                if len(parts) >= 4:
                    owner = parts[2]
                    repo = parts[3]
                    return get_branch_count(owner, repo)
                return "3"  # Default
            return None

        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            result = collect_owned_repositories("testuser", limit=10)

            # Verify structure and data transformation
            assert len(result) == 3
            
            # Check first repo (github_inventory)
            repo1 = result[0]
            assert repo1["name"] == "github_inventory"
            assert repo1["description"] == "A comprehensive GitHub repository inventory and analysis tool"
            assert repo1["visibility"] == "public"
            assert repo1["is_fork"] == "false"
            assert repo1["creation_date"] == "2023-01-15"
            assert repo1["last_update_date"] == "2023-12-01"
            assert repo1["default_branch"] == "main"
            assert repo1["number_of_branches"] == "5"
            assert repo1["primary_language"] == "Python"
            assert repo1["size"] == "2048"
            
            # Check fork repo
            repo2 = result[1]
            assert repo2["name"] == "test-fork"
            assert repo2["visibility"] == "private"
            assert repo2["is_fork"] == "true"
            assert repo2["default_branch"] == "develop"
            assert repo2["primary_language"] == "JavaScript"
            
            # Check repo with null values
            repo3 = result[2]
            assert repo3["name"] == "private-project"
            assert repo3["description"] == ""  # Should handle None
            assert repo3["primary_language"] == ""  # Should handle None

    def test_collect_starred_repositories_integration(self):
        """Test complete starred repository collection workflow"""
        def mock_run_gh_command(cmd):
            if 'gh api user/starred' in cmd or 'gh api users/' in cmd:
                return get_starred_repos_json()
            elif 'gh api repos/' in cmd and '/branches' in cmd:
                parts = cmd.split('/')
                if len(parts) >= 4:
                    owner = parts[2]
                    repo = parts[3]
                    return get_branch_count(owner, repo)
                return "3"
            return None

        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            result = collect_starred_repositories("testuser", limit=10)

            assert len(result) == 3
            
            # Check awesome-python repo
            repo1 = result[0]
            assert repo1["name"] == "awesome-python"
            assert repo1["full_name"] == "vinta/awesome-python"
            assert repo1["owner"] == "vinta"
            assert repo1["visibility"] == "public"
            assert repo1["is_fork"] == "false"
            assert repo1["primary_language"] == "Python"
            assert repo1["stars"] == "180234"
            assert repo1["forks"] == "24567"
            assert repo1["topics"] == "awesome, awesome-list, python"
            assert repo1["license"] == "Other"
            assert repo1["archived"] == "false"
            
            # Check tensorflow repo
            repo2 = result[1]
            assert repo2["name"] == "tensorflow"
            assert repo2["owner"] == "tensorflow"
            assert repo2["primary_language"] == "C++"
            assert repo2["license"] == "Apache License 2.0"
            
            # Check archived repo
            repo3 = result[2]
            assert repo3["name"] == "archived-project"
            assert repo3["is_fork"] == "true"
            assert repo3["archived"] == "true"

    def test_github_cli_error_handling_integration(self):
        """Test integration with various GitHub CLI error scenarios"""
        
        def mock_failing_gh_command(cmd):
            # Simulate different types of failures
            if 'auth' in cmd:
                error = get_error_response("auth_required")
                raise subprocess.CalledProcessError(
                    error["returncode"], cmd, stderr=error["stderr"]
                )
            return None

        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_failing_gh_command):
            result = collect_owned_repositories("testuser")
            assert result == []

    def test_branch_count_api_failure_integration(self):
        """Test integration when branch count API calls fail"""
        def mock_run_gh_command(cmd):
            if 'gh repo list' in cmd:
                return json.dumps([SAMPLE_OWNED_REPOS_RESPONSE[0]])  # Just one repo
            elif 'gh api repos/' in cmd and '/branches' in cmd:
                # Simulate API failure for branch count
                raise subprocess.CalledProcessError(1, cmd, stderr="API rate limit exceeded")
            return None

        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            result = collect_owned_repositories("testuser")
            
            assert len(result) == 1
            # Should handle branch count failure gracefully
            assert result[0]["number_of_branches"] == "unknown"

    def test_pagination_integration(self):
        """Test integration with GitHub CLI pagination"""
        # Simulate paginated response (multiple JSON arrays)
        paginated_response = json.dumps(SAMPLE_STARRED_REPOS_RESPONSE[:2]) + "\n" + json.dumps(SAMPLE_STARRED_REPOS_RESPONSE[2:])
        
        def mock_run_gh_command(cmd):
            if 'gh api user/starred' in cmd and '--paginate' in cmd:
                return paginated_response
            elif 'gh api repos/' in cmd and '/branches' in cmd:
                return "3"
            return None

        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            starred_repos = get_starred_repos()
            assert len(starred_repos) == 3

    def test_limit_parameter_integration(self):
        """Test integration with limit parameter in GitHub CLI commands"""
        with patch('github_inventory.inventory.run_gh_command') as mock_gh:
            mock_gh.return_value = get_owned_repos_json()
            
            # Test with limit
            get_repo_list("testuser", limit=50)
            mock_gh.assert_called_once()
            called_cmd = mock_gh.call_args[0][0]
            assert "--limit 50" in called_cmd
            
            # Test starred repos with limit
            mock_gh.reset_mock()
            mock_gh.return_value = "[]"
            get_starred_repos("testuser", limit=25)
            called_cmd = mock_gh.call_args[0][0]
            assert "[0:25]" in called_cmd


class TestDataIntegrity:
    """Test data integrity throughout the complete workflow"""

    def test_data_consistency_owned_to_csv(self):
        """Test data consistency from collection to CSV output"""
        def mock_run_gh_command(cmd):
            if 'gh repo list' in cmd:
                return get_owned_repos_json()
            elif 'gh api repos/' in cmd and '/branches' in cmd:
                return "3"
            return None

        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
                temp_filename = temp_file.name

            try:
                from github_inventory.inventory import write_to_csv
                
                repos = collect_owned_repositories("testuser")
                write_to_csv(repos, temp_filename)

                # Read back and verify
                import csv
                with open(temp_filename, 'r', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    csv_data = list(reader)

                assert len(csv_data) == 3
                assert csv_data[0]["name"] == "github_inventory"
                assert csv_data[0]["visibility"] == "public"
                
            finally:
                os.unlink(temp_filename)

    def test_data_consistency_starred_to_csv(self):
        """Test data consistency for starred repositories"""
        def mock_run_gh_command(cmd):
            if 'gh api user/starred' in cmd:
                return get_starred_repos_json()
            elif 'gh api repos/' in cmd and '/branches' in cmd:
                return "3"
            return None

        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
                temp_filename = temp_file.name

            try:
                from github_inventory.inventory import write_to_csv
                
                repos = collect_starred_repositories("testuser")
                write_to_csv(repos, temp_filename)

                # Read back and verify
                import csv
                with open(temp_filename, 'r', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    csv_data = list(reader)

                assert len(csv_data) == 3
                assert csv_data[0]["name"] == "awesome-python"
                assert csv_data[0]["stars"] == "180234"
                
            finally:
                os.unlink(temp_filename)

    def test_null_value_handling_integration(self):
        """Test proper handling of null/None values throughout workflow"""
        # Create a repo with various null fields
        null_repo = {
            "name": "null-test",
            "description": None,
            "url": "https://github.com/test/null-test",
            "isPrivate": False,
            "isFork": False,
            "createdAt": None,
            "updatedAt": None,
            "defaultBranchRef": None,
            "primaryLanguage": None,
            "diskUsage": None
        }

        def mock_run_gh_command(cmd):
            if 'gh repo list' in cmd:
                return json.dumps([null_repo])
            elif 'gh api repos/' in cmd:
                return "2"
            return None

        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            result = collect_owned_repositories("testuser")
            
            assert len(result) == 1
            repo = result[0]
            
            # Verify null handling
            assert repo["description"] == ""
            assert repo["creation_date"] == ""
            assert repo["last_update_date"] == ""
            assert repo["default_branch"] == ""
            assert repo["primary_language"] == ""
            assert repo["size"] == ""


class TestRealWorldScenarios:
    """Test real-world integration scenarios"""

    def test_mixed_repository_types_integration(self):
        """Test integration with mixed repository types (public/private, fork/original)"""
        def mock_run_gh_command(cmd):
            if 'gh repo list' in cmd:
                return get_owned_repos_json()  # Contains mix of repo types
            elif 'gh api repos/' in cmd and '/branches' in cmd:
                return "4"
            return None

        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            result = collect_owned_repositories("testuser")
            
            # Verify we have different types
            visibilities = {repo["visibility"] for repo in result}
            fork_statuses = {repo["is_fork"] for repo in result}
            languages = {repo["primary_language"] for repo in result if repo["primary_language"]}
            
            assert "public" in visibilities
            assert "private" in visibilities
            assert "true" in fork_statuses
            assert "false" in fork_statuses
            assert len(languages) >= 2  # Multiple languages

    def test_empty_results_integration(self):
        """Test integration when GitHub CLI returns empty results"""
        def mock_run_gh_command(cmd):
            if 'gh repo list' in cmd or 'gh api user/starred' in cmd:
                return "[]"
            return None

        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            owned_result = collect_owned_repositories("testuser")
            starred_result = collect_starred_repositories("testuser")
            
            assert owned_result == []
            assert starred_result == []

    def test_large_response_handling_integration(self):
        """Test integration with large GitHub CLI responses"""
        # Create a larger dataset
        from tests.fixtures.github_responses import generate_large_repo_dataset
        large_dataset = generate_large_repo_dataset(50)
        
        def mock_run_gh_command(cmd):
            if 'gh repo list' in cmd:
                return json.dumps(large_dataset)
            elif 'gh api repos/' in cmd and '/branches' in cmd:
                return "3"
            return None

        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            result = collect_owned_repositories("testuser")
            
            assert len(result) == 50
            # Verify data integrity on larger dataset
            assert all("name" in repo for repo in result)
            assert all("visibility" in repo for repo in result)


@pytest.fixture
def temp_output_dir():
    """Fixture providing temporary output directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


class TestWorkflowIntegration:
    """Test complete workflow integration"""

    def test_complete_data_collection_workflow(self, temp_output_dir):
        """Test the complete data collection and CSV writing workflow"""
        def mock_run_gh_command(cmd):
            if 'gh repo list' in cmd:
                return get_owned_repos_json()
            elif 'gh api user/starred' in cmd:
                return get_starred_repos_json()
            elif 'gh api repos/' in cmd and '/branches' in cmd:
                return "3"
            return None

        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            from github_inventory.inventory import write_to_csv
            
            # Collect data
            owned_repos = collect_owned_repositories("testuser")
            starred_repos = collect_starred_repositories("testuser")
            
            # Write to CSV files
            owned_csv = os.path.join(temp_output_dir, "repos.csv")
            starred_csv = os.path.join(temp_output_dir, "starred.csv")
            
            write_to_csv(owned_repos, owned_csv)
            write_to_csv(starred_repos, starred_csv)
            
            # Verify files were created
            assert os.path.exists(owned_csv)
            assert os.path.exists(starred_csv)
            
            # Verify file contents
            assert os.path.getsize(owned_csv) > 0
            assert os.path.getsize(starred_csv) > 0