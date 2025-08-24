#!/usr/bin/env python3
"""
GitHub Inventory CLI
Command-line interface for GitHub repository inventory tool
"""

import argparse
import os
import platform
import subprocess
import sys

from dotenv import load_dotenv

from .batch import get_default_configs, load_config_from_file, run_batch_processing
from .inventory import (
    collect_owned_repositories,
    collect_starred_repositories,
    write_to_csv,
)
from .report import generate_markdown_report, read_csv_data


class PathManager:
    """Manages output paths for GitHub inventory files"""
    
    def __init__(self, username: str):
        self.username = username
        self._output_base = self._get_output_base()
    
    def _get_output_base(self) -> str:
        """Determine output directory based on installation type"""
        if os.path.exists("pyproject.toml") and os.path.exists("src/github_inventory"):
            # Development mode - use relative paths
            return "docs"
        else:
            # Global install - use home directory
            output_base = os.path.expanduser("~/.ghscan")
            os.makedirs(output_base, exist_ok=True)
            return output_base
    
    def get_owned_csv_path(self, args_path: str) -> str:
        """Get path for owned repositories CSV"""
        if self._is_default_path(args_path):
            return f"{self._output_base}/{self.username}/repos.csv"
        return args_path
    
    def get_starred_csv_path(self, args_path: str) -> str:
        """Get path for starred repositories CSV"""
        if self._is_default_path(args_path):
            return f"{self._output_base}/{self.username}/starred_repos.csv"
        return args_path
    
    def get_report_md_path(self, args_path: str) -> str:
        """Get path for markdown report"""
        if self._is_default_path(args_path):
            return f"{self._output_base}/{self.username}/README.md"
        return args_path
    
    def _is_default_path(self, path: str) -> bool:
        """Check if path uses default pattern that should be updated"""
        default_username = os.getenv("GITHUB_USERNAME", "hsb3")
        return (
            path.startswith(f"docs/{default_username}/") or
            path.endswith("github_inventory_detailed.csv") or
            path.endswith("starred_repos.csv") or
            path.endswith("github_inventory_report.md")
        )
    
    def ensure_output_directory(self, file_path: str) -> None:
        """Ensure output directory exists for given file path"""
        output_dir = os.path.dirname(file_path) or "."
        os.makedirs(output_dir, exist_ok=True)
    
    @property
    def output_base(self) -> str:
        """Get the output base directory"""
        return self._output_base


def get_output_base():
    """Determine output directory based on installation type"""
    if os.path.exists("pyproject.toml") and os.path.exists("src/github_inventory"):
        # Development mode - use relative paths
        return "docs"
    else:
        # Global install - use home directory
        output_base = os.path.expanduser("~/.ghscan")
        os.makedirs(output_base, exist_ok=True)
        return output_base


def open_directory(directory_path):
    """Open directory in the default file manager"""
    abs_path = os.path.abspath(directory_path)

    if not os.path.exists(abs_path):
        os.makedirs(abs_path, exist_ok=True)

    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            subprocess.run(["open", abs_path], check=True)  # noqa: S603, S607
        elif system == "Windows":
            subprocess.run(["explorer", abs_path], check=True)  # noqa: S603, S607
        else:  # Linux and others
            subprocess.run(["xdg-open", abs_path], check=True)  # noqa: S603, S607
        print(f"📂 Opened {abs_path}")
    except subprocess.CalledProcessError:
        print(f"❌ Could not open directory. Path: {abs_path}")
    except FileNotFoundError:
        print(f"❌ Could not find file manager to open directory. Path: {abs_path}")


