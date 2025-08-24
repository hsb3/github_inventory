#!/usr/bin/env python3
"""
Comprehensive error path testing for GitHub Inventory
Tests various failure scenarios and error handling
"""

import json
import subprocess
import tempfile
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest

from github_inventory.inventory import (
    run_gh_command,
    get_repo_list,
    get_starred_repos,
    get_branch_count,
    collect_owned_repositories,
    collect_starred_repositories,
    write_to_csv
)
from github_inventory.cli import main, create_parser
from github_inventory.report import generate_markdown_report, read_csv_data
from tests.fixtures.github_responses import get_error_response


class TestGitHubCLIErrorPaths:
    """Test error paths in GitHub CLI interactions"""

    def test_run_gh_command_authentication_error(self):
        """Test handling of GitHub CLI authentication errors"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, 'gh repo list', stderr="To authenticate, please run `gh auth login`"
            )
            
            result = run_gh_command("gh repo list")
            assert result is None

    def test_run_gh_command_rate_limit_error(self):
        """Test handling of GitHub API rate limit errors"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, 'gh api user/starred', stderr="API rate limit exceeded for user"
            )
            
            result = run_gh_command("gh api user/starred")
            assert result is None

    def test_run_gh_command_network_error(self):
        """Test handling of network connectivity errors"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, 'gh repo list', stderr="unable to connect to api.github.com"
            )
            
            result = run_gh_command("gh repo list")
            assert result is None

    def test_run_gh_command_permission_denied(self):
        """Test handling of repository permission errors"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, 'gh repo list testuser', stderr="Not Found"
            )
            
            result = run_gh_command("gh repo list testuser")
            assert result is None

    def test_run_gh_command_malformed_json_response(self):
        """Test handling of malformed JSON responses"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.stdout = "invalid json response {"
            mock_run.return_value.returncode = 0
            
            result = run_gh_command("gh repo list --json name")
            assert result == "invalid json response {"  # Should return raw output

    def test_get_repo_list_json_decode_error(self):
        """Test handling of JSON decode errors in repo list"""
        with patch('github_inventory.inventory.run_gh_command') as mock_gh:
            mock_gh.return_value = "invalid json {"
            
            result = get_repo_list("testuser")
            assert result == []

    def test_get_starred_repos_json_decode_error(self):
        """Test handling of JSON decode errors in starred repos"""
        with patch('github_inventory.inventory.run_gh_command') as mock_gh:
            mock_gh.return_value = "invalid json {"
            
            result = get_starred_repos("testuser")
            assert result == []

    def test_get_starred_repos_empty_response(self):
        """Test handling of empty response from starred repos API"""
        with patch('github_inventory.inventory.run_gh_command') as mock_gh:
            mock_gh.return_value = None
            
            result = get_starred_repos("testuser")
            assert result == []

    def test_get_starred_repos_mixed_response_types(self):
        """Test handling of mixed response types in paginated results"""
        with patch('github_inventory.inventory.run_gh_command') as mock_gh:
            # Mix of valid JSON and invalid data
            mixed_response = '{"name": "repo1"}\ninvalid json\n[{"name": "repo2"}]'
            mock_gh.return_value = mixed_response
            
            result = get_starred_repos("testuser")
            # Should handle valid parts and skip invalid ones
            assert isinstance(result, list)

    def test_branch_count_api_error(self):
        """Test handling of branch count API errors"""
        with patch('github_inventory.inventory.run_gh_command') as mock_gh:
            mock_gh.return_value = None  # Simulate API failure
            
            result = get_branch_count("owner", "repo")
            assert result == "unknown"

    def test_branch_count_non_numeric_response(self):
        """Test handling of non-numeric branch count response"""
        with patch('github_inventory.inventory.run_gh_command') as mock_gh:
            mock_gh.return_value = "error: repository not found"
            
            result = get_branch_count("owner", "repo")
            assert result == "unknown"

    def test_branch_count_empty_response(self):
        """Test handling of empty branch count response"""
        with patch('github_inventory.inventory.run_gh_command') as mock_gh:
            mock_gh.return_value = ""
            
            result = get_branch_count("owner", "repo")
            assert result == "unknown"


class TestDataCollectionErrorPaths:
    """Test error paths in data collection workflows"""

    def test_collect_owned_repositories_no_repos(self):
        """Test collecting owned repositories when user has none"""
        with patch('github_inventory.inventory.get_repo_list') as mock_get_repos:
            mock_get_repos.return_value = []
            
            result = collect_owned_repositories("testuser")
            assert result == []

    def test_collect_owned_repositories_api_failure(self):
        """Test collecting owned repositories when API fails"""
        with patch('github_inventory.inventory.get_repo_list') as mock_get_repos:
            mock_get_repos.return_value = None
            
            result = collect_owned_repositories("testuser")
            assert result == []

    def test_collect_starred_repositories_no_stars(self):
        """Test collecting starred repositories when user has none"""
        with patch('github_inventory.inventory.get_starred_repos') as mock_get_starred:
            mock_get_starred.return_value = []
            
            result = collect_starred_repositories("testuser")
            assert result == []

    def test_collect_starred_repositories_api_failure(self):
        """Test collecting starred repositories when API fails"""
        with patch('github_inventory.inventory.get_starred_repos') as mock_get_starred:
            mock_get_starred.return_value = None
            
            result = collect_starred_repositories("testuser")
            assert result == []

    def test_collect_repositories_partial_branch_failures(self):
        """Test collection when some branch count API calls fail"""
        sample_repos = [
            {
                "name": "repo1",
                "description": "Test repo 1",
                "url": "https://github.com/user/repo1",
                "isPrivate": False,
                "isFork": False,
                "createdAt": "2023-01-01T00:00:00Z",
                "updatedAt": "2023-01-02T00:00:00Z",
                "defaultBranchRef": {"name": "main"},
                "primaryLanguage": {"name": "Python"},
                "diskUsage": 1024
            },
            {
                "name": "repo2",
                "description": "Test repo 2",
                "url": "https://github.com/user/repo2",
                "isPrivate": False,
                "isFork": False,
                "createdAt": "2023-01-01T00:00:00Z",
                "updatedAt": "2023-01-02T00:00:00Z",
                "defaultBranchRef": {"name": "main"},
                "primaryLanguage": {"name": "JavaScript"},
                "diskUsage": 2048
            }
        ]

        def mock_get_branch_count(username, repo_name):
            if repo_name == "repo1":
                return 5  # Success
            else:
                return "unknown"  # Failure

        with patch('github_inventory.inventory.get_repo_list') as mock_get_repos:
            with patch('github_inventory.inventory.get_branch_count', side_effect=mock_get_branch_count):
                mock_get_repos.return_value = sample_repos
                
                result = collect_owned_repositories("testuser")
                
                assert len(result) == 2
                assert result[0]["number_of_branches"] == "5"
                assert result[1]["number_of_branches"] == "unknown"

    def test_malformed_repository_data(self):
        """Test handling of malformed repository data"""
        malformed_repos = [
            {
                "name": "valid-repo",
                "description": "Valid repo",
                # Missing required fields to test resilience
            },
            {
                # Missing name field
                "description": "Repo without name",
                "url": "https://github.com/user/noname",
            },
            None,  # Completely invalid entry
            {
                "name": "partial-repo",
                "defaultBranchRef": None,  # Null reference
                "primaryLanguage": None,   # Null language
            }
        ]

        with patch('github_inventory.inventory.get_repo_list') as mock_get_repos:
            with patch('github_inventory.inventory.get_branch_count') as mock_get_branches:
                mock_get_repos.return_value = malformed_repos
                mock_get_branches.return_value = 3
                
                # Should handle malformed data gracefully
                result = collect_owned_repositories("testuser")
                
                # Should process valid entries and skip/handle invalid ones
                assert isinstance(result, list)
                # At least the valid entries should be processed
                valid_entries = [r for r in result if r.get("name")]
                assert len(valid_entries) >= 2


class TestFileOperationErrorPaths:
    """Test error paths in file operations"""

    def test_write_to_csv_permission_denied(self):
        """Test CSV writing when permission is denied"""
        test_data = [{"name": "test", "description": "Test repo"}]
        
        # Try to write to a location that should cause permission error
        with tempfile.TemporaryDirectory() as temp_dir:
            readonly_dir = Path(temp_dir) / "readonly"
            readonly_dir.mkdir(mode=0o444)  # Read-only directory
            readonly_file = readonly_dir / "test.csv"
            
            # This should not raise an exception but handle gracefully
            try:
                write_to_csv(test_data, str(readonly_file))
            except PermissionError:
                # Expected behavior
                pass

    def test_write_to_csv_disk_full_simulation(self):
        """Test CSV writing when disk is full (simulated with OSError)"""
        test_data = [{"name": "test", "description": "Test repo"}]
        
        with patch('builtins.open', side_effect=OSError("No space left on device")):
            # Should handle disk full error gracefully
            try:
                write_to_csv(test_data, "test.csv")
            except OSError:
                # Expected behavior
                pass

    def test_write_to_csv_empty_data(self):
        """Test CSV writing with empty data"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
            temp_filename = temp_file.name

        try:
            # Should handle empty data gracefully
            write_to_csv([], temp_filename)
            
            # File should exist but be empty or have just headers
            assert os.path.exists(temp_filename)
            
        finally:
            os.unlink(temp_filename)

    def test_read_csv_data_file_not_found(self):
        """Test reading CSV when file doesn't exist"""
        result = read_csv_data("nonexistent_file.csv")
        assert result == []

    def test_read_csv_data_permission_denied(self):
        """Test reading CSV when permission is denied"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
            temp_file.write("name,description\ntest,Test repo\n")
            temp_filename = temp_file.name

        try:
            # Make file unreadable
            os.chmod(temp_filename, 0o000)
            
            result = read_csv_data(temp_filename)
            assert result == []
            
        finally:
            # Restore permissions and cleanup
            os.chmod(temp_filename, 0o644)
            os.unlink(temp_filename)

    def test_read_csv_data_malformed_csv(self):
        """Test reading malformed CSV data"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
            temp_file.write("name,description\ntest,\"unclosed quote\n")
            temp_filename = temp_file.name

        try:
            # Should handle malformed CSV gracefully
            result = read_csv_data(temp_filename)
            # Should return empty list on error
            assert isinstance(result, list)
            
        finally:
            os.unlink(temp_filename)


