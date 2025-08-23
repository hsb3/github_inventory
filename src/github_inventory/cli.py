#!/usr/bin/env python3
"""
GitHub Inventory CLI
Command-line interface for GitHub repository inventory tool
"""

import argparse
import os
import sys

from dotenv import load_dotenv

from .batch import get_default_configs, load_config_from_file, run_batch_processing
from .inventory import (
    collect_owned_repositories,
    collect_starred_repositories,
    write_to_csv,
)
from .report import generate_markdown_report, read_csv_data


def create_parser():
    """Create the argument parser"""
    # Load environment variables
    load_dotenv()

    # Get default values from environment or fallback values
    default_username = os.getenv("GITHUB_USERNAME", "hsb3")

    # Default to docs/{username}/ structure for consistency with batch processing
    default_owned_csv = os.getenv(
        "OWNED_REPOS_CSV", f"docs/{default_username}/repos.csv"
    )
    default_starred_csv = os.getenv(
        "STARRED_REPOS_CSV", f"docs/{default_username}/starred_repos.csv"
    )
    default_report_md = os.getenv(
        "REPORT_OUTPUT_MD", f"docs/{default_username}/README.md"
    )

    parser = argparse.ArgumentParser(
        description="GitHub Repository Inventory Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate full inventory and report
  gh-inventory --user hsb3

  # Generate only owned repositories
  gh-inventory --user hsb3 --owned-only

  # Generate only starred repositories
  gh-inventory --user hsb3 --starred-only

  # Generate markdown report from existing CSV files
  gh-inventory --report-only

  # Custom output files
  gh-inventory --user hsb3 --owned-csv my_repos.csv --starred-csv my_stars.csv

  # Batch processing with default accounts
  gh-inventory --batch

  # Batch processing with custom config file (YAML recommended)
  gh-inventory --config myconfig.yaml
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


def main():
    """Main CLI function"""
    parser = create_parser()
    args = parser.parse_args()

    print("GitHub Repository Inventory Tool")
    print("=" * 50)

    # Handle batch processing mode
    if args.batch or args.config:
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
        return

    owned_repos = []
    starred_repos = []

    # Update paths to use the current username (always use docs/{username}/ structure)
    default_username = os.getenv("GITHUB_USERNAME", "hsb3")
    if (
        args.owned_csv == f"docs/{default_username}/repos.csv"
        or args.owned_csv.endswith("github_inventory_detailed.csv")
    ):
        args.owned_csv = f"docs/{args.user}/repos.csv"
    if (
        args.starred_csv == f"docs/{default_username}/starred_repos.csv"
        or args.starred_csv.endswith("starred_repos.csv")
    ):
        args.starred_csv = f"docs/{args.user}/starred_repos.csv"
    if (
        args.report_md == f"docs/{default_username}/README.md"
        or args.report_md.endswith("github_inventory_report.md")
    ):
        args.report_md = f"docs/{args.user}/README.md"

    # Ensure output directory exists
    output_dir = os.path.dirname(args.owned_csv) or "."
    os.makedirs(output_dir, exist_ok=True)

    # Handle report-only mode
    if args.report_only:
        print("Generating report from existing CSV files...")

        owned_repos = read_csv_data(args.owned_csv)
        starred_repos = read_csv_data(args.starred_csv)

        if not owned_repos and not starred_repos:
            print(
                "Error: No existing CSV files found. Run without --report-only first."
            )
            sys.exit(1)

        success = generate_markdown_report(
            owned_repos=owned_repos,
            starred_repos=starred_repos,
            username=args.user,
            output_file=args.report_md,
            limit_applied=args.limit,
        )

        if success:
            print_summary(owned_repos, starred_repos)
        sys.exit(0 if success else 1)

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
            write_to_csv(owned_repos, args.owned_csv, owned_headers)
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
            write_to_csv(starred_repos, args.starred_csv, starred_headers)
        else:
            print("Failed to collect starred repositories")

    # Generate markdown report
    if not args.no_report and (owned_repos or starred_repos):
        print("\nGenerating markdown report...")
        print("-" * 50)

        success = generate_markdown_report(
            owned_repos=owned_repos,
            starred_repos=starred_repos,
            username=args.user,
            output_file=args.report_md,
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


if __name__ == "__main__":
    main()
