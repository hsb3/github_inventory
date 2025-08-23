#!/usr/bin/env python3
"""
GitHub Repository Markdown Report Generator
Creates a markdown file with tables showing repository inventories
"""

import csv
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

from dotenv import load_dotenv

from .models import OwnedRepository, StarredRepository


def read_csv_data(filename: str) -> List[Dict[str, Any]]:
    """Read CSV data and return as list of dictionaries"""
    if not os.path.exists(filename):
        print(f"Error: {filename} not found")
        return []

    try:
        with open(filename, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            return list(reader)
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return []


def format_number(value: Union[str, int, None]) -> str:
    """Format numbers with commas for readability"""
    if not value or value == "" or value == "unknown":
        return str(value) if value is not None else ""
    try:
        # Handle both string and integer inputs
        if isinstance(value, int):
            return f"{value:,}"
        num = int(value)
        return f"{num:,}"
    except (ValueError, TypeError):
        return str(value)


def format_size_mb(value: Union[str, int, None]) -> str:
    """Format size from KB to MB with one decimal place"""
    if not value or value == "" or value == "unknown":
        return str(value) if value is not None else ""
    try:
        # Handle both string and integer inputs
        if isinstance(value, int):
            kb = value
        else:
            kb = int(value)
        mb = kb / 1024
        if mb < 0.1:
            return "<0.1"
        return f"{mb:.1f}"
    except (ValueError, TypeError):
        return str(value) if value is not None else ""


def truncate_description(description: Optional[str], max_length: int = 80) -> str:
    """Truncate description to fit in table"""
    if not description or len(description) <= max_length:
        return description
    return description[: max_length - 3] + "..."


def create_owned_repos_table(repos_data: List[Dict[str, Any]], limit_applied: Optional[int] = None) -> str:
    """Create markdown table for owned repositories"""
    if not repos_data:
        return "No owned repository data found.\n\n"

    # Load environment variables
    load_dotenv()

    # Get display limit from environment variable, default to 30
    display_limit = int(os.getenv("REPORT_OWNED_LIMIT", "30"))
    if display_limit == -1:
        display_limit = len(repos_data)  # Show all repos

    # Sort by last update date (most recent first)
    sorted_repos = sorted(
        repos_data, key=lambda x: x.get("last_update_date", ""), reverse=True
    )

    table = "## Owned Repositories\n\n"
    table += f"**Total:** {len(repos_data)} repositories\n\n"

    # Summary stats
    public_count = len([r for r in repos_data if r.get("visibility") == "public"])
    private_count = len([r for r in repos_data if r.get("visibility") == "private"])
    fork_count = len([r for r in repos_data if r.get("is_fork") == "true"])
    original_count = len([r for r in repos_data if r.get("is_fork") == "false"])

    table += f"- **Public:** {public_count} | **Private:** {private_count}\n"
    table += f"- **Original:** {original_count} | **Forks:** {fork_count}\n\n"

    # Language breakdown
    languages: dict[str, int] = {}
    for repo in repos_data:
        lang = repo.get("primary_language", "")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1

    if languages:
        top_languages = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]
        table += (
            "**Top Languages:** "
            + " | ".join([f"{lang}: {count}" for lang, count in top_languages])
            + "\n\n"
        )

    # Table headers
    table += "| Name | Description | Visibility | Language | Size (MB) | Branches | Updated |\n"
    table += "|------|-------------|------------|----------|-----------|----------|----------|\n"

    # Table rows
    for repo in sorted_repos[:display_limit]:  # Show configurable number of repos
        name = f"[{repo.get('name', '')}]({repo.get('url', '')})"
        description = truncate_description(repo.get("description", ""), 50)
        visibility = repo.get("visibility", "")
        if repo.get("is_fork") == "true":
            visibility += " (fork)"
        language = repo.get("primary_language", "")
        size = format_size_mb(repo.get("size", ""))
        branches = format_number(repo.get("number_of_branches", ""))
        updated = repo.get("last_update_date", "")

        table += f"| {name} | {description} | {visibility} | {language} | {size} | {branches} | {updated} |\n"

    if len(repos_data) > display_limit and display_limit != -1:
        if limit_applied:
            table += f"\n*Showing {display_limit} most recently updated repositories out of {len(repos_data)} collected (limited to {limit_applied}).*\n"
        else:
            table += f"\n*Showing {display_limit} most recently updated repositories out of {len(repos_data)} total.*\n"
    elif limit_applied and len(repos_data) == limit_applied:
        table += f"\n*Showing all {len(repos_data)} repositories (limited to {limit_applied}).*\n"

    table += "\n---\n\n"
    return table


