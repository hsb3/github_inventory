# GitHub Inventory

A comprehensive GitHub repository inventory and analysis tool that uses the GitHub CLI to gather detailed information about your repositories and starred projects.

## Features

- 📊 **Complete Repository Analysis**: Collects detailed information about your GitHub repositories
- ⭐ **Starred Repository Tracking**: Analyzes your starred repositories with comprehensive metrics
- 📄 **Rich Reporting**: Generates professional Markdown reports with tables and statistics
- 🔧 **CLI Interface**: Easy-to-use command-line interface with flexible options
- 💾 **CSV Export**: Exports data to CSV files for further analysis
- 🎯 **Smart Filtering**: Options to collect only owned repos, starred repos, or both

## Prerequisites

- Python 3.12 or higher
- [GitHub CLI](https://cli.github.com/) installed and authenticated
- `uv` package manager

### GitHub CLI Setup

Make sure you have GitHub CLI installed and authenticated:

```bash
# Install GitHub CLI (if not already installed)
# On macOS with Homebrew:
brew install gh

# Authenticate with GitHub
gh auth login
```

## Quickstart

**Get started in 60 seconds:**

```bash
# Clone and setup
git clone https://github.com/hsb3/github-inventory.git
cd github-inventory
uv sync

# Try the example (50 repos from sindresorhus)
make example

# Or run with your username
uv run gh-inventory --user YOUR_USERNAME --limit 20
```

The example generates comprehensive reports in `docs/output_example/` showing owned repositories, starred repositories, and statistics.

## Installation

```bash
git clone https://github.com/hsb3/github-inventory.git
cd github-inventory
uv sync
```

That's it! No need to activate virtual environments - just use `uv run` for all commands.

## Usage

### Basic Usage

Generate a complete inventory for user "hsb3":

```bash
uv run gh-inventory --user hsb3
```

This will:
1. Collect all owned repositories
2. Collect all starred repositories  
3. Generate CSV files for both
4. Create a comprehensive Markdown report

### Command Options

```bash
# Show help
uv run gh-inventory --help

# Generate only owned repositories
uv run gh-inventory --user hsb3 --owned-only

# Generate only starred repositories
uv run gh-inventory --user hsb3 --starred-only

# Limit results for large accounts
uv run gh-inventory --user sindresorhus --limit 50

# Generate report from existing CSV files
uv run gh-inventory --report-only

# Custom output files
uv run gh-inventory --user hsb3 \
    --owned-csv my_repos.csv \
    --starred-csv my_stars.csv \
    --report-md my_report.md

# Skip markdown report generation
uv run gh-inventory --user hsb3 --no-report
```

### Output Files

The tool generates three main outputs:

1. **`repos.csv`** - Owned repositories with columns:
   - name, description, url, visibility, is_fork
   - creation_date, last_update_date, default_branch
   - number_of_branches, primary_language, size

2. **`starred_repos.csv`** - Your starred repositories with columns:
   - name, full_name, owner, description, url, visibility
   - is_fork, creation_date, last_update_date, last_push_date
   - default_branch, number_of_branches, primary_language, size
   - stars, forks, watchers, open_issues, license, topics
   - homepage, archived, disabled

3. **`GITHUB_REPORT.md`** - Comprehensive Markdown report with:
   - Summary statistics
   - Top languages breakdown
   - Formatted tables with your most active repositories
   - Your most starred repositories

## Examples

### Complete Analysis

```bash
# Full analysis with custom username
uv run gh-inventory --user octocat

# Quick analysis of just your repos
uv run gh-inventory --user hsb3 --owned-only --no-report

# Large account with limit
uv run gh-inventory --user sindresorhus --limit 100
```

### Report Generation

```bash
# Generate fresh data and report
uv run gh-inventory --user hsb3

# Update report from existing data
uv run gh-inventory --report-only

# Custom report with specific user
uv run gh-inventory --report-only --user octocat
```

## Troubleshooting

### GitHub CLI Authentication Issues

```bash
# Check if authenticated
gh auth status

# Re-authenticate if needed
gh auth login
```

## Development

### Setup Development Environment

```bash
git clone https://github.com/hsb3/github-inventory.git
cd github-inventory
uv sync --all-groups
```

### Code Quality

```bash
# Run all development checks
make dev
```

### Project Structure

```
github-inventory/
├── src/github_inventory/
│   ├── __init__.py
│   ├── cli.py          # Command-line interface
│   ├── inventory.py    # Repository data collection
│   └── report.py       # Markdown report generation
├── main.py             # Entry point
├── pyproject.toml      # Project configuration
└── README.md           # This file
```