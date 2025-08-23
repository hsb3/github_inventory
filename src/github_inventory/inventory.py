#!/usr/bin/env python3
"""
GitHub Repository Inventory Module
Uses GitHub CLI to gather comprehensive repository information
Optimized with GraphQL batching, rate limiting, and parallel processing
"""

import csv
import json
import shlex
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple


def run_gh_command(cmd: str, retries: int = 3, backoff_factor: float = 1.0) -> Optional[str]:
    """Run a GitHub CLI command with exponential backoff retry logic"""
    for attempt in range(retries):
        try:
            # Use shlex.split() for security instead of shell=True
            cmd_args = shlex.split(cmd) if isinstance(cmd, str) else cmd
            result = subprocess.run(  # noqa: S603
                cmd_args, capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            if "rate limit" in e.stderr.lower() or "api rate limit" in e.stderr.lower():
                if attempt < retries - 1:
                    wait_time = backoff_factor * (2 ** attempt)
                    print(f"Rate limit hit, waiting {wait_time:.1f}s before retry {attempt + 1}/{retries}")
                    time.sleep(wait_time)
                    continue
            
            if attempt == retries - 1:  # Last attempt
                print(f"Error running command after {retries} attempts: {cmd}")
                print(f"Error: {e.stderr}")
            return None
    return None


def get_repo_list(username, limit=None):
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


@lru_cache(maxsize=1000)
def get_branch_count_cached(owner: str, repo_name: str) -> Any:
    """Get the number of branches for a repository with caching"""
    cmd = f'gh api repos/{owner}/{repo_name}/branches --jq "length"'
    result = run_gh_command(cmd)

    if result and result.isdigit():
        return int(result)
    else:
        return "unknown"


def get_repositories_with_branches_graphql(owner: str, repo_names: List[str], max_batch_size: int = 10) -> Dict[str, Any]:
    """Get repository data including branch counts using GraphQL batching"""
    results = {}
    
    # Process repositories in batches to avoid GraphQL query size limits
    for i in range(0, len(repo_names), max_batch_size):
        batch = repo_names[i:i + max_batch_size]
        batch_results = _fetch_repo_batch_graphql(owner, batch)
        results.update(batch_results)
        
        # Add a small delay between batches to be respectful to the API
        if i + max_batch_size < len(repo_names):
            time.sleep(0.1)
    
    return results


def _fetch_repo_batch_graphql(owner: str, repo_names: List[str]) -> Dict[str, Any]:
    """Fetch a batch of repositories with branch counts using GraphQL"""
    # Build GraphQL query for multiple repositories
    query_parts = []
    for i, repo_name in enumerate(repo_names):
        alias = f"repo{i}"
        query_parts.append(f'''
        {alias}: repository(owner: "{owner}", name: "{repo_name}") {{
            name
            refs(refPrefix: "refs/heads/", first: 100) {{
                totalCount
            }}
        }}''')
    
    query = f'''
    query {{
        {chr(10).join(query_parts)}
    }}
    '''
    
    # Execute GraphQL query
    cmd = f'gh api graphql --raw-field query={shlex.quote(query)}'
    result = run_gh_command(cmd)
    
    branch_counts = {}
    if result:
        try:
            data = json.loads(result)
            if "data" in data:
                for i, repo_name in enumerate(repo_names):
                    alias = f"repo{i}"
                    if alias in data["data"] and data["data"][alias]:
                        branch_count = data["data"][alias]["refs"]["totalCount"]
                        branch_counts[repo_name] = branch_count
                    else:
                        branch_counts[repo_name] = "unknown"
            else:
                print(f"GraphQL query failed: {data.get('errors', 'Unknown error')}")
                # Fallback to individual API calls
                for repo_name in repo_names:
                    branch_counts[repo_name] = get_branch_count_cached(owner, repo_name)
        except json.JSONDecodeError:
            print("Failed to parse GraphQL response, falling back to individual calls")
            # Fallback to individual API calls
            for repo_name in repo_names:
                branch_counts[repo_name] = get_branch_count_cached(owner, repo_name)
    else:
        # Fallback to individual API calls
        for repo_name in repo_names:
            branch_counts[repo_name] = get_branch_count_cached(owner, repo_name)
    
    return branch_counts


def get_branch_count_parallel(repo_data_list: List[Tuple[str, str]], max_workers: int = 5) -> Dict[str, Any]:
    """Get branch counts for multiple repositories in parallel"""
    branch_counts = {}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit tasks
        future_to_repo = {
            executor.submit(get_branch_count_cached, owner, repo_name): (owner, repo_name)
            for owner, repo_name in repo_data_list
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_repo):
            owner, repo_name = future_to_repo[future]
            try:
                branch_count = future.result()
                branch_counts[f"{owner}/{repo_name}"] = branch_count
            except Exception as e:
                print(f"Error getting branch count for {owner}/{repo_name}: {e}")
                branch_counts[f"{owner}/{repo_name}"] = "unknown"
    
    return branch_counts


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


def collect_owned_repositories(username: str, limit: Optional[int] = None, use_parallel: bool = True) -> List[Dict[str, Any]]:
    """Process all repositories and gather detailed information with optimizations"""
    repos = get_repo_list(username, limit)
    if not repos:
        print("No repositories found or error occurred")
        return []

    print(f"Collecting branch counts for {len(repos)} repositories...")
    
    # Get branch counts efficiently
    if use_parallel and len(repos) > 10:
        # Use GraphQL batching for better performance on large repo sets
        repo_names = [repo["name"] for repo in repos]
        print("Using GraphQL batching for optimal performance...")
        branch_counts = get_repositories_with_branches_graphql(username, repo_names)
    else:
        # Use parallel processing for smaller sets
        repo_data_list = [(username, repo["name"]) for repo in repos]
        print("Using parallel processing for branch counts...")
        branch_counts = get_branch_count_parallel(repo_data_list)
    
    detailed_repos = []
    print("\nProcessing repository data...")
    
    for i, repo in enumerate(repos, 1):
        if i % 10 == 0 or i == len(repos):
            print(f"Processing repository {i}/{len(repos)}: {repo['name']}")

        # Get branch count from our batch results
        repo_key = repo["name"] if use_parallel and len(repos) > 10 else f"{username}/{repo['name']}"
        branch_count = branch_counts.get(repo_key, "unknown")

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


def get_starred_repos(username=None, limit=None):
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


def collect_starred_repositories(username: Optional[str] = None, limit: Optional[int] = None, use_parallel: bool = True) -> List[Dict[str, Any]]:
    """Process all starred repositories and gather detailed information with optimizations"""
    repos = get_starred_repos(username, limit)
    if not repos:
        print("No starred repositories found or error occurred")
        return []

    print(f"Collecting branch counts for {len(repos)} starred repositories...")
    
    # Group repositories by owner for efficient GraphQL batching
    repos_by_owner: Dict[str, List[str]] = {}
    for repo in repos:
        owner = repo.get("owner", {}).get("login", "")
        if owner:
            if owner not in repos_by_owner:
                repos_by_owner[owner] = []
            repos_by_owner[owner].append(repo["name"])
    
    # Get branch counts efficiently
    all_branch_counts = {}
    if use_parallel and len(repos) > 10:
        print("Using GraphQL batching for starred repositories...")
        # Use GraphQL batching per owner
        for owner, repo_names in repos_by_owner.items():
            owner_branch_counts = get_repositories_with_branches_graphql(owner, repo_names)
            # Convert to full_name format for lookup
            for repo_name, count in owner_branch_counts.items():
                all_branch_counts[f"{owner}/{repo_name}"] = count
    else:
        # Use parallel processing
        print("Using parallel processing for starred repository branch counts...")
        repo_data_list = [(repo.get("owner", {}).get("login", ""), repo["name"]) for repo in repos]
        all_branch_counts = get_branch_count_parallel(repo_data_list)
    
    detailed_repos = []
    print("\nProcessing starred repository data...")
    
    for i, repo in enumerate(repos, 1):
        if i % 10 == 0 or i == len(repos):
            print(f"Processing starred repository {i}/{len(repos)}: {repo['full_name']}")

        # Get branch count from our batch results
        owner = repo.get("owner", {}).get("login", "")
        repo_name = repo["name"]
        repo_key = repo_name if (use_parallel and len(repos) > 10 and owner) else f"{owner}/{repo_name}"
        
        if use_parallel and len(repos) > 10:
            branch_count = all_branch_counts.get(repo_name, "unknown")
        else:
            branch_count = all_branch_counts.get(repo_key, "unknown")

        # Extract and format data
        repo_data = {
            "name": repo.get("name", ""),
            "full_name": repo.get("full_name", ""),
            "owner": owner,
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