def create_parser():
    """Create the argument parser"""
    # Load environment variables
    load_dotenv()

    # Get default values from environment or fallback values
    default_username = os.getenv("GITHUB_USERNAME", "hsb3")

    # Determine output directory
    output_base = get_output_base()

    # Default output paths
    default_owned_csv = os.getenv(
        "OWNED_REPOS_CSV", f"{output_base}/{default_username}/repos.csv"
    )
    default_starred_csv = os.getenv(
        "STARRED_REPOS_CSV", f"{output_base}/{default_username}/starred_repos.csv"
    )
    default_report_md = os.getenv(
        "REPORT_OUTPUT_MD", f"{output_base}/{default_username}/README.md"
    )

    parser = argparse.ArgumentParser(
        description="GitHub Repository Inventory Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Output Location: {output_base}/

Examples:
  # Generate full inventory and report
  ghscan --user hsb3

  # Generate only owned repositories
  ghscan --user hsb3 --owned-only

  # Generate only starred repositories
  ghscan --user hsb3 --starred-only

  # Generate markdown report from existing CSV files
  ghscan --report-only

  # Open the output directory
  ghscan --open

  # Custom output files
  ghscan --user hsb3 --owned-csv my_repos.csv --starred-csv my_stars.csv

  # Batch processing with default accounts
  ghscan --batch

  # Batch processing with custom config file (YAML recommended)
  ghscan --config myconfig.yaml
        """,
    )

    parser.add_argument(
        "--user",
        "-u",
        default=default_username,
        help=f"GitHub username (default: {default_username})",
    )

    parser.add_argument(
        "--owned-only", action="store_true", help="Only collect owned repositories"
    )

    parser.add_argument(
        "--starred-only", action="store_true", help="Only collect starred repositories"
    )

    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Only generate markdown report from existing CSV files",
    )

    parser.add_argument(
        "--owned-csv",
        default=default_owned_csv,
        help=f"Output file for owned repositories CSV (default: {default_owned_csv})",
    )

    parser.add_argument(
        "--starred-csv",
        default=default_starred_csv,
        help=f"Output file for starred repositories CSV (default: {default_starred_csv})",
    )

    parser.add_argument(
        "--report-md",
        default=default_report_md,
        help=f"Output file for markdown report (default: {default_report_md})",
    )

    parser.add_argument(
        "--no-report", action="store_true", help="Skip generating markdown report"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of repositories to process (useful for large accounts)",
    )

    parser.add_argument("--version", action="version", version="github_inventory 0.1.0")

    parser.add_argument(
        "--open",
        action="store_true",
        help=f"Open the output directory ({output_base}) in your default file manager",
    )

    # Batch processing arguments
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Run batch processing with default account configurations",
    )

    parser.add_argument(
        "--config",
        help="Run batch processing with custom configuration file (JSON/YAML)",
    )

    return parser


def print_summary(owned_repos, starred_repos):
    """Print summary statistics"""
    print(f"\n{'=' * 50}")
    print("SUMMARY")
    print(f"{'=' * 50}")

    if owned_repos:
        print(f"📁 Your repositories: {len(owned_repos)}")
        public_count = len([r for r in owned_repos if r.get("visibility") == "public"])
        private_count = len(
            [r for r in owned_repos if r.get("visibility") == "private"]
        )
        fork_count = len([r for r in owned_repos if r.get("is_fork") == "true"])
        original_count = len([r for r in owned_repos if r.get("is_fork") == "false"])

        print(f"   - Public: {public_count} | Private: {private_count}")
        print(f"   - Original: {original_count} | Forks: {fork_count}")

        # Language breakdown
        languages: dict[str, int] = {}
        for repo in owned_repos:
            lang = repo.get("primary_language", "")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1

        if languages:
            top_languages = sorted(languages.items(), key=lambda x: x[1], reverse=True)[
                :3
            ]
            lang_str = " | ".join([f"{lang}: {count}" for lang, count in top_languages])
            print(f"   - Top languages: {lang_str}")

    if starred_repos:
        print(f"⭐ Starred repositories: {len(starred_repos)}")
        public_count = len(
            [r for r in starred_repos if r.get("visibility") == "public"]
        )
        private_count = len(
            [r for r in starred_repos if r.get("visibility") == "private"]
        )
        archived_count = len([r for r in starred_repos if r.get("archived") == "true"])

        print(
            f"   - Public: {public_count} | Private: {private_count} | Archived: {archived_count}"
        )

        # Language breakdown
        starred_languages: dict[str, int] = {}
        for repo in starred_repos:
            lang = repo.get("primary_language", "")
            if lang:
                starred_languages[lang] = starred_languages.get(lang, 0) + 1

        if starred_languages:
            top_languages = sorted(
                starred_languages.items(), key=lambda x: x[1], reverse=True
            )[:3]
            lang_str = " | ".join([f"{lang}: {count}" for lang, count in top_languages])
            print(f"   - Top languages: {lang_str}")


def handle_batch_processing(args):
    """Handle batch processing mode"""
    if args.batch and args.config:
        print("Error: Cannot use --batch and --config together")
        sys.exit(1)

    if args.batch:
        print("Running batch processing with default configurations...")
        configs = get_default_configs()
    else:
        print(f"Running batch processing with config file: {args.config}")
        configs = load_config_from_file(args.config)

    run_batch_processing(configs)


def collect_repository_data(args, path_manager):
    """Collect owned and starred repository data"""
    owned_repos = []
    starred_repos = []

    # Collect owned repositories
    if not args.starred_only:
        print(f"\nCollecting owned repositories for user: {args.user}")
        print("-" * 50)

        owned_repos = collect_owned_repositories(args.user, args.limit)

        if owned_repos:
            owned_headers = [
                "name",
                "description",
                "url",
                "visibility",
                "is_fork",
                "creation_date",
                "last_update_date",
                "default_branch",
                "number_of_branches",
                "primary_language",
                "size",
            ]
            owned_csv_path = path_manager.get_owned_csv_path(args.owned_csv)
            path_manager.ensure_output_directory(owned_csv_path)
            write_to_csv(owned_repos, owned_csv_path, owned_headers)
        else:
            print("Failed to collect owned repositories")

    # Collect starred repositories
    if not args.owned_only:
        print("\nCollecting starred repositories...")
        print("-" * 50)

        starred_repos = collect_starred_repositories(args.user, args.limit)

        if starred_repos:
            starred_headers = [
                "name",
                "full_name",
                "owner",
                "description",
                "url",
                "visibility",
                "is_fork",
                "creation_date",
                "last_update_date",
                "last_push_date",
                "default_branch",
                "number_of_branches",
                "primary_language",
                "size",
                "stars",
                "forks",
                "watchers",
                "open_issues",
                "license",
                "topics",
                "homepage",
                "archived",
                "disabled",
            ]
            starred_csv_path = path_manager.get_starred_csv_path(args.starred_csv)
            path_manager.ensure_output_directory(starred_csv_path)
            write_to_csv(starred_repos, starred_csv_path, starred_headers)
        else:
            print("Failed to collect starred repositories")

    return owned_repos, starred_repos


def generate_outputs(args, path_manager, owned_repos, starred_repos):
    """Generate markdown report and print summary"""
    # Generate markdown report
    if not args.no_report and (owned_repos or starred_repos):
        print("\nGenerating markdown report...")
        print("-" * 50)

        report_md_path = path_manager.get_report_md_path(args.report_md)
        path_manager.ensure_output_directory(report_md_path)
        
        success = generate_markdown_report(
            owned_repos=owned_repos,
            starred_repos=starred_repos,
            username=args.user,
            output_file=report_md_path,
            limit_applied=args.limit,
        )

        if not success:
            print("Failed to generate markdown report")
            sys.exit(1)

    # Print summary
    if owned_repos or starred_repos:
        print_summary(owned_repos, starred_repos)
        print("\n✅ GitHub inventory completed successfully!")
    else:
        print("❌ No data collected. Please check your GitHub CLI authentication.")
        sys.exit(1)


def main():
    """Main CLI function orchestrating repository inventory workflow"""
    parser = create_parser()
    args = parser.parse_args()

    # Handle --open command
    if args.open:
        output_base = get_output_base()
        open_directory(output_base)
        return

    print("GitHub Repository Inventory Tool")
    print("=" * 50)

    # Handle batch processing mode
    if args.batch or args.config:
        handle_batch_processing(args)
        return

    # Initialize path manager
    path_manager = PathManager(args.user)

    # Handle report-only mode
    if args.report_only:
        print("Generating report from existing CSV files...")

        owned_csv_path = path_manager.get_owned_csv_path(args.owned_csv)
        starred_csv_path = path_manager.get_starred_csv_path(args.starred_csv)
        
        owned_repos = read_csv_data(owned_csv_path)
        starred_repos = read_csv_data(starred_csv_path)

        if not owned_repos and not starred_repos:
            print("Error: No existing CSV files found. Run without --report-only first.")
            sys.exit(1)

        report_md_path = path_manager.get_report_md_path(args.report_md)
        path_manager.ensure_output_directory(report_md_path)
        
        success = generate_markdown_report(
            owned_repos=owned_repos,
            starred_repos=starred_repos,
            username=args.user,
            output_file=report_md_path,
            limit_applied=args.limit,
        )

        if success:
            print_summary(owned_repos, starred_repos)
        sys.exit(0 if success else 1)

    # Collect repository data
    owned_repos, starred_repos = collect_repository_data(args, path_manager)

    # Generate outputs
    generate_outputs(args, path_manager, owned_repos, starred_repos)


if __name__ == "__main__":
    main()
