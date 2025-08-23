#!/usr/bin/env python3
"""
GitHub Client Abstraction Layer
Provides interfaces for GitHub API interactions with multiple implementations
"""

import json
import shlex
import subprocess
import urllib.request
import urllib.parse
import urllib.error
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class GitHubClient(ABC):
    """Abstract base class for GitHub API clients"""

    @abstractmethod
    def get_repositories(self, username: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get list of repositories for a user"""
        pass

    @abstractmethod
    def get_starred_repositories(self, username: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get list of starred repositories"""
        pass

    @abstractmethod
    def get_branch_count(self, owner: str, repo_name: str) -> int | str:
        """Get the number of branches for a repository"""
        pass

    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check if the client is properly authenticated"""
        pass


class CLIGitHubClient(GitHubClient):
    """GitHub client implementation using GitHub CLI (gh)"""

    def _run_gh_command(self, cmd: str | List[str]) -> Optional[str]:
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

    def get_repositories(self, username: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get list of repositories for a user using GitHub CLI"""
        print("Getting repository list...")

        # Get all repos with detailed JSON output
        limit_param = f"--limit {limit}" if limit is not None else "--limit 1000"
        cmd = f'gh repo list {username} {limit_param} --json "name,description,url,isPrivate,isFork,createdAt,updatedAt,defaultBranchRef,primaryLanguage,diskUsage"'

        output = self._run_gh_command(cmd)
        if not output:
            return []

        try:
            repos = json.loads(output)
            print(f"Found {len(repos)} repositories")
            return repos
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return []

    def get_starred_repositories(self, username: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get list of starred repositories using GitHub CLI"""
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

        output = self._run_gh_command(cmd)
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

    def get_branch_count(self, owner: str, repo_name: str) -> int | str:
        """Get the number of branches for a repository using GitHub CLI"""
        cmd = f'gh api repos/{owner}/{repo_name}/branches --jq "length"'
        result = self._run_gh_command(cmd)

        if result and result.isdigit():
            return int(result)
        else:
            return "unknown"

    def is_authenticated(self) -> bool:
        """Check if GitHub CLI is authenticated"""
        try:
            result = self._run_gh_command("gh auth status")
            return result is not None
        except Exception:
            return False


class MockGitHubClient(GitHubClient):
    """Mock GitHub client for testing"""

    def __init__(self, mock_repos: List[Dict[str, Any]] = None, 
                 mock_starred: List[Dict[str, Any]] = None,
                 mock_branch_count: int = 3):
        self.mock_repos = mock_repos or []
        self.mock_starred = mock_starred or []
        self.mock_branch_count = mock_branch_count
        self.authenticated = True

    def get_repositories(self, username: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return mock repository data"""
        repos = self.mock_repos.copy()
        if limit is not None:
            repos = repos[:limit]
        return repos

    def get_starred_repositories(self, username: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return mock starred repository data"""
        starred = self.mock_starred.copy()
        if limit is not None:
            starred = starred[:limit]
        return starred

    def get_branch_count(self, owner: str, repo_name: str) -> int | str:
        """Return mock branch count"""
        return self.mock_branch_count

    def is_authenticated(self) -> bool:
        """Return mock authentication status"""
        return self.authenticated


class APIGitHubClient(GitHubClient):
    """GitHub client implementation using direct API calls"""

    def __init__(self, token: Optional[str] = None):
        """Initialize with optional GitHub token"""
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "github-inventory/0.1.0"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """Make a request to the GitHub API"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"

        try:
            request = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(request) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    return data if isinstance(data, list) else [data]
                else:
                    print(f"API request failed with status {response.status}")
                    return None
        except urllib.error.HTTPError as e:
            print(f"HTTP error {e.code}: {e.reason}")
            return None
        except urllib.error.URLError as e:
            print(f"URL error: {e.reason}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return None

    def _paginate_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Make paginated requests to get all results"""
        all_results = []
        page = 1
        per_page = 100
        
        if params is None:
            params = {}
        
        while True:
            page_params = {**params, "page": page, "per_page": per_page}
            results = self._make_request(endpoint, page_params)
            
            if not results:
                break
                
            all_results.extend(results)
            
            if limit and len(all_results) >= limit:
                all_results = all_results[:limit]
                break
                
            if len(results) < per_page:
                break
                
            page += 1
            
        return all_results

    def get_repositories(self, username: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get list of repositories for a user using direct API"""
        print("Getting repository list...")
        
        endpoint = f"users/{username}/repos"
        params = {"type": "all", "sort": "updated"}
        
        repos = self._paginate_request(endpoint, params, limit)
        
        # Transform to match CLI format
        transformed_repos = []
        for repo in repos:
            transformed_repo = {
                "name": repo.get("name", ""),
                "description": repo.get("description", ""),
                "url": repo.get("html_url", ""),
                "isPrivate": repo.get("private", False),
                "isFork": repo.get("fork", False),
                "createdAt": repo.get("created_at", ""),
                "updatedAt": repo.get("updated_at", ""),
                "defaultBranchRef": {"name": repo.get("default_branch", "")} if repo.get("default_branch") else None,
                "primaryLanguage": {"name": repo.get("language", "")} if repo.get("language") else None,
                "diskUsage": repo.get("size", 0),
            }
            transformed_repos.append(transformed_repo)
        
        print(f"Found {len(transformed_repos)} repositories")
        return transformed_repos

    def get_starred_repositories(self, username: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get list of starred repositories using direct API"""
        print("Getting starred repositories...")
        
        if username:
            endpoint = f"users/{username}/starred"
        else:
            endpoint = "user/starred"
        
        starred_repos = self._paginate_request(endpoint, None, limit)
        
        print(f"Found {len(starred_repos)} starred repositories")
        return starred_repos

    def get_branch_count(self, owner: str, repo_name: str) -> int | str:
        """Get the number of branches for a repository using direct API"""
        endpoint = f"repos/{owner}/{repo_name}/branches"
        
        try:
            branches = self._paginate_request(endpoint)
            return len(branches) if branches else "unknown"
        except Exception:
            return "unknown"

    def is_authenticated(self) -> bool:
        """Check if the API client is authenticated by testing a simple request"""
        try:
            result = self._make_request("user")
            return result is not None
        except Exception:
            return False