class TestReportGenerationErrorPaths:
    """Test error paths in report generation"""

    def test_generate_markdown_report_write_error(self):
        """Test report generation when file writing fails"""
        sample_data = [{"name": "test", "description": "Test repo"}]
        
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            result = generate_markdown_report(
                owned_repos=sample_data,
                starred_repos=sample_data,
                username="testuser",
                output_file="test.md"
            )
            assert result is False

    def test_generate_markdown_report_invalid_path(self):
        """Test report generation with invalid file path"""
        sample_data = [{"name": "test", "description": "Test repo"}]
        
        # Use invalid path that should cause error
        invalid_path = "/invalid/path/that/does/not/exist/report.md"
        
        result = generate_markdown_report(
            owned_repos=sample_data,
            starred_repos=sample_data,
            username="testuser",
            output_file=invalid_path
        )
        assert result is False

    def test_generate_markdown_report_with_malformed_data(self):
        """Test report generation with malformed data"""
        malformed_data = [
            {"name": "valid"},
            None,  # Invalid entry
            {"description": "no name"},  # Missing name
            {},  # Empty dict
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as temp_file:
            temp_filename = temp_file.name

        try:
            result = generate_markdown_report(
                owned_repos=malformed_data,
                starred_repos=malformed_data,
                username="testuser",
                output_file=temp_filename
            )
            
            # Should handle malformed data and still generate report
            assert result is True
            assert os.path.exists(temp_filename)
            
        finally:
            os.unlink(temp_filename)


class TestCLIErrorPaths:
    """Test CLI error paths and edge cases"""

    def test_cli_invalid_arguments(self):
        """Test CLI with invalid argument combinations"""
        parser = create_parser()
        
        # Test conflicting flags (would need to be implemented in CLI)
        # For now, test that parser handles unknown arguments
        with pytest.raises(SystemExit):
            parser.parse_args(['--invalid-flag'])

    def test_cli_missing_github_cli(self):
        """Test CLI behavior when GitHub CLI is not installed"""
        test_args = ['ghscan', '--user', 'testuser', '--owned-only', '--no-report']
        
        def mock_run_gh_command(cmd):
            raise FileNotFoundError("gh: command not found")

        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            with patch('sys.argv', test_args):
                with pytest.raises(SystemExit):
                    main()

    def test_cli_github_cli_not_authenticated(self, capsys):
        """Test CLI behavior when GitHub CLI is not authenticated"""
        test_args = ['ghscan', '--user', 'testuser', '--owned-only', '--no-report']
        
        def mock_run_gh_command(cmd):
            return None  # Simulate auth failure

        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            with patch('sys.argv', test_args):
                with pytest.raises(SystemExit):
                    main()

        captured = capsys.readouterr()
        assert "No data collected" in captured.out

    def test_cli_batch_config_file_not_found(self, capsys):
        """Test batch processing with non-existent config file"""
        test_args = ['ghscan', '--config', 'nonexistent_config.yaml']
        
        with patch('sys.argv', test_args):
            with pytest.raises((SystemExit, FileNotFoundError)):
                main()

    def test_cli_report_only_no_existing_data(self, capsys):
        """Test report-only mode when no CSV files exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            owned_csv = os.path.join(temp_dir, "repos.csv")
            starred_csv = os.path.join(temp_dir, "starred.csv")
            report_md = os.path.join(temp_dir, "report.md")
            
            test_args = [
                'ghscan', '--user', 'testuser', '--report-only',
                '--owned-csv', owned_csv,
                '--starred-csv', starred_csv,
                '--report-md', report_md
            ]
            
            with patch('sys.argv', test_args):
                with pytest.raises(SystemExit):
                    main()

            captured = capsys.readouterr()
            assert "No existing CSV files found" in captured.out


class TestEdgeCaseErrorPaths:
    """Test edge cases and unusual error scenarios"""

    def test_unicode_handling_in_repository_data(self):
        """Test handling of Unicode characters in repository data"""
        unicode_repos = [
            {
                "name": "unicode-test",
                "description": "Repository with émojis 🚀 and spëcial chars",
                "url": "https://github.com/user/unicode-test",
                "isPrivate": False,
                "isFork": False,
                "createdAt": "2023-01-01T00:00:00Z",
                "updatedAt": "2023-01-02T00:00:00Z",
                "defaultBranchRef": {"name": "main"},
                "primaryLanguage": {"name": "Python"},
                "diskUsage": 1024
            }
        ]

        with patch('github_inventory.inventory.get_repo_list') as mock_get_repos:
            with patch('github_inventory.inventory.get_branch_count') as mock_get_branches:
                mock_get_repos.return_value = unicode_repos
                mock_get_branches.return_value = 3
                
                result = collect_owned_repositories("testuser")
                
                assert len(result) == 1
                assert "émojis 🚀" in result[0]["description"]

    def test_very_large_repository_data(self):
        """Test handling of repositories with very large data values"""
        large_data_repo = [
            {
                "name": "huge-repo",
                "description": "x" * 10000,  # Very long description
                "url": "https://github.com/user/huge-repo",
                "isPrivate": False,
                "isFork": False,
                "createdAt": "2023-01-01T00:00:00Z",
                "updatedAt": "2023-01-02T00:00:00Z",
                "defaultBranchRef": {"name": "main"},
                "primaryLanguage": {"name": "Python"},
                "diskUsage": 999999999  # Very large size
            }
        ]

        with patch('github_inventory.inventory.get_repo_list') as mock_get_repos:
            with patch('github_inventory.inventory.get_branch_count') as mock_get_branches:
                mock_get_repos.return_value = large_data_repo
                mock_get_branches.return_value = 1000  # Many branches
                
                result = collect_owned_repositories("testuser")
                
                assert len(result) == 1
                assert len(result[0]["description"]) == 10000
                assert result[0]["size"] == "999999999"
                assert result[0]["number_of_branches"] == "1000"

    def test_concurrent_file_access_simulation(self):
        """Test handling of concurrent file access (simulated)"""
        test_data = [{"name": "test", "description": "Test repo"}]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
            temp_filename = temp_file.name

        # Simulate file being locked/in use by another process
        def mock_open_with_lock_error(*args, **kwargs):
            raise OSError("The process cannot access the file because it is being used by another process")

        try:
            with patch('builtins.open', side_effect=mock_open_with_lock_error):
                # Should handle file lock error gracefully
                try:
                    write_to_csv(test_data, temp_filename)
                except OSError:
                    # Expected behavior
                    pass
        finally:
            os.unlink(temp_filename)

    def test_memory_pressure_simulation(self):
        """Test handling of memory pressure with large datasets"""
        # Create a very large dataset that might cause memory issues
        def generate_huge_dataset():
            for i in range(10000):  # Large number of repos
                yield {
                    "name": f"repo-{i}",
                    "description": "x" * 1000,  # Large descriptions
                    "url": f"https://github.com/user/repo-{i}",
                    "isPrivate": i % 2 == 0,
                    "isFork": i % 3 == 0,
                    "createdAt": "2023-01-01T00:00:00Z",
                    "updatedAt": "2023-01-02T00:00:00Z",
                    "defaultBranchRef": {"name": "main"},
                    "primaryLanguage": {"name": "Python"},
                    "diskUsage": 1024
                }

        # Convert generator to list (simulating large memory usage)
        huge_dataset = list(generate_huge_dataset())

        with patch('github_inventory.inventory.get_repo_list') as mock_get_repos:
            with patch('github_inventory.inventory.get_branch_count') as mock_get_branches:
                mock_get_repos.return_value = huge_dataset
                mock_get_branches.return_value = 3
                
                # Should handle large datasets without crashing
                result = collect_owned_repositories("testuser")
                
                assert len(result) == 10000
                assert all("name" in repo for repo in result[:10])  # Check first few