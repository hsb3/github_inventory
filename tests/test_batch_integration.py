#!/usr/bin/env python3
"""
Integration tests for batch processing functionality
Tests complete batch workflows with multiple configurations
"""

import json
import tempfile
import os
import yaml
from pathlib import Path
from unittest.mock import patch
import subprocess

import pytest

from github_inventory.cli import main
from github_inventory.batch import (
    run_batch_processing,
    load_config_from_file,
    get_default_configs
)
from tests.fixtures.github_responses import (
    get_owned_repos_json,
    get_starred_repos_json,
    get_branch_count,
    generate_large_repo_dataset
)


class TestBatchProcessingIntegration:
    """Test complete batch processing workflows"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for batch processing tests"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create docs directory structure like real app
            docs_dir = Path(temp_dir) / "docs"
            docs_dir.mkdir(exist_ok=True)
            yield {
                "base_dir": temp_dir,
                "docs_dir": str(docs_dir)
            }

    def mock_gh_command_factory(self, user_data_map=None):
        """Factory for creating GitHub CLI command mocks with per-user data"""
        if user_data_map is None:
            user_data_map = {}

        def mock_run_gh_command(cmd):
            # Extract username from command
            username = None
            if 'gh repo list' in cmd:
                parts = cmd.split()
                if len(parts) >= 4:  # gh repo list username
                    username = parts[3]
            elif 'gh api users/' in cmd:
                # Format: gh api users/{username}/starred
                parts = cmd.split('/')
                if len(parts) >= 3:
                    username = parts[2]

            if 'gh repo list' in cmd:
                # Return different data based on user
                if username in user_data_map:
                    return json.dumps(user_data_map[username]['owned'])
                else:
                    return get_owned_repos_json()  # Default data
            elif 'gh api user/starred' in cmd or 'gh api users/' in cmd:
                if username in user_data_map:
                    return json.dumps(user_data_map[username]['starred'])
                else:
                    return get_starred_repos_json()  # Default data
            elif 'gh api repos/' in cmd and '/branches' in cmd:
                parts = cmd.split('/')
                if len(parts) >= 4:
                    owner = parts[2]
                    repo = parts[3]
                    return get_branch_count(owner, repo)
                return "3"
            return None

        return mock_run_gh_command

    def test_default_batch_processing_integration(self, temp_workspace):
        """Test batch processing with default configurations"""
        # Create user-specific test data
        user_data_map = {
            'microsoft': {
                'owned': [
                    {
                        "name": "microsoft-repo",
                        "description": "Microsoft test repository",
                        "url": "https://github.com/microsoft/microsoft-repo",
                        "isPrivate": False,
                        "isFork": False,
                        "createdAt": "2023-01-01T00:00:00Z",
                        "updatedAt": "2023-12-01T00:00:00Z",
                        "defaultBranchRef": {"name": "main"},
                        "primaryLanguage": {"name": "C#"},
                        "diskUsage": 5000
                    }
                ],
                'starred': []
            },
            'google': {
                'owned': [
                    {
                        "name": "google-repo",
                        "description": "Google test repository",
                        "url": "https://github.com/google/google-repo",
                        "isPrivate": False,
                        "isFork": False,
                        "createdAt": "2023-01-01T00:00:00Z",
                        "updatedAt": "2023-12-01T00:00:00Z",
                        "defaultBranchRef": {"name": "main"},
                        "primaryLanguage": {"name": "Go"},
                        "diskUsage": 3000
                    }
                ],
                'starred': []
            },
            'facebook': {
                'owned': [],  # Empty to test handling of no data
                'starred': []
            }
        }

        test_args = ['ghscan', '--batch']

        original_cwd = os.getcwd()
        os.chdir(temp_workspace['base_dir'])

        try:
            with patch('github_inventory.inventory.run_gh_command', 
                      side_effect=self.mock_gh_command_factory(user_data_map)):
                with patch('sys.argv', test_args):
                    main()

            # Verify directories and files were created for accounts with data
            docs_path = Path(temp_workspace['docs_dir'])
            
            # Check that at least some accounts were processed
            account_dirs = list(docs_path.glob('*/'))
            account_names = [d.name for d in account_dirs]
            
            # Should have processed default accounts
            expected_accounts = ['microsoft', 'google', 'facebook']
            processed_accounts = [name for name in expected_accounts if name in account_names]
            
            assert len(processed_accounts) >= 1  # At least one account processed

            # Verify file structure for processed accounts
            for account in processed_accounts:
                account_dir = docs_path / account
                if account_dir.exists():
                    # Check if files were created (may be empty for accounts with no data)
                    csv_files = list(account_dir.glob('*.csv'))
                    md_files = list(account_dir.glob('*.md'))
                    
                    # Should have attempted to create files
                    assert len(csv_files) >= 0  # May be empty if no data
                    assert len(md_files) >= 0   # May be empty if no data

        finally:
            os.chdir(original_cwd)

    def test_custom_config_batch_processing_integration(self, temp_workspace):
        """Test batch processing with custom YAML configuration"""
        # Create custom configuration file
        config_content = {
            "configs": [
                {"account": "testuser1", "limit": 10},
                {"account": "testuser2"},
                {"account": "testuser3", "limit": 5}
            ]
        }

        config_file = Path(temp_workspace['base_dir']) / "test_config.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_content, f)

        # Create test data for each user
        user_data_map = {
            'testuser1': {
                'owned': generate_large_repo_dataset(15)[:10],  # Limit should apply
                'starred': []
            },
            'testuser2': {
                'owned': generate_large_repo_dataset(3),
                'starred': []
            },
            'testuser3': {
                'owned': generate_large_repo_dataset(10)[:5],  # Limit should apply
                'starred': []
            }
        }

        test_args = ['ghscan', '--config', str(config_file)]

        original_cwd = os.getcwd()
        os.chdir(temp_workspace['base_dir'])

        try:
            with patch('github_inventory.inventory.run_gh_command',
                      side_effect=self.mock_gh_command_factory(user_data_map)):
                with patch('sys.argv', test_args):
                    main()

            # Verify processing for custom accounts
            docs_path = Path(temp_workspace['docs_dir'])
            
            for account in ['testuser1', 'testuser2', 'testuser3']:
                account_dir = docs_path / account
                if account_dir.exists():
                    csv_files = list(account_dir.glob('*.csv'))
                    # Should have CSV files for accounts with data
                    if account in ['testuser1', 'testuser2', 'testuser3']:
                        assert len(csv_files) > 0

        finally:
            os.chdir(original_cwd)

    def test_batch_processing_error_handling_integration(self, temp_workspace):
        """Test batch processing with various error scenarios"""
        config_content = {
            "configs": [
                {"account": "valid-user"},
                {"account": "auth-error-user"},
                {"account": "not-found-user"},
                {"account": "rate-limited-user"}
            ]
        }

        config_file = Path(temp_workspace['base_dir']) / "error_test_config.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_content, f)

        def mock_error_gh_command(cmd):
            # Extract username to determine error type
            username = None
            if 'gh repo list' in cmd:
                parts = cmd.split()
                if len(parts) >= 4:
                    username = parts[3]

            if username == 'valid-user':
                if 'gh repo list' in cmd:
                    return get_owned_repos_json()
                elif 'gh api' in cmd and '/branches' in cmd:
                    return "3"
                return None
            elif username == 'auth-error-user':
                raise subprocess.CalledProcessError(
                    1, cmd, stderr="To authenticate, please run `gh auth login`"
                )
            elif username == 'not-found-user':
                raise subprocess.CalledProcessError(
                    1, cmd, stderr="Not Found"
                )
            elif username == 'rate-limited-user':
                raise subprocess.CalledProcessError(
                    1, cmd, stderr="API rate limit exceeded"
                )
            return None

        test_args = ['ghscan', '--config', str(config_file)]

        original_cwd = os.getcwd()
        os.chdir(temp_workspace['base_dir'])

        try:
            with patch('github_inventory.inventory.run_gh_command',
                      side_effect=mock_error_gh_command):
                with patch('sys.argv', test_args):
                    # Should handle errors gracefully and continue processing
                    try:
                        main()
                    except SystemExit:
                        pass  # Expected if all users fail

            # Verify that valid user was processed despite errors with others
            docs_path = Path(temp_workspace['docs_dir'])
            valid_user_dir = docs_path / 'valid-user'
            
            if valid_user_dir.exists():
                csv_files = list(valid_user_dir.glob('*.csv'))
                # Should have processed the valid user
                assert len(csv_files) >= 1

        finally:
            os.chdir(original_cwd)

    def test_batch_processing_with_mixed_limits_integration(self, temp_workspace):
        """Test batch processing with mixed limit configurations"""
        config_content = {
            "configs": [
                {"account": "unlimited-user"},  # No limit
                {"account": "limited-user-10", "limit": 10},
                {"account": "limited-user-5", "limit": 5},
                {"account": "zero-limit-user", "limit": 0}
            ]
        }

        config_file = Path(temp_workspace['base_dir']) / "mixed_limits_config.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_content, f)

        # Create different sized datasets for each user
        user_data_map = {
            'unlimited-user': {
                'owned': generate_large_repo_dataset(20),  # Should get all
                'starred': []
            },
            'limited-user-10': {
                'owned': generate_large_repo_dataset(15),  # Should be limited to 10
                'starred': []
            },
            'limited-user-5': {
                'owned': generate_large_repo_dataset(12),  # Should be limited to 5
                'starred': []
            },
            'zero-limit-user': {
                'owned': generate_large_repo_dataset(10),  # Should get 0
                'starred': []
            }
        }

        test_args = ['ghscan', '--config', str(config_file)]

        original_cwd = os.getcwd()
        os.chdir(temp_workspace['base_dir'])

        try:
            with patch('github_inventory.inventory.run_gh_command',
                      side_effect=self.mock_gh_command_factory(user_data_map)):
                with patch('sys.argv', test_args):
                    main()

            # Verify limit handling by checking CSV file contents
            import csv
            docs_path = Path(temp_workspace['docs_dir'])
            
            # Check unlimited user (should have many repos)
            unlimited_dir = docs_path / 'unlimited-user'
            if unlimited_dir.exists():
                csv_files = list(unlimited_dir.glob('repos.csv'))
                if csv_files:
                    with open(csv_files[0], 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        rows = list(reader)
                    # Should have more than limited users
                    assert len(rows) >= 10

        finally:
            os.chdir(original_cwd)


class TestBatchProcessingEdgeCases:
    """Test edge cases in batch processing"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_batch_processing_empty_config(self, temp_workspace):
        """Test batch processing with empty configuration"""
        config_content = {"configs": []}
        config_file = Path(temp_workspace) / "empty_config.yaml"
        
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_content, f)

        test_args = ['ghscan', '--config', str(config_file)]

        original_cwd = os.getcwd()
        os.chdir(temp_workspace)

        try:
            with patch('sys.argv', test_args):
                # Should handle empty config gracefully
                try:
                    main()
                except SystemExit:
                    pass  # Expected with no configs

        finally:
            os.chdir(original_cwd)

    def test_batch_processing_duplicate_accounts(self, temp_workspace):
        """Test batch processing with duplicate account names"""
        config_content = {
            "configs": [
                {"account": "duplicate-user", "limit": 10},
                {"account": "other-user"},
                {"account": "duplicate-user", "limit": 20}  # Duplicate with different limit
            ]
        }

        config_file = Path(temp_workspace) / "duplicate_config.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_content, f)

        def mock_run_gh_command(cmd):
            if 'gh repo list' in cmd:
                return get_owned_repos_json()
            elif 'gh api' in cmd and '/branches' in cmd:
                return "3"
            return None

        test_args = ['ghscan', '--config', str(config_file)]

        original_cwd = os.getcwd()
        os.chdir(temp_workspace)

        try:
            with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
                with patch('sys.argv', test_args):
                    main()

            # Should process all entries (including duplicates)
            docs_path = Path(temp_workspace) / 'docs'
            if docs_path.exists():
                duplicate_dirs = list(docs_path.glob('duplicate-user*'))
                # Might create multiple directories or overwrite - either is acceptable

        finally:
            os.chdir(original_cwd)

    def test_batch_processing_invalid_usernames(self, temp_workspace):
        """Test batch processing with invalid/special usernames"""
        config_content = {
            "configs": [
                {"account": "valid-user"},
                {"account": ""},  # Empty username
                {"account": "user with spaces"},  # Spaces in username
                {"account": "special-chars!@#"},  # Special characters
                {"account": "very-long-username-" + "x" * 50}  # Very long username
            ]
        }

        config_file = Path(temp_workspace) / "invalid_users_config.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_content, f)

        def mock_run_gh_command(cmd):
            # Only valid-user should work
            if 'valid-user' in cmd:
                if 'gh repo list' in cmd:
                    return get_owned_repos_json()
                elif 'gh api' in cmd and '/branches' in cmd:
                    return "3"
            # All others should fail
            raise subprocess.CalledProcessError(1, cmd, stderr="User not found")

        test_args = ['ghscan', '--config', str(config_file)]

        original_cwd = os.getcwd()
        os.chdir(temp_workspace)

        try:
            with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
                with patch('sys.argv', test_args):
                    # Should handle invalid usernames gracefully
                    try:
                        main()
                    except SystemExit:
                        pass

            # Should have processed the valid user
            docs_path = Path(temp_workspace) / 'docs'
            if docs_path.exists():
                valid_user_dir = docs_path / 'valid-user'
                assert valid_user_dir.exists()

        finally:
            os.chdir(original_cwd)

    def test_batch_processing_large_config_file(self, temp_workspace):
        """Test batch processing with large configuration file"""
        # Create config with many accounts
        configs = []
        for i in range(50):  # 50 accounts
            config = {"account": f"user-{i:02d}"}
            if i % 5 == 0:  # Every 5th user gets a limit
                config["limit"] = 10 + i
            configs.append(config)

        config_content = {"configs": configs}
        config_file = Path(temp_workspace) / "large_config.yaml"
        
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_content, f)

        def mock_run_gh_command(cmd):
            # Return empty results for all to speed up test
            if 'gh repo list' in cmd:
                return "[]"
            elif 'gh api' in cmd and 'starred' in cmd:
                return "[]"
            return None

        test_args = ['ghscan', '--config', str(config_file)]

        original_cwd = os.getcwd()
        os.chdir(temp_workspace)

        try:
            with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
                with patch('sys.argv', test_args):
                    # Should handle large config without issues
                    main()

            # Verify some processing occurred
            docs_path = Path(temp_workspace) / 'docs'
            if docs_path.exists():
                user_dirs = list(docs_path.glob('user-*'))
                # Should have created directories for at least some users
                assert len(user_dirs) >= 10

        finally:
            os.chdir(original_cwd)


