#!/usr/bin/env python3
"""
Realistic GitHub CLI response fixtures for integration testing
"""

import json


# Sample repository data from gh repo list command
SAMPLE_OWNED_REPOS_RESPONSE = [
    {
        "name": "github_inventory",
        "description": "A comprehensive GitHub repository inventory and analysis tool",
        "url": "https://github.com/testuser/github_inventory",
        "isPrivate": False,
        "isFork": False,
        "createdAt": "2023-01-15T10:30:00Z",
        "updatedAt": "2023-12-01T15:45:00Z",
        "defaultBranchRef": {"name": "main"},
        "primaryLanguage": {"name": "Python"},
        "diskUsage": 2048
    },
    {
        "name": "test-fork",
        "description": "A forked repository for testing",
        "url": "https://github.com/testuser/test-fork",
        "isPrivate": True,
        "isFork": True,
        "createdAt": "2023-06-01T08:00:00Z",
        "updatedAt": "2023-11-15T12:30:00Z",
        "defaultBranchRef": {"name": "develop"},
        "primaryLanguage": {"name": "JavaScript"},
        "diskUsage": 512
    },
    {
        "name": "private-project",
        "description": None,  # Test null description
        "url": "https://github.com/testuser/private-project",
        "isPrivate": True,
        "isFork": False,
        "createdAt": "2023-03-10T14:20:00Z",
        "updatedAt": "2023-10-05T09:15:00Z",
        "defaultBranchRef": {"name": "master"},
        "primaryLanguage": None,  # Test null language
        "diskUsage": 128
    }
]


# Sample starred repositories response from gh api user/starred
SAMPLE_STARRED_REPOS_RESPONSE = [
    {
        "name": "awesome-python",
        "full_name": "vinta/awesome-python",
        "owner": {"login": "vinta"},
        "description": "A curated list of awesome Python frameworks, libraries, software and resources",
        "html_url": "https://github.com/vinta/awesome-python",
        "private": False,
        "fork": False,
        "created_at": "2014-06-27T21:00:06Z",
        "updated_at": "2023-12-01T10:30:00Z",
        "pushed_at": "2023-11-28T15:45:00Z",
        "default_branch": "master",
        "language": "Python",
        "size": 15420,
        "stargazers_count": 180234,
        "forks_count": 24567,
        "watchers_count": 180234,
        "open_issues_count": 45,
        "license": {"name": "Other"},
        "topics": ["awesome", "awesome-list", "python"],
        "homepage": "https://awesome-python.com/",
        "archived": False,
        "disabled": False
    },
    {
        "name": "tensorflow",
        "full_name": "tensorflow/tensorflow",
        "owner": {"login": "tensorflow"},
        "description": "An Open Source Machine Learning Framework for Everyone",
        "html_url": "https://github.com/tensorflow/tensorflow",
        "private": False,
        "fork": False,
        "created_at": "2015-11-07T01:19:31Z",
        "updated_at": "2023-12-01T20:15:00Z",
        "pushed_at": "2023-12-01T19:30:00Z",
        "default_branch": "master",
        "language": "C++",
        "size": 245678,
        "stargazers_count": 185234,
        "forks_count": 74123,
        "watchers_count": 6789,
        "open_issues_count": 2345,
        "license": {"name": "Apache License 2.0"},
        "topics": ["machine-learning", "deep-learning", "tensorflow", "python", "ml"],
        "homepage": "https://tensorflow.org",
        "archived": False,
        "disabled": False
    },
    {
        "name": "archived-project",
        "full_name": "oldorg/archived-project",
        "owner": {"login": "oldorg"},
        "description": "This project is archived",
        "html_url": "https://github.com/oldorg/archived-project",
        "private": False,
        "fork": True,
        "created_at": "2020-01-01T00:00:00Z",
        "updated_at": "2021-06-01T12:00:00Z",
        "pushed_at": "2021-05-15T10:30:00Z",
        "default_branch": "main",
        "language": "Go",
        "size": 1024,
        "stargazers_count": 42,
        "forks_count": 8,
        "watchers_count": 42,
        "open_issues_count": 0,
        "license": {"name": "MIT License"},
        "topics": [],
        "homepage": "",
        "archived": True,
        "disabled": False
    }
]


