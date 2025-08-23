#!/usr/bin/env python3
"""
Tests for report module
"""

import os
import tempfile
from unittest.mock import patch

import pytest

from github_inventory.report import (
    create_owned_repos_table,
    create_starred_repos_table,
    create_summary_section,
    format_number,
    generate_markdown_report,
    read_csv_data,
    truncate_description,
)


class TestCSVReading:
    """Test CSV data reading functionality"""

    def test_read_csv_data_success(self):
        """Test successful CSV reading"""
        csv_content = "name,description\nrepo1,Test repo 1\nrepo2,Test repo 2"

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv"
        ) as temp_file:
            temp_file.write(csv_content)
            temp_filename = temp_file.name

        try:
            result = read_csv_data(temp_filename)

            assert len(result) == 2
            assert result[0]["name"] == "repo1"
            assert result[1]["description"] == "Test repo 2"
        finally:
            os.unlink(temp_filename)

    def test_read_csv_data_file_not_found(self):
        """Test CSV reading when file doesn't exist"""
        result = read_csv_data("nonexistent_file.csv")
        assert result == []

    @patch("builtins.open", side_effect=Exception("Read error"))
    def test_read_csv_data_read_error(self, mock_file):
        """Test CSV reading with file read error"""
        with patch("os.path.exists", return_value=True):
            result = read_csv_data("error_file.csv")
            assert result == []


class TestDataFormatting:
    """Test data formatting functions"""

    def test_format_number_valid_integer(self):
        """Test formatting valid integer"""
        assert format_number("1234") == "1,234"
        assert format_number("1000000") == "1,000,000"

    def test_format_number_empty_values(self):
        """Test formatting empty or special values"""
        assert format_number("") == ""
        assert format_number("unknown") == "unknown"
        assert format_number(None) is None

    def test_format_number_invalid(self):
        """Test formatting invalid number"""
        assert format_number("not-a-number") == "not-a-number"

    def test_truncate_description_short(self):
        """Test truncating short description"""
        short_desc = "Short description"
        assert truncate_description(short_desc, 50) == short_desc

    def test_truncate_description_long(self):
        """Test truncating long description"""
        long_desc = "This is a very long description that should be truncated"
        result = truncate_description(long_desc, 30)
        assert len(result) <= 30
        assert result.endswith("...")

    def test_truncate_description_empty(self):
        """Test truncating empty description"""
        assert truncate_description("", 50) == ""
        assert truncate_description(None, 50) is None


class TestTableGeneration:
    """Test markdown table generation"""

    def test_create_owned_repos_table_empty(self):
        """Test owned repos table with no data"""
        result = create_owned_repos_table([])
        assert "No owned repository data found" in result

    def test_create_owned_repos_table_with_data(self):
        """Test owned repos table with sample data"""
        sample_data = [
            {
                "name": "test-repo",
                "description": "A test repository",
                "url": "https://github.com/user/test-repo",
                "visibility": "public",
                "is_fork": "false",
                "primary_language": "Python",
                "size": "1024",
                "number_of_branches": "3",
                "last_update_date": "2023-12-01",
            }
        ]

        result = create_owned_repos_table(sample_data)

        assert "## Owned Repositories" in result
        assert "**Total:** 1 repositories" in result
        assert "test-repo" in result
        assert "Python" in result
        assert "1.0" in result  # Should be formatted as MB

    def test_create_starred_repos_table_empty(self):
        """Test starred repos table with no data"""
        result = create_starred_repos_table([])
        assert "No starred repository data found" in result

    def test_create_starred_repos_table_with_data(self):
        """Test starred repos table with sample data"""
        sample_data = [
            {
                "name": "starred-repo",
                "description": "A starred repository",
                "url": "https://github.com/owner/starred-repo",
                "owner": "owner",
                "visibility": "public",
                "primary_language": "JavaScript",
                "stars": "500",
                "forks": "50",
                "archived": "false",
                "last_update_date": "2023-11-01",
            }
        ]

        result = create_starred_repos_table(sample_data)

        assert "## Starred Repositories" in result
        assert "**Total:** 1 starred repositories" in result
        assert "starred-repo" in result
        assert "JavaScript" in result
        assert "500" in result


class TestReportSections:
    """Test report section generation"""

    def test_create_summary_section(self):
        """Test summary section creation"""
        result = create_summary_section("testuser")

        assert "# GitHub Repository Inventory Report" in result
        assert "**Account:** @testuser" in result
        assert "## Methodology & Notes" in result
        assert "Displayed in MB" in result

    def test_create_summary_section_default_user(self):
        """Test summary section with default user"""
        result = create_summary_section()

        assert "**Account:** @hsb3" in result


