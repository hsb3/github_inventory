# GitHub Inventory

[![CI](https://github.com/hsb3/github_inventory/workflows/CI/badge.svg)](https://github.com/hsb3/github_inventory/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![GitHub CLI Required](https://img.shields.io/badge/requires-GitHub%20CLI-blue?logo=github)](https://cli.github.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: ruff](https://img.shields.io/badge/linting-ruff-red)](https://github.com/astral-sh/ruff)
[![Type checking: mypy](https://img.shields.io/badge/type%20checking-mypy-blue)](https://mypy-lang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub issues](https://img.shields.io/github/issues/hsb3/github_inventory)](https://github.com/hsb3/github_inventory/issues)

CLI tool for generating comprehensive GitHub repository inventories and reports

## Key Features

• **Repository Analysis** - Analyzes owned and starred repositories with detailed metadata  
• **Professional Reports** - Generates Markdown reports with statistics and language breakdowns  
• **Batch Processing** - Process multiple GitHub accounts at once with configuration files  
• **CSV Export** - Export data for further analysis in spreadsheet tools  
• **Rate Limit Friendly** - Built-in limits for large accounts to avoid GitHub API limits

📊 **[View Example Report](docs/output_example/README.md)** - See what the generated report looks like

## Quick Start

```bash
# Clone and run
git clone https://github.com/hsb3/github_inventory.git
cd github_inventory && uv sync
uv run ghscan --user octocat
```

Requires [GitHub CLI](https://cli.github.com/) authenticated with `gh auth login`

## Basic Usage

```bash
# Full analysis (owned + starred repos)
uv run ghscan --user username

# Just your repositories
uv run ghscan --user username --owned-only

# Limit results for large accounts  
uv run ghscan --user sindresorhus --limit 50

# Batch process multiple accounts
uv run ghscan --batch

# Custom configuration file (JSON/YAML)
uv run ghscan --config accounts.yaml
```

## Configuration Files

For batch processing multiple accounts, create a JSON or YAML configuration file:

```yaml
# accounts.yaml
configs:
  - account: "langchain-ai"
    limit: 100
  - account: "microsoft" 
  - account: "google"
    limit: 50
```

```bash
# Use the configuration
uv run ghscan --config accounts.yaml
```

**Note**: Configuration files are **not** automatically detected - you must specify them with `--config filename`. Supports `.json`, `.yml`, and `.yaml` extensions.

## Environment Configuration

The tool automatically loads settings from a `.env` file in the project root:

```bash
# .env
GITHUB_USERNAME=your-username          # Default username
REPORT_OWNED_LIMIT=30                 # Max owned repos in reports (-1 = no limit)  
REPORT_STARRED_LIMIT=25               # Max starred repos in reports (-1 = no limit)
OWNED_REPOS_CSV=docs/user/repos.csv   # Output paths
```

Copy `.env.example` to `.env` and customize as needed. Environment variables override CLI defaults.

## Output

Creates three files in `docs/username/`:

- `repos.csv` - Owned repository data
- `starred_repos.csv` - Starred repository data  
- `README.md` - Professional report with statistics and tables

## Prerequisites

- Python 3.12+
- GitHub CLI installed and authenticated (`gh auth login`)
- `uv` package manager

## Documentation

- [Contributing Guidelines](CONTRIBUTING.md)
- [Documentation Overview](docs/README.md)

## License

MIT