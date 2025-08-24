#!/usr/bin/env python3
"""
GitHub Client Abstraction Layer
Provides different implementations for accessing GitHub API
"""

import shlex
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union

from .exceptions import AuthenticationError, GitHubCLIError


class GitHubClient(ABC):
    """Abstract base class for GitHub API clients"""

    @abstractmethod
    def run_command(self, cmd: Union[str, List[str]]) -> str:
        """Run a GitHub command and return the result"""
        pass

    @abstractmethod
    def api_request(self, endpoint: str, method: str = "GET") -> str:
        """Make a direct API request to GitHub"""
        pass


class CLIGitHubClient(GitHubClient):
    """GitHub client that uses GitHub CLI subprocess calls"""

    def run_command(self, cmd: Union[str, List[str]]) -> str:
        """Run a GitHub CLI command and return the result

        Args:
            cmd: GitHub CLI command to run (string or list of args)

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
            cmd_str = cmd if isinstance(cmd, str) else " ".join(cmd)
            raise GitHubCLIError(cmd_str, stderr, e.returncode) from e

    def api_request(self, endpoint: str, method: str = "GET") -> str:
        """Make a direct API request via GitHub CLI

        Args:
            endpoint: API endpoint (e.g., 'repos/owner/repo/branches')
            method: HTTP method (default: GET)

        Returns:
            str: API response as JSON string
        """
        cmd = f"gh api {endpoint}"
        if method != "GET":
            cmd += f" --method {method}"
        return self.run_command(cmd)


class APIGitHubClient(GitHubClient):
    """GitHub client that makes direct API requests using urllib"""

    def __init__(self, token: str):
        """Initialize with GitHub token

        Args:
            token: GitHub personal access token
        """
        self.token = token
        self.base_url = "https://api.github.com"

    def run_command(self, cmd: Union[str, List[str]]) -> str:
        """Run a GitHub command by translating to API calls

        This method attempts to translate common gh CLI commands to API calls.
        For complex commands, it raises NotImplementedError.

        Args:
            cmd: GitHub CLI command to translate

        Returns:
            str: API response

        Raises:
            NotImplementedError: For commands that can't be translated
        """
        cmd_str = cmd if isinstance(cmd, str) else " ".join(cmd)

        # Handle common gh CLI patterns
        if cmd_str.startswith("gh repo list"):
            # Extract username from command
            parts = cmd_str.split()
            if len(parts) >= 4:
                username = parts[3]
                return self.api_request(f"users/{username}/repos")
        elif cmd_str.startswith("gh api"):
            # Direct API call
            endpoint = cmd_str.split("gh api", 1)[1].strip()
            # Remove any flags for simplicity
            endpoint = endpoint.split(" --")[0]
            return self.api_request(endpoint)

        raise NotImplementedError(f"Command translation not implemented: {cmd_str}")

    def api_request(self, endpoint: str, method: str = "GET") -> str:
        """Make a direct API request to GitHub

        Args:
            endpoint: API endpoint (e.g., 'repos/owner/repo/branches')
            method: HTTP method (default: GET)

        Returns:
            str: API response as JSON string

        Raises:
            AuthenticationError: When authentication fails
            GitHubCLIError: When API request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        request = urllib.request.Request(url, method=method)  # noqa: S310
        request.add_header("Authorization", f"token {self.token}")
        request.add_header("Accept", "application/vnd.github.v3+json")
        request.add_header("User-Agent", "github-inventory-cli")

        try:
            with urllib.request.urlopen(request) as response:  # noqa: S310
                return str(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise AuthenticationError(
                    "GitHub API authentication failed. Check your token."
                ) from e
            elif e.code == 403:
                raise AuthenticationError(
                    "GitHub API access forbidden. Check token permissions."
                ) from e
            else:
                error_body = e.read().decode("utf-8") if e.fp else ""
                raise GitHubCLIError(f"API {endpoint}", error_body, e.code) from e
        except urllib.error.URLError as e:
            raise GitHubCLIError(f"API {endpoint}", str(e), -1) from e


class MockGitHubClient(GitHubClient):
    """Mock GitHub client for testing"""

    def __init__(self):
        self.responses: Dict[str, str] = {}
        self.call_history: List[str] = []

    def set_response(self, cmd_pattern: str, response: str):
        """Set a mock response for a command pattern"""
        self.responses[cmd_pattern] = response

    def run_command(self, cmd: Union[str, List[str]]) -> str:
        """Return mock response for command"""
        cmd_str = cmd if isinstance(cmd, str) else " ".join(cmd)
        self.call_history.append(cmd_str)

        # Find matching response pattern
        for pattern, response in self.responses.items():
            if pattern in cmd_str:
                return response

        # Default empty response
        return ""

    def api_request(self, endpoint: str, method: str = "GET") -> str:
        """Return mock response for API request"""
        api_cmd = f"gh api {endpoint}"
        return self.run_command(api_cmd)


def create_github_client(
    client_type: str = "cli", github_token: Optional[str] = None
) -> GitHubClient:
    """Factory function to create GitHub client

    Args:
        client_type: Type of client ('cli' or 'api')
        github_token: GitHub token (required for 'api' client)

    Returns:
        GitHubClient: Configured client instance

    Raises:
        ValueError: When invalid client type or missing token
        AuthenticationError: When CLI authentication is not available
    """
    if client_type == "cli":
        client = CLIGitHubClient()
        # Test CLI authentication
        try:
            client.run_command("gh auth status")
        except GitHubCLIError as e:
            raise AuthenticationError(
                "GitHub CLI not authenticated. Please run 'gh auth login'"
            ) from e
        return client
    elif client_type == "api":
        if not github_token:
            raise ValueError("GitHub token is required for API client")
        return APIGitHubClient(github_token)
    else:
        raise ValueError(f"Unknown client type: {client_type}")
