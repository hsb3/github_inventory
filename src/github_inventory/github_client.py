#!/usr/bin/env python3
"""
GitHub Client Abstraction
Provides different implementations for accessing GitHub data
"""

import json
import os
import shlex
import subprocess
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from .exceptions import AuthenticationError, DataProcessingError, GitHubCLIError


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
    def get_branch_count(self, owner: str, repo_name: str) -> Union[int, str]:
        """Get the number of branches for a repository"""
        pass


class CLIGitHubClient(GitHubClient):
    """GitHub client using GitHub CLI (gh)"""

    def _run_gh_command(self, cmd: str) -> str:
        """Run a GitHub CLI command and return the result
        
        Args:
            cmd: GitHub CLI command to run
            
        Returns:
            str: Command output
            
        Raises:
            GitHubCLIError: When the GitHub CLI command fails
            AuthenticationError: When authentication is required but missing
        """
        try:
            # Use shlex.split() for security instead of shell=True
            cmd_args = shlex.split(cmd) if isinstance(cmd, str) else cmd
            result = subprocess.run(  # noqa: S603
                cmd_args, capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.strip() if e.stderr else ""

            # Check for common authentication errors
            if "authentication" in stderr.lower() or "login" in stderr.lower():
                raise AuthenticationError(
                    "GitHub CLI authentication required. Please run 'gh auth login'"
                ) from e

            # Raise GitHubCLIError with details
            raise GitHubCLIError(cmd, stderr, e.returncode) from e

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
            raise DataProcessingError(
                "JSON parsing of repository list", f"Failed to parse GitHub CLI output: {e}"
            ) from e

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
            raise DataProcessingError(
                "JSON parsing of starred repositories",
                f"Failed to parse GitHub CLI output: {e}\nRaw output: {output[:500]}...",
            ) from e

    def get_branch_count(self, owner: str, repo_name: str) -> Union[int, str]:
        """Get the number of branches for a repository using GitHub CLI"""
        cmd = f'gh api repos/{owner}/{repo_name}/branches --jq "length"'
        try:
            result = self._run_gh_command(cmd)
            if result and result.isdigit():
                return int(result)
            else:
                return "unknown"
        except GitHubCLIError:
            # If branch count fails, return "unknown" instead of failing completely
            # This allows the main inventory process to continue
            return "unknown"


class APIGitHubClient(GitHubClient):
    """GitHub client using direct API calls"""
    
    def __init__(self, token: Optional[str] = None):
        """Initialize API client with optional token"""
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise AuthenticationError(
                "GitHub token required for API client. Set GITHUB_TOKEN environment variable or pass token parameter."
            )

    def _make_api_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Make a GitHub API request"""
        url = f"https://api.github.com{endpoint}"
        
        if params:
            url += "?" + urllib.parse.urlencode(params)
            
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"token {self.token}")
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "github-inventory")
        
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise AuthenticationError("Invalid GitHub token or insufficient permissions") from e
            elif e.code == 404:
                return []  # User or repo not found
            else:
                raise GitHubCLIError(f"API request to {endpoint}", f"HTTP {e.code}: {e.reason}", e.code) from e
        except urllib.error.URLError as e:
            raise GitHubCLIError(f"API request to {endpoint}", f"Network error: {e.reason}", 0) from e

    def get_repositories(self, username: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get list of repositories for a user using GitHub API"""
        print("Getting repository list...")
        
        repos = []
        page = 1
        per_page = min(100, limit) if limit else 100
        
        while True:
            params = {"page": page, "per_page": per_page}
            page_repos = self._make_api_request(f"/users/{username}/repos", params)
            
            if not page_repos:
                break
                
            repos.extend(page_repos)
            
            if limit and len(repos) >= limit:
                repos = repos[:limit]
                break
                
            if len(page_repos) < per_page:
                break
                
            page += 1
            
        # Transform API response to match CLI format
        formatted_repos = []
        for repo in repos:
            formatted_repo = {
                "name": repo.get("name", ""),
                "description": repo.get("description", ""),
                "url": repo.get("html_url", ""),
                "isPrivate": repo.get("private", False),
                "isFork": repo.get("fork", False),
                "createdAt": repo.get("created_at", ""),
                "updatedAt": repo.get("updated_at", ""),
                "defaultBranchRef": {"name": repo.get("default_branch", "")} if repo.get("default_branch") else None,
                "primaryLanguage": {"name": repo.get("language", "")} if repo.get("language") else None,
                "diskUsage": repo.get("size", 0),  # Size in KB
            }
            formatted_repos.append(formatted_repo)
            
        print(f"Found {len(formatted_repos)} repositories")
        return formatted_repos

    def get_starred_repositories(self, username: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get list of starred repositories using GitHub API"""
        print("Getting starred repositories...")
        
        repos = []
        page = 1
        per_page = min(100, limit) if limit else 100
        
        endpoint = f"/users/{username}/starred" if username else "/user/starred"
        
        while True:
            params = {"page": page, "per_page": per_page}
            page_repos = self._make_api_request(endpoint, params)
            
            if not page_repos:
                break
                
            repos.extend(page_repos)
            
            if limit and len(repos) >= limit:
                repos = repos[:limit]
                break
                
            if len(page_repos) < per_page:
                break
                
            page += 1
            
        print(f"Found {len(repos)} starred repositories")
        return repos

    def get_branch_count(self, owner: str, repo_name: str) -> Union[int, str]:
        """Get the number of branches for a repository using GitHub API"""
        try:
            branches = self._make_api_request(f"/repos/{owner}/{repo_name}/branches")
            return len(branches) if isinstance(branches, list) else "unknown"
        except GitHubCLIError:
            # If branch count fails, return "unknown" instead of failing completely
            return "unknown"


class MockGitHubClient(GitHubClient):
    """Mock GitHub client for testing"""
    
    def __init__(self, repos: Optional[List[Dict[str, Any]]] = None, 
                 starred: Optional[List[Dict[str, Any]]] = None,
                 branch_count: Union[int, str] = 3):
        """Initialize mock client with test data"""
        self.repos = repos or []
        self.starred = starred or []
        self.branch_count = branch_count

    def get_repositories(self, username: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return mock repository data"""
        repos = self.repos[:limit] if limit else self.repos
        print(f"Found {len(repos)} repositories")
        return repos

    def get_starred_repositories(self, username: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return mock starred repository data"""
        starred = self.starred[:limit] if limit else self.starred
        print(f"Found {len(starred)} starred repositories")
        return starred

    def get_branch_count(self, owner: str, repo_name: str) -> Union[int, str]:
        """Return mock branch count"""
        return self.branch_count


def create_github_client(client_type: str = "cli", token: Optional[str] = None) -> GitHubClient:
    """Factory function to create GitHub clients"""
    if client_type.lower() == "cli":
        return CLIGitHubClient()
    elif client_type.lower() == "api":
        return APIGitHubClient(token)
    elif client_type.lower() == "mock":
        return MockGitHubClient()
    else:
        raise ValueError(f"Unknown client type: {client_type}")