#!/usr/bin/env python3
"""
GitHub Inventory Batch Processing Module
Handles batch processing of multiple GitHub accounts with configuration support
"""

import json
import sys
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, ValidationError

from .inventory import (
    collect_owned_repositories,
    collect_starred_repositories,
    write_to_csv,
)
from .report import generate_markdown_report


class RunConfig(BaseModel):
    """Configuration for a single GitHub account run"""

    account: str
    limit: Optional[int] = None


class ConfigsToRun(BaseModel):
    """Configuration containing multiple account runs"""

    configs: List[RunConfig]


def get_default_configs() -> ConfigsToRun:
    """Get the default configuration for batch processing"""
    return ConfigsToRun(
        configs=[
            RunConfig(account="langchain-ai", limit=100),
            RunConfig(account="aider-ai"),
            RunConfig(account="dlt-hub"),
        ]
    )


def load_config_from_file(config_file: str) -> ConfigsToRun:
    """Load configuration from JSON or YAML file"""
    config_path = Path(config_file)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            if config_path.suffix.lower() in [".yml", ".yaml"]:
                try:
                    import yaml

                    data = yaml.safe_load(f)
                except ImportError as err:
                    raise ImportError(
                        "PyYAML is required to read YAML config files. Install with: uv add pyyaml"
                    ) from err
            else:
                data = json.load(f)

        return ConfigsToRun(**data)

    except ValidationError as e:
        print(f"Configuration validation error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading configuration file: {e}")
        sys.exit(1)


def create_output_directory(account: str, base_dir: str = "docs") -> Path:
    """Create output directory for an account"""
    output_dir = Path(base_dir) / account
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def process_single_account(config: RunConfig, base_dir: str = "docs") -> bool:
    """Process a single GitHub account and save to its directory"""
    account = config.account
    limit = config.limit

    print(f"\n{'='*60}")
    print(f"Processing account: {account}")
    if limit:
        print(f"Repository limit: {limit}")
    print(f"{'='*60}")

    # Create output directory
    output_dir = create_output_directory(account, base_dir)

    # Define output files
    owned_csv = output_dir / "repos.csv"
    starred_csv = output_dir / "starred_repos.csv"
    report_md = output_dir / "README.md"

    owned_repos = []
    starred_repos = []

    try:
        # Collect owned repositories
        print(f"\nCollecting owned repositories for: {account}")
        print("-" * 50)
        owned_repos = collect_owned_repositories(account, limit)

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
            write_to_csv(owned_repos, str(owned_csv), owned_headers)
        else:
            print(f"No owned repositories found for {account}")

        # Collect starred repositories
        print(f"\nCollecting starred repositories for: {account}")
        print("-" * 50)
        starred_repos = collect_starred_repositories(account, limit)

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
            write_to_csv(starred_repos, str(starred_csv), starred_headers)
        else:
            print(f"No starred repositories found for {account}")

        # Generate markdown report
        if owned_repos or starred_repos:
            print(f"\nGenerating markdown report for: {account}")
            print("-" * 50)

            success = generate_markdown_report(
                owned_repos=owned_repos,
                starred_repos=starred_repos,
                username=account,
                output_file=str(report_md),
                limit_applied=limit,
            )

            if success:
                print(f"✅ Successfully processed account: {account}")
                print(f"   - Owned repositories: {len(owned_repos)}")
                print(f"   - Starred repositories: {len(starred_repos)}")
                print(f"   - Output directory: {output_dir}")
                return True
            else:
                print(f"❌ Failed to generate report for: {account}")
                return False
        else:
            print(f"⚠️  No data collected for: {account}")
            return False

    except Exception as e:
        print(f"❌ Error processing account {account}: {e}")
        return False


def run_batch_processing(configs: ConfigsToRun, base_dir: str = "docs") -> None:
    """Run batch processing for multiple GitHub accounts"""
    print("GitHub Repository Inventory - Batch Processing")
    print("=" * 60)
    print(f"Processing {len(configs.configs)} accounts...")

    successful = 0
    failed = 0

    for i, config in enumerate(configs.configs, 1):
        print(f"\n[{i}/{len(configs.configs)}] Processing: {config.account}")

        success = process_single_account(config, base_dir)
        if success:
            successful += 1
        else:
            failed += 1

    # Print final summary
    print(f"\n{'='*60}")
    print("BATCH PROCESSING SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successful accounts: {successful}")
    print(f"❌ Failed accounts: {failed}")
    print(f"📁 Total accounts processed: {len(configs.configs)}")

    if successful > 0:
        print(f"\n📂 Output directory: {base_dir}/")
        print("   Each account has its own subdirectory with:")
        print("   - repos.csv (owned repositories)")
        print("   - starred_repos.csv (starred repositories)")
        print("   - README.md (markdown report)")

    if failed > 0:
        print(f"\n⚠️  {failed} account(s) failed. Check output above for details.")
        sys.exit(1)
    else:
        print("\n🎉 All accounts processed successfully!")
