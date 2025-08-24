"""
Test fixtures for GitHub Inventory integration tests

This package provides realistic GitHub CLI response data and utilities
for testing the complete GitHub Inventory workflow without making
actual API calls to GitHub.

Available fixtures:
- github_responses: Realistic GitHub API response data
- Sample data for owned and starred repositories
- Large dataset generators for performance testing
- Error response patterns for failure scenario testing
"""

from .github_responses import (
    get_owned_repos_json,
    get_starred_repos_json,
    get_branch_count,
    get_error_response,
    generate_large_repo_dataset,
    generate_large_starred_dataset,
    SAMPLE_OWNED_REPOS_RESPONSE,
    SAMPLE_STARRED_REPOS_RESPONSE,
    BRANCH_COUNT_RESPONSES,
    ERROR_RESPONSES
)

__all__ = [
    'get_owned_repos_json',
    'get_starred_repos_json',
    'get_branch_count',
    'get_error_response',
    'generate_large_repo_dataset',
    'generate_large_starred_dataset',
    'SAMPLE_OWNED_REPOS_RESPONSE',
    'SAMPLE_STARRED_REPOS_RESPONSE',
    'BRANCH_COUNT_RESPONSES',
    'ERROR_RESPONSES'
]