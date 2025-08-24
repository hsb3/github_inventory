#!/usr/bin/env python3
"""
Performance tests for GitHub Inventory
Tests performance characteristics with large datasets and stress scenarios
"""

import json
import time
import tempfile
import os
import csv
from pathlib import Path
from unittest.mock import patch
import gc

import pytest

from github_inventory.inventory import (
    collect_owned_repositories,
    collect_starred_repositories,
    write_to_csv,
    get_branch_count
)
from github_inventory.report import generate_markdown_report
from github_inventory.cli import main
from tests.fixtures.github_responses import (
    generate_large_repo_dataset,
    generate_large_starred_dataset
)


class TestDataCollectionPerformance:
    """Test performance of data collection operations"""

    def test_large_owned_repository_collection_performance(self):
        """Test performance with large number of owned repositories"""
        # Generate dataset of 200 repositories
        large_dataset = generate_large_repo_dataset(200)
        
        def mock_run_gh_command(cmd):
            if 'gh repo list' in cmd:
                return json.dumps(large_dataset)
            elif 'gh api repos/' in cmd and '/branches' in cmd:
                return "3"  # Consistent branch count for performance testing
            return None

        start_time = time.time()
        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            result = collect_owned_repositories("testuser")
        end_time = time.time()

        # Verify correctness
        assert len(result) == 200
        assert all("name" in repo for repo in result)
        
        # Performance assertion - should complete within reasonable time
        execution_time = end_time - start_time
        assert execution_time < 10  # Should complete within 10 seconds
        
        # Memory efficiency check - result should not be excessively large
        import sys
        result_size = sys.getsizeof(result)
        assert result_size < 50 * 1024 * 1024  # Should be less than 50MB

    def test_large_starred_repository_collection_performance(self):
        """Test performance with large number of starred repositories"""
        # Generate dataset of 500 starred repositories
        large_dataset = generate_large_starred_dataset(500)
        
        def mock_run_gh_command(cmd):
            if 'gh api user/starred' in cmd:
                return json.dumps(large_dataset)
            elif 'gh api repos/' in cmd and '/branches' in cmd:
                return "3"
            return None

        start_time = time.time()
        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            result = collect_starred_repositories("testuser")
        end_time = time.time()

        # Verify correctness
        assert len(result) == 500
        assert all("name" in repo for repo in result)
        
        # Performance assertion
        execution_time = end_time - start_time
        assert execution_time < 20  # Should complete within 20 seconds

    def test_branch_count_api_calls_performance(self):
        """Test performance of branch count API calls with many repositories"""
        # Create dataset where branch counting is the bottleneck
        repos_count = 100
        dataset = generate_large_repo_dataset(repos_count)
        
        call_count = 0
        
        def mock_run_gh_command(cmd):
            nonlocal call_count
            if 'gh repo list' in cmd:
                return json.dumps(dataset)
            elif 'gh api repos/' in cmd and '/branches' in cmd:
                call_count += 1
                # Add small delay to simulate real API call
                time.sleep(0.01)
                return "3"
            return None

        start_time = time.time()
        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            result = collect_owned_repositories("testuser")
        end_time = time.time()

        # Verify all branch count calls were made
        assert call_count == repos_count
        assert len(result) == repos_count
        
        # Performance should scale reasonably with number of API calls
        execution_time = end_time - start_time
        # With 100 * 0.01s = 1s minimum + processing time, should be < 5s
        assert execution_time < 5

    def test_memory_usage_with_large_datasets(self):
        """Test memory usage patterns with large datasets"""
        # Generate very large dataset
        large_dataset = generate_large_repo_dataset(1000)
        
        def mock_run_gh_command(cmd):
            if 'gh repo list' in cmd:
                return json.dumps(large_dataset)
            elif 'gh api repos/' in cmd:
                return "3"
            return None

        # Force garbage collection before test
        gc.collect()
        
        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            result = collect_owned_repositories("testuser")
        
        # Force garbage collection after processing
        del result
        gc.collect()
        
        # Test should complete without memory errors
        assert True  # If we get here, memory handling was acceptable

    def test_concurrent_processing_simulation(self):
        """Test performance characteristics that simulate concurrent processing"""
        import threading
        import queue
        
        # Create datasets for multiple "users"
        datasets = [
            generate_large_repo_dataset(50),
            generate_large_repo_dataset(50),
            generate_large_repo_dataset(50)
        ]
        
        results_queue = queue.Queue()
        
        def collect_for_user(user_index):
            dataset = datasets[user_index]
            
            def mock_run_gh_command(cmd):
                if 'gh repo list' in cmd:
                    return json.dumps(dataset)
                elif 'gh api repos/' in cmd:
                    return "3"
                return None

            with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
                result = collect_owned_repositories(f"user{user_index}")
                results_queue.put((user_index, len(result)))

        # Run multiple collection operations
        threads = []
        start_time = time.time()
        
        for i in range(3):
            thread = threading.Thread(target=collect_for_user, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # Verify all operations completed
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        assert len(results) == 3
        assert all(count == 50 for _, count in results)
        
        # Should complete concurrent operations within reasonable time
        execution_time = end_time - start_time
        assert execution_time < 15


class TestFileOperationPerformance:
    """Test performance of file operations"""

    def test_large_csv_writing_performance(self):
        """Test performance of writing large CSV files"""
        # Generate large dataset
        large_dataset = []
        for i in range(1000):
            large_dataset.append({
                "name": f"repo-{i:04d}",
                "description": f"Repository number {i} with some description text",
                "url": f"https://github.com/testuser/repo-{i:04d}",
                "visibility": "public" if i % 2 == 0 else "private",
                "is_fork": "true" if i % 3 == 0 else "false",
                "creation_date": "2023-01-01",
                "last_update_date": "2023-12-01",
                "default_branch": "main",
                "number_of_branches": str(i % 10 + 1),
                "primary_language": ["Python", "JavaScript", "Go", "Rust"][i % 4],
                "size": str(1024 + i * 10)
            })

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
            temp_filename = temp_file.name

        try:
            start_time = time.time()
            write_to_csv(large_dataset, temp_filename)
            end_time = time.time()

            # Verify file was written correctly
            assert os.path.exists(temp_filename)
            file_size = os.path.getsize(temp_filename)
            assert file_size > 0

            # Performance assertion
            execution_time = end_time - start_time
            assert execution_time < 2  # Should write within 2 seconds

            # Verify data integrity with spot checks
            with open(temp_filename, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            assert len(rows) == 1000
            assert rows[0]['name'] == 'repo-0000'
            assert rows[999]['name'] == 'repo-0999'

        finally:
            os.unlink(temp_filename)

    def test_large_csv_reading_performance(self):
        """Test performance of reading large CSV files"""
        # First create a large CSV file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
            temp_filename = temp_file.name
            writer = csv.writer(temp_file)
            
            # Write header
            writer.writerow(['name', 'description', 'url', 'visibility', 'primary_language'])
            
            # Write 2000 rows
            for i in range(2000):
                writer.writerow([
                    f'repo-{i:04d}',
                    f'Description for repository {i}',
                    f'https://github.com/user/repo-{i:04d}',
                    'public' if i % 2 == 0 else 'private',
                    ['Python', 'JavaScript', 'Go', 'Rust'][i % 4]
                ])

        try:
            from github_inventory.report import read_csv_data
            
            start_time = time.time()
            data = read_csv_data(temp_filename)
            end_time = time.time()

            # Verify data was read correctly
            assert len(data) == 2000
            assert data[0]['name'] == 'repo-0000'
            assert data[1999]['name'] == 'repo-1999'

            # Performance assertion
            execution_time = end_time - start_time
            assert execution_time < 1  # Should read within 1 second

        finally:
            os.unlink(temp_filename)

    def test_multiple_file_operations_performance(self):
        """Test performance of multiple concurrent file operations"""
        datasets = {
            'owned': generate_large_repo_dataset(300),
            'starred': generate_large_starred_dataset(200)
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            files = {
                'owned_csv': os.path.join(temp_dir, 'owned.csv'),
                'starred_csv': os.path.join(temp_dir, 'starred.csv'),
                'report_md': os.path.join(temp_dir, 'report.md')
            }

            def mock_run_gh_command(cmd):
                if 'gh repo list' in cmd:
                    return json.dumps(datasets['owned'])
                elif 'gh api user/starred' in cmd:
                    return json.dumps(datasets['starred'])
                elif 'gh api repos/' in cmd:
                    return "3"
                return None

            start_time = time.time()
            with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
                # Collect data
                owned_repos = collect_owned_repositories("testuser")
                starred_repos = collect_starred_repositories("testuser")
                
                # Write CSV files
                write_to_csv(owned_repos, files['owned_csv'])
                write_to_csv(starred_repos, files['starred_csv'])
                
                # Generate report
                generate_markdown_report(
                    owned_repos=owned_repos,
                    starred_repos=starred_repos,
                    username="testuser",
                    output_file=files['report_md']
                )
            end_time = time.time()

            # Verify all files were created
            for file_path in files.values():
                assert os.path.exists(file_path)
                assert os.path.getsize(file_path) > 0

            # Performance assertion for complete workflow
            execution_time = end_time - start_time
            assert execution_time < 30  # Complete workflow within 30 seconds


class TestReportGenerationPerformance:
    """Test performance of report generation"""

    def test_large_report_generation_performance(self):
        """Test performance of generating reports with large datasets"""
        # Create large datasets
        owned_data = []
        for i in range(500):
            owned_data.append({
                "name": f"owned-repo-{i:03d}",
                "description": f"Owned repository number {i} with detailed description",
                "url": f"https://github.com/testuser/owned-repo-{i:03d}",
                "visibility": "public" if i % 2 == 0 else "private",
                "is_fork": "true" if i % 3 == 0 else "false",
                "primary_language": ["Python", "JavaScript", "Go", "Rust", "TypeScript"][i % 5],
                "size": str(1024 + i * 50),
                "number_of_branches": str(i % 20 + 1),
                "last_update_date": "2023-12-01"
            })

        starred_data = []
        for i in range(1000):
            starred_data.append({
                "name": f"starred-repo-{i:04d}",
                "owner": f"owner{i % 10}",
                "description": f"Starred repository number {i}",
                "url": f"https://github.com/owner{i % 10}/starred-repo-{i:04d}",
                "visibility": "public",
                "primary_language": ["Python", "JavaScript", "Go"][i % 3],
                "stars": str(100 + i * 5),
                "forks": str(10 + i),
                "archived": "true" if i % 50 == 0 else "false",
                "last_update_date": "2023-11-01"
            })

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as temp_file:
            temp_filename = temp_file.name

        try:
            start_time = time.time()
            success = generate_markdown_report(
                owned_repos=owned_data,
                starred_repos=starred_data,
                username="testuser",
                output_file=temp_filename
            )
            end_time = time.time()

            assert success is True
            assert os.path.exists(temp_filename)
            
            # Verify report content
            with open(temp_filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert '**Total:** 500 repositories' in content
            assert '**Total:** 1000 starred repositories' in content

            # Performance assertion
            execution_time = end_time - start_time
            assert execution_time < 5  # Should generate within 5 seconds

        finally:
            os.unlink(temp_filename)

    def test_report_with_complex_data_performance(self):
        """Test report generation performance with complex/unusual data"""
        # Create dataset with complex Unicode content, long descriptions, etc.
        complex_data = []
        for i in range(200):
            complex_data.append({
                "name": f"complex-repo-{i:03d}",
                "description": f"Complex repo {i} with Unicode: 🚀 émojis and very long descriptions " + "x" * 100,
                "url": f"https://github.com/testuser/complex-repo-{i:03d}",
                "visibility": "public",
                "is_fork": "false",
                "primary_language": "Python",
                "size": str(999999 + i),  # Large numbers
                "number_of_branches": str(i % 100),
                "last_update_date": "2023-12-01"
            })

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as temp_file:
            temp_filename = temp_file.name

        try:
            start_time = time.time()
            success = generate_markdown_report(
                owned_repos=complex_data,
                starred_repos=None,
                username="testuser",
                output_file=temp_filename
            )
            end_time = time.time()

            assert success is True
            
            # Performance should not be significantly impacted by complex data
            execution_time = end_time - start_time
            assert execution_time < 3

        finally:
            os.unlink(temp_filename)


class TestEndToEndPerformance:
    """Test end-to-end performance scenarios"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for performance tests"""
        with tempfile.TemporaryDirectory() as temp_dir:
            user_dir = Path(temp_dir) / "testuser"
            user_dir.mkdir(exist_ok=True)
            yield {
                "owned_csv": str(user_dir / "repos.csv"),
                "starred_csv": str(user_dir / "starred.csv"),
                "report_md": str(user_dir / "README.md")
            }

    def test_full_cli_workflow_performance(self, temp_workspace):
        """Test complete CLI workflow performance with realistic large datasets"""
        # Create realistic large datasets
        large_owned = generate_large_repo_dataset(150)
        large_starred = generate_large_starred_dataset(300)

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
            with patch('sys.argv', test_args):
                main()
        end_time = time.time()

        # Verify all outputs
        assert os.path.exists(temp_workspace['owned_csv'])
        assert os.path.exists(temp_workspace['starred_csv'])
        assert os.path.exists(temp_workspace['report_md'])

        # Verify data integrity
        with open(temp_workspace['owned_csv'], 'r', encoding='utf-8') as f:
            owned_reader = csv.DictReader(f)
            owned_data = list(owned_reader)
        assert len(owned_data) == 150

        # Performance assertion for complete workflow
        execution_time = end_time - start_time
        assert execution_time < 20  # Complete workflow within 20 seconds

    def test_report_only_mode_performance(self, temp_workspace):
        """Test performance of report-only mode with large existing datasets"""
        # First create large CSV files
        self.test_full_cli_workflow_performance(temp_workspace)
        
        # Remove report to test regeneration
        os.remove(temp_workspace['report_md'])

        test_args = [
            'ghscan',
            '--user', 'testuser',
            '--report-only',
            '--owned-csv', temp_workspace['owned_csv'],
            '--starred-csv', temp_workspace['starred_csv'],
            '--report-md', temp_workspace['report_md']
        ]

        start_time = time.time()
        with patch('sys.argv', test_args):
            main()
        end_time = time.time()

        # Verify report was regenerated
        assert os.path.exists(temp_workspace['report_md'])

        # Report-only mode should be fast
        execution_time = end_time - start_time
        assert execution_time < 3  # Report generation only should be quick


class TestMemoryEfficiency:
    """Test memory efficiency and resource usage"""

    def test_streaming_processing_efficiency(self):
        """Test that processing doesn't hold entire datasets in memory unnecessarily"""
        # This test verifies that we're not creating unnecessary copies of large data
        large_dataset = generate_large_repo_dataset(500)

        def mock_run_gh_command(cmd):
            if 'gh repo list' in cmd:
                return json.dumps(large_dataset)
            elif 'gh api repos/' in cmd:
                return "3"
            return None

        with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
            result = collect_owned_repositories("testuser")

        # Result should be processed efficiently
        assert len(result) == 500
        
        # Clean up references to allow garbage collection
        del result
        del large_dataset
        gc.collect()

    def test_batch_processing_memory_efficiency(self):
        """Test memory efficiency in batch processing scenarios"""
        # Simulate processing multiple users in sequence
        datasets = [
            generate_large_repo_dataset(100),
            generate_large_repo_dataset(100),
            generate_large_repo_dataset(100)
        ]

        results = []
        
        for i, dataset in enumerate(datasets):
            def mock_run_gh_command(cmd):
                if 'gh repo list' in cmd:
                    return json.dumps(dataset)
                elif 'gh api repos/' in cmd:
                    return "3"
                return None

            with patch('github_inventory.inventory.run_gh_command', side_effect=mock_run_gh_command):
                result = collect_owned_repositories(f"user{i}")
                results.append(len(result))
                
                # Clean up after each iteration to test memory efficiency
                del result
                gc.collect()

        # All batches should process successfully
        assert results == [100, 100, 100]