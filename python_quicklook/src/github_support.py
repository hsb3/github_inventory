"""
GitHub repository support for Python Quick Look tool.
Uses GitHub CLI (gh) for secure and efficient repository access.
"""

import logging
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class GitHubRepo:
    """Information about a GitHub repository."""

    owner: str
    name: str
    branch: Optional[str] = None
    is_private: bool = False
    clone_url: str = ""

    @property
    def full_name(self) -> str:
        """Get the full repository name (owner/name)."""
        return f"{self.owner}/{self.name}"

    @property
    def github_url(self) -> str:
        """Get the GitHub URL for this repository."""
        return f"https://github.com/{self.full_name}"


class GitHubError(Exception):
    """Exception raised for GitHub-related errors."""
    pass


class GitHubSupport:
    """Handles GitHub repository operations using gh cli."""

    def __init__(self):
        """Initialize GitHub support."""
        self.temp_dirs: list[Path] = []  # Track temp directories for cleanup

    def parse_github_url(self, url: str) -> Optional[GitHubRepo]:
        """Parse a GitHub URL into repository components.

        Supports formats:
        - github.com/owner/repo
        - https://github.com/owner/repo
        - https://github.com/owner/repo.git
        - https://github.com/owner/repo/tree/branch
        - owner/repo (simple format)

        Args:
            url: GitHub URL or repository identifier

        Returns:
            GitHubRepo object or None if not a valid GitHub URL
        """
        # Clean up the URL
        url = url.strip()

        # Handle simple owner/repo format
        if '/' in url and not url.startswith(('http', 'github.com')):
            parts = url.split('/')
            if len(parts) == 2 and all(part.strip() for part in parts):
                return GitHubRepo(owner=parts[0], name=parts[1])

        # Handle GitHub URLs
        patterns = [
            # https://github.com/owner/repo
            r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?(?:\?.*)?$',
            # https://github.com/owner/repo/tree/branch
            r'https?://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/?(?:\?.*)?$',
            # github.com/owner/repo
            r'github\.com/([^/]+)/([^/]+?)(?:\.git)?/?(?:\?.*)?$',
            # github.com/owner/repo/tree/branch
            r'github\.com/([^/]+)/([^/]+)/tree/([^/]+)/?(?:\?.*)?$',
        ]

        for pattern in patterns:
            match = re.match(pattern, url, re.IGNORECASE)
            if match:
                groups = match.groups()
                owner, name = groups[0], groups[1]
                branch = groups[2] if len(groups) > 2 else None

                # Clean up repository name (remove .git suffix if present)
                name = name.replace('.git', '')

                return GitHubRepo(owner=owner, name=name, branch=branch)

        return None

    def check_gh_cli(self) -> bool:
        """Check if GitHub CLI is available and authenticated.

        Returns:
            True if gh cli is available and authenticated
        """
        try:
            # Check if gh is installed
            result = subprocess.run(
                ['gh', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.error("GitHub CLI (gh) is not installed")
                return False

            # Check if authenticated
            result = subprocess.run(
                ['gh', 'auth', 'status'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.warning("GitHub CLI is not authenticated - public repos only")
                # We can still work with public repos

            return True

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"Failed to check GitHub CLI: {e}")
            return False

    def get_repo_info(self, repo: GitHubRepo) -> GitHubRepo:
        """Get additional information about a repository.

        Args:
            repo: Basic repository information

        Returns:
            Enhanced repository information
        """
        try:
            cmd = ['gh', 'repo', 'view', repo.full_name, '--json', 'isPrivate,defaultBranchRef']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                repo.is_private = data.get('isPrivate', False)

                # Use default branch if none specified
                if not repo.branch and 'defaultBranchRef' in data:
                    repo.branch = data['defaultBranchRef']['name']

        except Exception as e:
            logger.warning(f"Could not get repo info for {repo.full_name}: {e}")
            # Set reasonable defaults
            repo.branch = repo.branch or 'main'

        return repo

    def clone_repository(self, repo: GitHubRepo) -> Path:
        """Clone a GitHub repository to a temporary directory.

        Args:
            repo: Repository to clone

        Returns:
            Path to the cloned repository

        Raises:
            GitHubError: If cloning fails
        """
        try:
            # Create temporary directory
            temp_dir = Path(tempfile.mkdtemp(prefix=f"quicklook_{repo.name}_"))
            self.temp_dirs.append(temp_dir)

            # Build gh repo clone command
            cmd = ['gh', 'repo', 'clone', repo.full_name, str(temp_dir)]

            # Add branch specification if provided
            if repo.branch:
                cmd.extend(['--', '--branch', repo.branch])

            logger.info(f"Cloning {repo.full_name} (branch: {repo.branch or 'default'})...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout for cloning
            )

            if result.returncode != 0:
                error_msg = f"Failed to clone {repo.full_name}: {result.stderr}"
                logger.error(error_msg)
                raise GitHubError(error_msg)

            logger.info(f"Successfully cloned to: {temp_dir}")
            return temp_dir

        except subprocess.TimeoutExpired:
            error_msg = f"Timeout while cloning {repo.full_name}"
            logger.error(error_msg)
            raise GitHubError(error_msg)
        except Exception as e:
            error_msg = f"Failed to clone {repo.full_name}: {e}"
            logger.error(error_msg)
            raise GitHubError(error_msg)

    def cleanup(self):
        """Clean up all temporary directories created during this session."""
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up {temp_dir}: {e}")

        self.temp_dirs.clear()

    def analyze_github_url(self, url: str) -> Tuple[Optional[GitHubRepo], Optional[Path]]:
        """Analyze a GitHub URL and prepare it for code analysis.

        Args:
            url: GitHub URL or repository identifier

        Returns:
            Tuple of (repo_info, local_path) or (None, None) if failed
        """
        # Parse the URL
        repo = self.parse_github_url(url)
        if not repo:
            logger.error(f"Invalid GitHub URL format: {url}")
            return None, None

        # Check GitHub CLI availability
        if not self.check_gh_cli():
            logger.error("GitHub CLI is required for repository analysis")
            return None, None

        try:
            # Get repository information
            repo = self.get_repo_info(repo)

            # Clone the repository
            local_path = self.clone_repository(repo)

            return repo, local_path

        except GitHubError as e:
            logger.error(f"GitHub operation failed: {e}")
            return None, None
        except Exception as e:
            logger.error(f"Unexpected error analyzing GitHub URL: {e}")
            return None, None


def main():
    """Test GitHub support functionality."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python github_support.py <github_url>")
        print("Examples:")
        print("  python github_support.py github.com/psf/requests")
        print("  python github_support.py https://github.com/python/cpython")
        print("  python github_support.py pallets/flask")
        return

    url = sys.argv[1]
    github = GitHubSupport()

    try:
        print(f"🔍 Analyzing GitHub URL: {url}")

        repo, local_path = github.analyze_github_url(url)

        if repo and local_path:
            print(f"✅ Repository: {repo.full_name}")
            print(f"📁 Local path: {local_path}")
            print(f"🌿 Branch: {repo.branch}")
            print(f"🔒 Private: {repo.is_private}")

            # List some files to verify
            python_files = list(local_path.glob('**/*.py'))
            print(f"🐍 Found {len(python_files)} Python files")

            if python_files:
                print("📄 Sample files:")
                for f in python_files[:5]:
                    print(f"  - {f.relative_to(local_path)}")
        else:
            print("❌ Failed to analyze repository")

    finally:
        # Always cleanup
        github.cleanup()
        print("🧹 Cleaned up temporary files")


if __name__ == "__main__":
    main()