class TestReportGeneration:
    """Test complete report generation"""

    def test_generate_markdown_report_success(self):
        """Test successful markdown report generation"""
        owned_data = [
            {
                "name": "my-repo",
                "description": "My repository",
                "url": "https://github.com/user/my-repo",
                "visibility": "public",
                "is_fork": "false",
                "primary_language": "Python",
                "size": "2048",
                "number_of_branches": "2",
                "last_update_date": "2023-12-01",
            }
        ]

        starred_data = [
            {
                "name": "cool-project",
                "owner": "someowner",
                "description": "A cool project",
                "url": "https://github.com/someowner/cool-project",
                "visibility": "public",
                "primary_language": "Go",
                "stars": "1000",
                "forks": "100",
                "archived": "false",
                "last_update_date": "2023-11-15",
            }
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".md"
        ) as temp_file:
            temp_filename = temp_file.name

        try:
            result = generate_markdown_report(
                owned_repos=owned_data,
                starred_repos=starred_data,
                username="testuser",
                output_file=temp_filename,
            )

            assert result is True

            # Verify file was created and contains expected content
            with open(temp_filename, "r", encoding="utf-8") as f:
                content = f.read()

                assert "# GitHub Repository Inventory Report" in content
                assert "**Account:** @testuser" in content
                assert "## Owned Repositories" in content
                assert "## Starred Repositories" in content
                assert "my-repo" in content
                assert "cool-project" in content
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def test_generate_markdown_report_owned_only(self):
        """Test report generation with only owned repos"""
        owned_data = [
            {
                "name": "solo-repo",
                "description": "Solo repository",
                "url": "https://github.com/user/solo-repo",
                "visibility": "private",
                "is_fork": "true",
                "primary_language": "Rust",
                "size": "512",
                "number_of_branches": "1",
                "last_update_date": "2023-10-01",
            }
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".md"
        ) as temp_file:
            temp_filename = temp_file.name

        try:
            result = generate_markdown_report(
                owned_repos=owned_data,
                starred_repos=None,
                username="testuser",
                output_file=temp_filename,
            )

            assert result is True

            # Verify file content
            with open(temp_filename, "r", encoding="utf-8") as f:
                content = f.read()

                assert "## Owned Repositories" in content
                assert "solo-repo" in content
                assert "## Starred Repositories" not in content
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    @patch("builtins.open", side_effect=Exception("Write error"))
    def test_generate_markdown_report_write_error(self, mock_file):
        """Test report generation with file write error"""
        result = generate_markdown_report(
            owned_repos=[],
            starred_repos=[],
            username="testuser",
            output_file="error_file.md",
        )

        assert result is False


@pytest.fixture
def sample_repos_data():
    """Sample repository data for testing"""
    return [
        {
            "name": "repo-a",
            "description": "Repository A with a very long description that should be truncated when displayed in tables",
            "url": "https://github.com/user/repo-a",
            "visibility": "public",
            "is_fork": "false",
            "primary_language": "Python",
            "size": "5000",
            "number_of_branches": "5",
            "last_update_date": "2023-12-01",
        },
        {
            "name": "repo-b",
            "description": "Repository B",
            "url": "https://github.com/user/repo-b",
            "visibility": "private",
            "is_fork": "true",
            "primary_language": "JavaScript",
            "size": "1500",
            "number_of_branches": "2",
            "last_update_date": "2023-11-15",
        },
    ]


class TestTableGenerationWithFixtures:
    """Test table generation with sample data fixtures"""

    def test_owned_repos_statistics(self, sample_repos_data):
        """Test statistics calculation in owned repos table"""
        result = create_owned_repos_table(sample_repos_data)

        assert "**Total:** 2 repositories" in result
        assert "**Public:** 1 | **Private:** 1" in result
        assert "**Original:** 1 | **Forks:** 1" in result
        assert "**Top Languages:** Python: 1 | JavaScript: 1" in result

    def test_owned_repos_sorting(self, sample_repos_data):
        """Test that repos are sorted by last update date"""
        result = create_owned_repos_table(sample_repos_data)

        # repo-a should appear first (more recent update: 2023-12-01)
        repo_a_pos = result.find("repo-a")
        repo_b_pos = result.find("repo-b")

        assert repo_a_pos < repo_b_pos