def create_starred_repos_table(starred_data: List[Dict[str, Any]], limit_applied: Optional[int] = None) -> str:
    """Create markdown table for starred repositories"""
    if not starred_data:
        return "No starred repository data found.\n\n"

    # Load environment variables
    load_dotenv()

    # Get display limit from environment variable, default to 25
    display_limit = int(os.getenv("REPORT_STARRED_LIMIT", "25"))
    if display_limit == -1:
        display_limit = len(starred_data)  # Show all repos

    # Sort by star count (most starred first)
    def get_star_count(repo: Dict[str, Any]) -> int:
        stars = repo.get("stars", 0)
        if isinstance(stars, int):
            return stars
        try:
            return int(stars or "0")
        except (ValueError, TypeError):
            return 0
    
    sorted_starred = sorted(
        starred_data, key=get_star_count, reverse=True
    )

    table = "## Starred Repositories\n\n"
    table += f"**Total:** {len(starred_data)} starred repositories\n\n"

    # Summary stats
    public_count = len([r for r in starred_data if r.get("visibility") == "public"])
    private_count = len([r for r in starred_data if r.get("visibility") == "private"])
    archived_count = len([r for r in starred_data if r.get("archived") == "true"])

    table += f"- **Public:** {public_count} | **Private:** {private_count} | **Archived:** {archived_count}\n\n"

    # Language breakdown
    languages: dict[str, int] = {}
    for repo in starred_data:
        lang = repo.get("primary_language", "")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1

    if languages:
        top_languages = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:8]
        table += (
            "**Top Languages:** "
            + " | ".join([f"{lang}: {count}" for lang, count in top_languages])
            + "\n\n"
        )

    # Table headers
    table += "| Repository | Owner | Description | Language | ⭐ Stars | 🍴 Forks | Updated |\n"
    table += "|------------|-------|-------------|----------|----------|----------|----------|\n"

    # Table rows
    for repo in sorted_starred[:display_limit]:  # Show configurable number of repos
        name = f"[{repo.get('name', '')}]({repo.get('url', '')})"
        owner = repo.get("owner", "")
        description = truncate_description(repo.get("description", ""), 60)
        language = repo.get("primary_language", "")
        stars = format_number(repo.get("stars", "0"))
        forks = format_number(repo.get("forks", "0"))
        updated = repo.get("last_update_date", "")

        # Add archived indicator
        if repo.get("archived") == "true":
            name += " 🗄️"

        table += f"| {name} | {owner} | {description} | {language} | {stars} | {forks} | {updated} |\n"

    if len(starred_data) > display_limit and display_limit != -1:
        if limit_applied:
            table += f"\n*Showing {display_limit} most starred repositories out of {len(starred_data)} collected (limited to {limit_applied}).*\n"
        else:
            table += f"\n*Showing {display_limit} most starred repositories out of {len(starred_data)} total.*\n"
    elif limit_applied and len(starred_data) == limit_applied:
        table += f"\n*Showing all {len(starred_data)} starred repositories (limited to {limit_applied}).*\n"

    table += "\n---\n\n"
    return table


def create_summary_section(username: str = "hsb3") -> str:
    """Create a summary section with key metrics"""
    current_date = datetime.now().strftime("%Y-%m-%d at %H:%M UTC")

    summary = "# GitHub Repository Inventory Report\n\n"
    summary += f"**Generated:** {current_date}  \n"
    summary += f"**Account:** @{username}  \n"
    summary += "**Tool:** [GitHub Inventory](https://github.com/hsb3/github_inventory) via GitHub CLI\n\n"

    summary += "## Overview\n\n"
    summary += "This automated report provides a comprehensive analysis of GitHub repositories and starred projects. "
    summary += "Data is collected using the GitHub CLI and includes repository metadata, activity metrics, and language statistics.\n\n"

    # Add methodology notes
    summary += "## Methodology & Notes\n\n"
    summary += "- **Data Source:** GitHub REST API v4 via GitHub CLI\n"
    summary += "- **Repository Sizes:** Displayed in MB (converted from KB)\n"
    summary += (
        "- **Sorting:** Owned repositories by last update date, starred by star count\n"
    )
    summary += "- **Indicators:** 🗄️ = archived, (fork) = forked repository\n"
    summary += "- **Limitations:** Tables show most relevant entries; full data available in CSV exports\n\n"
    summary += "---\n\n"

    return summary


def create_footer() -> str:
    """Create a footer with additional information"""
    footer = "\n---\n"
    footer += "*Generated using GitHub CLI and Python*\n"

    return footer


def generate_markdown_report(
    owned_repos: Optional[List[Dict[str, Any]]] = None,
    starred_repos: Optional[List[Dict[str, Any]]] = None,
    username: str = "hsb3",
    output_file: str = "github_inventory_report.md",
    limit_applied: Optional[int] = None,
) -> bool:
    """Generate a complete markdown report"""

    # Create markdown content
    markdown_content = ""

    # Summary section
    markdown_content += create_summary_section(username)

    # Owned repositories table
    if owned_repos:
        markdown_content += create_owned_repos_table(owned_repos, limit_applied)

    # Starred repositories table
    if starred_repos:
        markdown_content += create_starred_repos_table(starred_repos, limit_applied)

    # Footer
    markdown_content += create_footer()

    # Write to file
    try:
        with open(output_file, "w", encoding="utf-8") as file:
            file.write(markdown_content)

        print(f"✅ Markdown report created: {output_file}")

        # Print summary
        if owned_repos:
            print(f"📁 Your repositories: {len(owned_repos)}")
        if starred_repos:
            print(f"⭐ Starred repositories: {len(starred_repos)}")

        return True

    except Exception as e:
        print(f"Error writing markdown file: {e}")
        return False
