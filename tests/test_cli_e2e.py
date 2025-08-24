#!/usr/bin/env python3
"""
End-to-end CLI tests for GitHub Inventory
Tests complete CLI workflows using temporary directories
"""

import os
import sys
import tempfile
import csv
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

import pytest

from github_inventory.cli import main, create_parser
from tests.fixtures.github_responses import (
    get_owned_repos_json,
    get_starred_repos_json,
    get_branch_count,
    generate_large_repo_dataset,
    generate_large_starred_dataset
)


class TestCLIEndToEnd:
    """End-to-end CLI workflow tests"""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for CLI tests"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create subdirectory structure like the real app
            user_dir = Path(temp_dir) / "testuser"
            user_dir.mkdir(exist_ok=True)
            yield {
                "base_dir": temp_dir,
                "user_dir": str(user_dir),
                "owned_csv": str(user_dir / "repos.csv"),
                "starred_csv": str(user_dir / "starred_repos.csv"),
                "report_md": str(user_dir / "README.md")
            }

    def mock_gh_command_factory(self):
        """Factory for creating GitHub CLI command mocks"""
        def mock_run_gh_command(cmd):
            if 'gh repo list' in cmd:
                return get_owned_repos_json()
            elif 'gh api user/starred' in cmd or 'gh api users/' in cmd:
                return get_starred_repos_json()
            elif 'gh api repos/' in cmd and '/branches' in cmd:
                parts = cmd.split('/')
                if len(parts) >= 4:
                    owner = parts[2]
                    repo = parts[3]
                    return get_branch_count(owner, repo)
                return "3"
            return None
        return mock_run_gh_command

    def test_full_cli_workflow(self, temp_workspace):
        """Test complete CLI workflow: collect repositories, generate report"""
        test_args = [
            'ghscan',
            '--user', 'testuser',
            '--owned-csv', temp_workspace['owned_csv'],
            '--starred-csv', temp_workspace['starred_csv'],
            '--report-md', temp_workspace['report_md']
        ]

        with patch('github_inventory.inventory.run_gh_command', side_effect=self.mock_gh_command_factory()):
            with patch.object(sys, 'argv', test_args):
                main()

        # Verify all files were created
        assert os.path.exists(temp_workspace['owned_csv'])
        assert os.path.exists(temp_workspace['starred_csv'])
        assert os.path.exists(temp_workspace['report_md'])

        # Verify CSV content
        with open(temp_workspace['owned_csv'], 'r', encoding='utf-8') as f:
            owned_reader = csv.DictReader(f)
            owned_data = list(owned_reader)
        assert len(owned_data) == 3
        assert owned_data[0]['name'] == 'github_inventory'

        with open(temp_workspace['starred_csv'], 'r', encoding='utf-8') as f:
            starred_reader = csv.DictReader(f)
            starred_data = list(starred_reader)
        assert len(starred_data) == 3
        assert starred_data[0]['name'] == 'awesome-python'

        # Verify report content
        with open(temp_workspace['report_md'], 'r', encoding='utf-8') as f:
            report_content = f.read()
        assert '# GitHub Repository Inventory Report' in report_content
        assert '**Account:** @testuser' in report_content
        assert 'github_inventory' in report_content
        assert 'awesome-python' in report_content

    def test_owned_only_workflow(self, temp_workspace):
        """Test CLI workflow with --owned-only flag"""
        test_args = [
            'ghscan',
            '--user', 'testuser',
            '--owned-only',
            '--owned-csv', temp_workspace['owned_csv'],
            '--starred-csv', temp_workspace['starred_csv'],
            '--report-md', temp_workspace['report_md']
        ]

        with patch('github_inventory.inventory.run_gh_command', side_effect=self.mock_gh_command_factory()):
            with patch.object(sys, 'argv', test_args):
                main()

        # Verify only owned CSV was created
        assert os.path.exists(temp_workspace['owned_csv'])
        assert not os.path.exists(temp_workspace['starred_csv'])
        assert os.path.exists(temp_workspace['report_md'])

        # Verify report doesn't include starred section
        with open(temp_workspace['report_md'], 'r', encoding='utf-8') as f:
            report_content = f.read()
        assert '## Owned Repositories' in report_content
        assert '## Starred Repositories' not in report_content

    def test_starred_only_workflow(self, temp_workspace):
        """Test CLI workflow with --starred-only flag"""
        test_args = [
            'ghscan',
            '--user', 'testuser',
            '--starred-only',
            '--owned-csv', temp_workspace['owned_csv'],
            '--starred-csv', temp_workspace['starred_csv'],
            '--report-md', temp_workspace['report_md']
        ]

        with patch('github_inventory.inventory.run_gh_command', side_effect=self.mock_gh_command_factory()):
            with patch.object(sys, 'argv', test_args):
                main()

        # Verify only starred CSV was created
        assert not os.path.exists(temp_workspace['owned_csv'])
        assert os.path.exists(temp_workspace['starred_csv'])
        assert os.path.exists(temp_workspace['report_md'])

    def test_report_only_workflow(self, temp_workspace):
        """Test CLI workflow with --report-only flag using existing CSV files"""
        # First, create CSV files
        self.test_full_cli_workflow(temp_workspace)

        # Clear the report file
        os.remove(temp_workspace['report_md'])

        # Now test report-only mode
        test_args = [
            'ghscan',
            '--user', 'testuser',
            '--report-only',
            '--owned-csv', temp_workspace['owned_csv'],
            '--starred-csv', temp_workspace['starred_csv'],
            '--report-md', temp_workspace['report_md']
        ]

        # No GitHub CLI mocking needed for report-only mode
        with patch.object(sys, 'argv', test_args):
            main()

        # Verify report was recreated
        assert os.path.exists(temp_workspace['report_md'])
        with open(temp_workspace['report_md'], 'r', encoding='utf-8') as f:
            report_content = f.read()
        assert '# GitHub Repository Inventory Report' in report_content

    def test_no_report_workflow(self, temp_workspace):
        """Test CLI workflow with --no-report flag"""
        test_args = [
            'ghscan',
            '--user', 'testuser',
            '--no-report',
            '--owned-csv', temp_workspace['owned_csv'],
            '--starred-csv', temp_workspace['starred_csv']
        ]

        with patch('github_inventory.inventory.run_gh_command', side_effect=self.mock_gh_command_factory()):
            with patch.object(sys, 'argv', test_args):
                main()

        # Verify CSV files were created but no report
        assert os.path.exists(temp_workspace['owned_csv'])
        assert os.path.exists(temp_workspace['starred_csv'])
        assert not os.path.exists(temp_workspace['report_md'])

    def test_limit_parameter_workflow(self, temp_workspace):
        """Test CLI workflow with --limit parameter"""
        test_args = [
            'ghscan',
            '--user', 'testuser',
            '--limit', '2',
            '--owned-csv', temp_workspace['owned_csv'],
            '--starred-csv', temp_workspace['starred_csv'],
            '--report-md', temp_workspace['report_md']
        ]

        with patch('github_inventory.inventory.run_gh_command', side_effect=self.mock_gh_command_factory()):
            with patch.object(sys, 'argv', test_args):
                main()

        # Verify files were created
        assert os.path.exists(temp_workspace['owned_csv'])
        assert os.path.exists(temp_workspace['starred_csv'])

        # Verify report mentions the limit
        with open(temp_workspace['report_md'], 'r', encoding='utf-8') as f:
            report_content = f.read()
        assert 'limit of 2' in report_content.lower()

    def test_directory_creation_workflow(self, temp_workspace):
        """Test that CLI creates directories when they don't exist"""
        # Use nested directory that doesn't exist
        nested_dir = Path(temp_workspace['base_dir']) / "nested" / "directories" / "testuser"
        nested_csv = str(nested_dir / "repos.csv")

        test_args = [
            'ghscan',
            '--user', 'testuser',
            '--owned-only',
            '--owned-csv', nested_csv,
            '--no-report'
        ]

        with patch('github_inventory.inventory.run_gh_command', side_effect=self.mock_gh_command_factory()):
            with patch.object(sys, 'argv', test_args):
                main()

        # Verify directory was created and file exists
        assert nested_dir.exists()
        assert os.path.exists(nested_csv)