# Branch count responses for different repositories
BRANCH_COUNT_RESPONSES = {
    "testuser/github_inventory": "5",
    "testuser/test-fork": "3",
    "testuser/private-project": "1",
    "vinta/awesome-python": "12",
    "tensorflow/tensorflow": "unknown",  # Simulate API failure
    "oldorg/archived-project": "2"
}


# Error responses for testing failure scenarios
ERROR_RESPONSES = {
    "auth_required": {
        "stderr": "To authenticate, please run `gh auth login`",
        "returncode": 1
    },
    "rate_limited": {
        "stderr": "API rate limit exceeded for user",
        "returncode": 1
    },
    "repo_not_found": {
        "stderr": "Not Found",
        "returncode": 1
    },
    "network_error": {
        "stderr": "unable to connect to api.github.com",
        "returncode": 1
    }
}


def get_owned_repos_json():
    """Get JSON string of owned repositories response"""
    return json.dumps(SAMPLE_OWNED_REPOS_RESPONSE)


def get_starred_repos_json():
    """Get JSON string of starred repositories response"""
    return json.dumps(SAMPLE_STARRED_REPOS_RESPONSE)


def get_branch_count(owner, repo):
    """Get branch count for a specific repository"""
    key = f"{owner}/{repo}"
    return BRANCH_COUNT_RESPONSES.get(key, "3")  # Default to 3 branches


def get_error_response(error_type):
    """Get error response for testing failure scenarios"""
    return ERROR_RESPONSES.get(error_type, ERROR_RESPONSES["network_error"])


# Large dataset fixtures for performance testing
def generate_large_repo_dataset(count=100):
    """Generate a large dataset of repositories for performance testing"""
    repos = []
    for i in range(count):
        repo = {
            "name": f"repo-{i:04d}",
            "description": f"Test repository number {i}",
            "url": f"https://github.com/testuser/repo-{i:04d}",
            "isPrivate": i % 3 == 0,  # Every 3rd repo is private
            "isFork": i % 5 == 0,     # Every 5th repo is a fork
            "createdAt": f"2023-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}T10:00:00Z",
            "updatedAt": f"2023-{((i + 6) % 12) + 1:02d}-{(i % 28) + 1:02d}T15:30:00Z",
            "defaultBranchRef": {"name": "main" if i % 2 == 0 else "master"},
            "primaryLanguage": {"name": ["Python", "JavaScript", "Go", "Rust", "TypeScript"][i % 5]},
            "diskUsage": 1024 + (i * 10)
        }
        repos.append(repo)
    return repos


def generate_large_starred_dataset(count=500):
    """Generate a large dataset of starred repositories for performance testing"""
    starred = []
    for i in range(count):
        repo = {
            "name": f"starred-{i:04d}",
            "full_name": f"org{i % 10}/starred-{i:04d}",
            "owner": {"login": f"org{i % 10}"},
            "description": f"Starred repository number {i}",
            "html_url": f"https://github.com/org{i % 10}/starred-{i:04d}",
            "private": i % 7 == 0,  # Every 7th repo is private
            "fork": i % 4 == 0,     # Every 4th repo is a fork
            "created_at": f"2022-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}T10:00:00Z",
            "updated_at": f"2023-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}T15:30:00Z",
            "pushed_at": f"2023-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}T12:00:00Z",
            "default_branch": "main",
            "language": ["Python", "JavaScript", "Go", "Rust", "TypeScript", "C++"][i % 6],
            "size": 500 + (i * 5),
            "stargazers_count": 100 + (i * 3),
            "forks_count": 10 + (i // 5),
            "watchers_count": 50 + i,
            "open_issues_count": i % 20,
            "license": {"name": ["MIT License", "Apache License 2.0", "BSD 3-Clause", "GPL v3.0"][i % 4]},
            "topics": [f"topic{i % 5}", f"category{i % 3}"],
            "homepage": f"https://example{i % 10}.com",
            "archived": i % 50 == 0,  # Every 50th repo is archived
            "disabled": False
        }
        starred.append(repo)
    return starred