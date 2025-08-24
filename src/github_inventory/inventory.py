#!/usr/bin/env python3
"""
GitHub Repository Inventory Module
Uses GitHub CLI or API to gather comprehensive repository information
"""

import csv
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from .github_client import GitHubClient, create_github_client


# Legacy function for backward compatibility
def run_gh_command(cmd):
    """Run a GitHub CLI command and return the result (legacy function)
    
    Args:
        cmd: GitHub CLI command to run (string or list of args)
        
    Returns:
        str: Command output
        
    Raises:
        GitHubCLIError: When the GitHub CLI command fails
        AuthenticationError: When authentication is required but missing
    """
    from .github_client import CLIGitHubClient
    client = CLIGitHubClient()
    return client._run_gh_command(cmd)


def get_repo_list(username: str, limit: Optional[int] = None, client: Optional[GitHubClient] = None) -> List[Dict[str, Any]]:
    """Get list of all repositories for a user

    Args:
        username: GitHub username
        limit: Maximum number of repositories to fetch
        client: GitHub client instance (defaults to CLI client)

    Returns:
        list: List of repository data dictionaries
    """
    if client is None:
        client = create_github_client("cli")
    return client.get_repositories(username, limit)


def get_branch_count(owner: str, repo_name: str, client: Optional[GitHubClient] = None) -> Union[int, str]:
    """Get the number of branches for a repository

    Args:
        owner: Repository owner username
        repo_name: Repository name
        client: GitHub client instance (defaults to CLI client)

    Returns:
        int or str: Number of branches, or "unknown" if unable to determine
    """
    if client is None:
        client = create_github_client("cli")
    return client.get_branch_count(owner, repo_name)


def format_date(date_str):
    """Format ISO date string to readable format"""
    if not date_str:
        return ""
    try:
        # Parse ISO format and return just the date part
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return date_str


def collect_owned_repositories(username: str, limit: Optional[int] = None, client: Optional[GitHubClient] = None) -> List[Dict[str, Any]]:
    """Process all repositories and gather detailed information
    
    Args:
        username: GitHub username
        limit: Maximum number of repositories to process
        client: GitHub client instance (defaults to CLI client)
        
    Returns:
        List of repository data dictionaries
    """
    if client is None:
        client = create_github_client("cli")
        
    repos = client.get_repositories(username, limit)
    if not repos:
        print("No repositories found or error occurred")
        return []

    detailed_repos = []

    for i, repo in enumerate(repos, 1):
        print(f"Processing repository {i}/{len(repos)}: {repo['name']}")

        # Get branch count
        branch_count = client.get_branch_count(username, repo["name"])

        # Extract and format data
        repo_data = {
            "name": repo.get("name", ""),
            "description": repo.get("description", ""),
            "url": repo.get("url", ""),
            "visibility": "private" if repo.get("isPrivate", False) else "public",
            "is_fork": str(repo.get("isFork", False)).lower(),
            "creation_date": format_date(repo.get("createdAt", "")),
            "last_update_date": format_date(repo.get("updatedAt", "")),
            "default_branch": (
                repo.get("defaultBranchRef", {}).get("name", "")
                if repo.get("defaultBranchRef")
                else ""
            ),
            "number_of_branches": str(branch_count),
            "primary_language": (
                repo.get("primaryLanguage", {}).get("name", "")
                if repo.get("primaryLanguage")
                else ""
            ),
            "size": str(repo.get("diskUsage", "")) if repo.get("diskUsage") else "",
        }

        detailed_repos.append(repo_data)

    return detailed_repos


def get_starred_repos(username: Optional[str] = None, limit: Optional[int] = None, client: Optional[GitHubClient] = None) -> List[Dict[str, Any]]:
    """Get list of all starred repositories

    Args:
        username: GitHub username (None for authenticated user)
        limit: Maximum number of starred repositories to fetch
        client: GitHub client instance (defaults to CLI client)

    Returns:
        list: List of starred repository data dictionaries
    """
    if client is None:
        client = create_github_client("cli")
    return client.get_starred_repositories(username, limit)


def collect_starred_repositories(username: Optional[str] = None, limit: Optional[int] = None, client: Optional[GitHubClient] = None) -> List[Dict[str, Any]]:
    """Process all starred repositories and gather detailed information
    
    Args:
        username: GitHub username (None for authenticated user)
        limit: Maximum number of starred repositories to process
        client: GitHub client instance (defaults to CLI client)
        
    Returns:
        List of starred repository data dictionaries
    """
    if client is None:
        client = create_github_client("cli")
        
    repos = client.get_starred_repositories(username, limit)
    if not repos:
        print("No starred repositories found or error occurred")
        return []

    detailed_repos = []

    for i, repo in enumerate(repos, 1):
        print(f"Processing starred repository {i}/{len(repos)}: {repo['full_name']}")

        # Get branch count
        branch_count = client.get_branch_count(
            repo.get("owner", {}).get("login", ""), repo["name"]
        )

        # Extract and format data
        repo_data = {
            "name": repo.get("name", ""),
            "full_name": repo.get("full_name", ""),
            "owner": (
                repo.get("owner", {}).get("login", "") if repo.get("owner") else ""
            ),
            "description": repo.get("description", ""),
            "url": repo.get("html_url", ""),
            "visibility": "private" if repo.get("private", False) else "public",
            "is_fork": str(repo.get("fork", False)).lower(),
            "creation_date": format_date(repo.get("created_at", "")),
            "last_update_date": format_date(repo.get("updated_at", "")),
            "last_push_date": format_date(repo.get("pushed_at", "")),
            "default_branch": repo.get("default_branch", ""),
            "number_of_branches": str(branch_count),
            "primary_language": repo.get("language", ""),
            "size": str(repo.get("size", "")),  # Size in KB
            "stars": str(repo.get("stargazers_count", 0)),
            "forks": str(repo.get("forks_count", 0)),
            "watchers": str(repo.get("watchers_count", 0)),
            "open_issues": str(repo.get("open_issues_count", 0)),
            "license": (
                repo.get("license", {}).get("name", "") if repo.get("license") else ""
            ),
            "topics": ", ".join(repo.get("topics", [])) if repo.get("topics") else "",
            "homepage": repo.get("homepage", ""),
            "archived": str(repo.get("archived", False)).lower(),
            "disabled": str(repo.get("disabled", False)).lower(),
        }

        detailed_repos.append(repo_data)

    return detailed_repos


def write_to_csv(repos, filename, headers=None):
    """Write repository data to CSV file"""
    if not repos:
        print("No data to write")
        return

    if not headers:
        headers = list(repos[0].keys())

    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        writer.writerows(repos)

    print(f"Data written to {filename}")