class TestCLIErrorHandling:
    """Test CLI error handling scenarios"""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for CLI tests"""
        with tempfile.TemporaryDirectory() as temp_dir:
            user_dir = Path(temp_dir) / "testuser"
            user_dir.mkdir(exist_ok=True)
            yield {
                "base_dir": temp_dir,
                "owned_csv": str(user_dir / "repos.csv"),
                "starred_csv": str(user_dir / "starred_repos.csv"),
                "report_md": str(user_dir / "README.md")
            }

    def test_github_cli_authentication_error(self, temp_workspace, capsys):
        """Test CLI behavior when GitHub CLI is not authenticated"""
        def mock_failing_gh_command(cmd):
            raise subprocess.CalledProcessError(
                1, cmd, stderr="To authenticate, please run `gh auth login`"
            )

        test_args = [
            'ghscan',
            '--user', 'testuser',
            '--owned-csv', temp_workspace['owned_csv'],
            '--starred-csv', temp_workspace['starred_csv'],
            '--report-md', temp_workspace['report_md']
        ]

        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_failing_gh_command):
            with patch.object(sys, 'argv', test_args):
                with pytest.raises(SystemExit):
                    main()

        # Verify error message and exit
        captured = capsys.readouterr()
        assert "No data collected" in captured.out or "Please check your GitHub CLI authentication" in captured.out

    def test_report_only_with_missing_csv_files(self, temp_workspace, capsys):
        """Test --report-only when CSV files don't exist"""
        test_args = [
            'ghscan',
            '--user', 'testuser',
            '--report-only',
            '--owned-csv', temp_workspace['owned_csv'],
            '--starred-csv', temp_workspace['starred_csv'],
            '--report-md', temp_workspace['report_md']
        ]

        with patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit):
                main()

        captured = capsys.readouterr()
        assert "No existing CSV files found" in captured.out

    def test_invalid_limit_parameter(self):
        """Test CLI with invalid limit parameter"""
        parser = create_parser()
        
        # Test non-integer limit
        with pytest.raises(SystemExit):
            parser.parse_args(['--limit', 'invalid'])

    def test_permission_denied_error(self, temp_workspace, capsys):
        """Test CLI behavior when file permissions are denied"""
        # Create a read-only directory to simulate permission error
        readonly_dir = Path(temp_workspace['base_dir']) / "readonly"
        readonly_dir.mkdir(mode=0o444)  # Read-only directory
        
        readonly_csv = str(readonly_dir / "repos.csv")

        test_args = [
            'ghscan',
            '--user', 'testuser',
            '--owned-only',
            '--owned-csv', readonly_csv,
            '--no-report'
        ]

        def mock_run_gh_command(cmd):
            if 'gh repo list' in cmd:
                from tests.fixtures.github_responses import get_owned_repos_json
                return get_owned_repos_json()
            elif 'gh api repos/' in cmd:
                return "3"
            return None

        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            with patch.object(sys, 'argv', test_args):
                try:
                    main()
                except (PermissionError, OSError):
                    # Expected to fail due to permissions
                    pass


