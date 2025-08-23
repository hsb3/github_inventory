#!/usr/bin/env python3
"""
GitHub Repository Inventory Module
Uses GitHub CLI to gather comprehensive repository information
"""

import csv
import json
import shlex
import subprocess
from datetime import datetime
from typing import List, Optional, Union, Dict, Any

from .models import OwnedRepository, StarredRepository, BranchCount


def run_gh_command(cmd: Union[str, List[str]]) -> Optional[str]:
    """Run a GitHub CLI command and return the result"""
    try:
        # Use shlex.split() for security instead of shell=True
        cmd_args = shlex.split(cmd) if isinstance(cmd, str) else cmd
        result = subprocess.run(  # noqa: S603
            cmd_args, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Error: {e.stderr}")
        return None


def get_repo_list(username: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get list of all repositories for a user"""
    print("Getting repository list...")

    # Get all repos with detailed JSON output
    limit_param = f"--limit {limit}" if limit is not None else "--limit 1000"
    cmd = f'gh repo list {username} {limit_param} --json "name,description,url,isPrivate,isFork,createdAt,updatedAt,defaultBranchRef,primaryLanguage,diskUsage"'

    output = run_gh_command(cmd)
    if not output:
        return []

    try:
        repos = json.loads(output)
        print(f"Found {len(repos)} repositories")
        return repos
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return []


def get_branch_count(owner: str, repo_name: str) -> Union[int, str]:
    """Get the number of branches for a repository"""
    cmd = f'gh api repos/{owner}/{repo_name}/branches --jq "length"'
    result = run_gh_command(cmd)

    if result and result.isdigit():
        return int(result)
    else:
        return "unknown"


def format_date(date_str: Optional[str]) -> str:
    """Format ISO date string to readable format"""
    if not date_str:
        return ""
    try:
        # Parse ISO format and return just the date part
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return date_str


def collect_owned_repositories(username: str, limit: Optional[int] = None) -> List[OwnedRepository]:
    """Process all repositories and gather detailed information"""
    repos = get_repo_list(username, limit)
    if not repos:
        print("No repositories found or error occurred")
        return []

    detailed_repos = []

    for i, repo in enumerate(repos, 1):
        print(f"Processing repository {i}/{len(repos)}: {repo['name']}")

        # Get branch count
        branch_count = get_branch_count(username, repo["name"])

        # Create OwnedRepository model instance
        repo_data = OwnedRepository(
            name=repo.get("name", ""),
            description=repo.get("description") or "",
            url=repo.get("url", ""),
            visibility="private" if repo.get("isPrivate", False) else "public",
            is_fork=repo.get("isFork", False),
            creation_date=format_date(repo.get("createdAt")),
            last_update_date=format_date(repo.get("updatedAt")),
            default_branch=(
                repo.get("defaultBranchRef", {}).get("name", "")
                if repo.get("defaultBranchRef")
                else ""
            ),
            number_of_branches=branch_count,  # Keep as int or "unknown"
            primary_language=(
                repo.get("primaryLanguage", {}).get("name", "")
                if repo.get("primaryLanguage")
                else ""
            ),
            size=repo.get("diskUsage"),  # Keep as int (KB) or None
        )

        detailed_repos.append(repo_data)

    return detailed_repos


def get_starred_repos(username: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get list of all starred repositories"""
    print("Getting starred repositories...")

    # Get all starred repos with detailed JSON output - using paginate to get all
    if username:
        if limit is not None:
            cmd = f'gh api users/{username}/starred --jq ".[0:{limit}]"'
        else:
            cmd = f'gh api users/{username}/starred --paginate --jq "."'
    else:
        if limit is not None:
            cmd = f'gh api user/starred --jq ".[0:{limit}]"'
        else:
            cmd = 'gh api user/starred --paginate --jq "."'

    output = run_gh_command(cmd)
    if not output:
        return []

    try:
        # The paginated output might be multiple JSON arrays, so we need to parse each line
        starred_repos = []
        for line in output.strip().split("\n"):
            if line.strip():
                repos_batch = json.loads(line)
                if isinstance(repos_batch, list):
                    starred_repos.extend(repos_batch)
                else:
                    starred_repos.append(repos_batch)

        print(f"Found {len(starred_repos)} starred repositories")
        return starred_repos
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print(f"Raw output: {output[:500]}...")
        return []


def collect_starred_repositories(username: Optional[str] = None, limit: Optional[int] = None) -> List[StarredRepository]:
    """Process all starred repositories and gather detailed information"""
    repos = get_starred_repos(username, limit)
    if not repos:
        print("No starred repositories found or error occurred")
        return []

    detailed_repos = []

    for i, repo in enumerate(repos, 1):
        print(f"Processing starred repository {i}/{len(repos)}: {repo['full_name']}")

        # Get branch count
        branch_count = get_branch_count(
            repo.get("owner", {}).get("login", ""), repo["name"]
        )

        # Create StarredRepository model instance
        repo_data = StarredRepository(
            name=repo.get("name", ""),
            full_name=repo.get("full_name", ""),
            owner=(
                repo.get("owner", {}).get("login", "") if repo.get("owner") else ""
            ),
            description=repo.get("description") or "",
            url=repo.get("html_url", ""),
            visibility="private" if repo.get("private", False) else "public",
            is_fork=repo.get("fork", False),
            creation_date=format_date(repo.get("created_at")),
            last_update_date=format_date(repo.get("updated_at")),
            last_push_date=format_date(repo.get("pushed_at")),
            default_branch=repo.get("default_branch", ""),
            number_of_branches=branch_count,  # Keep as int or "unknown"
            primary_language=repo.get("language") or "",
            size=repo.get("size", 0),  # Size in bytes - keep as int
            stars=repo.get("stargazers_count", 0),
            forks=repo.get("forks_count", 0),
            watchers=repo.get("watchers_count", 0),
            open_issues=repo.get("open_issues_count", 0),
            license=(
                repo.get("license", {}).get("name", "") if repo.get("license") else ""
            ),
            topics=", ".join(repo.get("topics", [])) if repo.get("topics") else "",
            homepage=repo.get("homepage") or "",
            archived=repo.get("archived", False),
            disabled=repo.get("disabled", False),
        )

        detailed_repos.append(repo_data)

    return detailed_repos


def write_to_csv(repos: List[Union[OwnedRepository, StarredRepository]], filename: str, headers: Optional[List[str]] = None) -> None:
    """Write repository data to CSV file"""
    if not repos:
        print("No data to write")
        return

    if not headers:
        headers = list(repos[0].model_dump().keys())

    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        # Convert Pydantic models to dictionaries for CSV output
        for repo in repos:
            repo_dict = repo.model_dump()
            # Convert boolean values to string for CSV compatibility
            for key, value in repo_dict.items():
                if isinstance(value, bool):
                    repo_dict[key] = str(value).lower()
                elif value is None:
                    repo_dict[key] = ""
            writer.writerow(repo_dict)

    print(f"Data written to {filename}")