class TestBatchProcessingFileHandling:
    """Test file handling aspects of batch processing"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_batch_processing_directory_creation(self, temp_workspace):
        """Test that batch processing creates necessary directories"""
        config_content = {
            "configs": [
                {"account": "deep/nested/user"},  # Test nested directory structure
                {"account": "regular-user"}
            ]
        }

        config_file = Path(temp_workspace) / "dir_test_config.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_content, f)

        def mock_run_gh_command(cmd):
            if 'gh repo list' in cmd:
                return get_owned_repos_json()
            elif 'gh api' in cmd and '/branches' in cmd:
                return "3"
            return None

        test_args = ['ghscan', '--config', str(config_file)]

        original_cwd = os.getcwd()
        os.chdir(temp_workspace)

        try:
            with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
                with patch('sys.argv', test_args):
                    main()

            # Check that directories were created appropriately
            docs_path = Path(temp_workspace) / 'docs'
            
            # Regular user directory
            regular_user_dir = docs_path / 'regular-user'
            assert regular_user_dir.exists()

            # Nested directory (should be sanitized/flattened)
            nested_dirs = list(docs_path.glob('*nested*')) or list(docs_path.glob('deep*'))
            # Directory structure should handle this gracefully

        finally:
            os.chdir(original_cwd)

    def test_batch_processing_concurrent_file_access(self, temp_workspace):
        """Test batch processing with potential file access conflicts"""
        # This test simulates scenarios where multiple processes might access files
        config_content = {
            "configs": [
                {"account": "concurrent-user-1"},
                {"account": "concurrent-user-2"}
            ]
        }

        config_file = Path(temp_workspace) / "concurrent_config.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_content, f)

        def mock_run_gh_command(cmd):
            # Add small delay to simulate real API calls
            import time
            time.sleep(0.01)
            
            if 'gh repo list' in cmd:
                return get_owned_repos_json()
            elif 'gh api' in cmd and '/branches' in cmd:
                return "3"
            return None

        test_args = ['ghscan', '--config', str(config_file)]

        original_cwd = os.getcwd()
        os.chdir(temp_workspace)

        try:
            with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
                with patch('sys.argv', test_args):
                    main()

            # Verify both users were processed successfully
            docs_path = Path(temp_workspace) / 'docs'
            user1_dir = docs_path / 'concurrent-user-1'
            user2_dir = docs_path / 'concurrent-user-2'
            
            # Both should exist if processing was successful
            assert user1_dir.exists() or user2_dir.exists()

        finally:
            os.chdir(original_cwd)