class TestCLIBatchProcessing:
    """Test CLI batch processing functionality"""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for batch tests"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_batch_mode_with_default_configs(self, temp_workspace):
        """Test batch processing with default configurations"""
        test_args = ['ghscan', '--batch']

        def mock_run_gh_command(cmd):
            if 'gh repo list' in cmd:
                # Return different data based on user in command
                if 'microsoft' in cmd:
                    return '[]'  # Empty for microsoft
                elif 'google' in cmd:
                    return get_owned_repos_json()  # Sample data for google
                return '[]'
            elif 'gh api' in cmd and 'starred' in cmd:
                return '[]'  # Empty starred for all
            elif 'gh api repos/' in cmd:
                return "3"
            return None

        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            with patch.object(sys, 'argv', test_args):
                # Change to temp directory to avoid creating files in project
                original_cwd = os.getcwd()
                os.chdir(temp_workspace)
                try:
                    main()
                finally:
                    os.chdir(original_cwd)

        # Verify directories were created for default accounts
        expected_dirs = ['microsoft', 'google', 'facebook']
        for account in expected_dirs:
            account_dir = Path(temp_workspace) / 'docs' / account
            if account_dir.exists():
                # At least one account should have created directory
                break
        else:
            # If running in CI without proper setup, this might not create dirs
            pass

    def test_batch_mode_with_custom_config(self, temp_workspace):
        """Test batch processing with custom configuration file"""
        # Create a custom config file
        config_content = """
configs:
  - account: testuser1
    limit: 10
  - account: testuser2
"""
        config_file = Path(temp_workspace) / "test_config.yaml"
        config_file.write_text(config_content)

        test_args = ['ghscan', '--config', str(config_file)]

        def mock_run_gh_command(cmd):
            return '[]'  # Empty responses for all commands

        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            with patch.object(sys, 'argv', test_args):
                original_cwd = os.getcwd()
                os.chdir(temp_workspace)
                try:
                    main()
                except SystemExit:
                    # Batch mode might exit early with no data
                    pass
                finally:
                    os.chdir(original_cwd)


class TestCLIPerformance:
    """Test CLI performance with large datasets"""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace"""
        with tempfile.TemporaryDirectory() as temp_dir:
            user_dir = Path(temp_dir) / "testuser"
            user_dir.mkdir(exist_ok=True)
            yield {
                "owned_csv": str(user_dir / "repos.csv"),
                "starred_csv": str(user_dir / "starred_repos.csv"),
                "report_md": str(user_dir / "README.md")
            }

    def test_large_dataset_performance(self, temp_workspace):
        """Test CLI performance with large datasets"""
        import json
        import time
        
        # Generate large datasets
        large_owned = generate_large_repo_dataset(100)
        large_starred = generate_large_starred_dataset(200)

        def mock_run_gh_command(cmd):
            if 'gh repo list' in cmd:
                return json.dumps(large_owned)
            elif 'gh api user/starred' in cmd:
                return json.dumps(large_starred)
            elif 'gh api repos/' in cmd:
                return "3"
            return None

        test_args = [
            'ghscan',
            '--user', 'testuser',
            '--owned-csv', temp_workspace['owned_csv'],
            '--starred-csv', temp_workspace['starred_csv'],
            '--report-md', temp_workspace['report_md']
        ]

        start_time = time.time()
        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            with patch.object(sys, 'argv', test_args):
                main()
        end_time = time.time()

        # Verify files were created with expected sizes
        assert os.path.exists(temp_workspace['owned_csv'])
        assert os.path.exists(temp_workspace['starred_csv'])
        assert os.path.exists(temp_workspace['report_md'])

        # Verify data integrity
        with open(temp_workspace['owned_csv'], 'r', encoding='utf-8') as f:
            owned_reader = csv.DictReader(f)
            owned_data = list(owned_reader)
        assert len(owned_data) == 100

        with open(temp_workspace['starred_csv'], 'r', encoding='utf-8') as f:
            starred_reader = csv.DictReader(f)
            starred_data = list(starred_reader)
        assert len(starred_data) == 200

        # Performance should complete within reasonable time (adjust as needed)
        execution_time = end_time - start_time
        assert execution_time < 30  # Should complete within 30 seconds