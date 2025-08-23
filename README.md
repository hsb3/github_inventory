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
- `uv` package manager (recommended) or `pip`

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
uv venv && source .venv/bin/activate && uv add -e .

# Try the example (50 repos from sindresorhus)
make example

# Or run with your username
gh-inventory --user YOUR_USERNAME --limit 20
```

The example generates comprehensive reports in `docs/output_example/` showing owned repositories, starred repositories, and statistics.

## Installation

### Using uv (recommended)

```bash
git clone https://github.com/hsb3/github-inventory.git
cd github-inventory
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv add -e .
```

### Using pip

```bash
git clone https://github.com/hsb3/github-inventory.git
cd github-inventory
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

## Usage

### Basic Usage

Generate a complete inventory for user "hsb3":

```bash
gh-inventory --user hsb3
```

This will:
1. Collect all owned repositories
2. Collect all starred repositories  
3. Generate CSV files for both
4. Create a comprehensive Markdown report

### Command Options

```bash
# Show help
gh-inventory --help

# Generate only owned repositories
gh-inventory --user hsb3 --owned-only

# Generate only starred repositories
gh-inventory --user hsb3 --starred-only

# Limit results for large accounts
gh-inventory --user sindresorhus --limit 50

# Generate report from existing CSV files
gh-inventory --report-only

# Custom output files
gh-inventory --user hsb3 \
    --owned-csv my_repos.csv \
    --starred-csv my_stars.csv \
    --report-md my_report.md

# Skip markdown report generation
gh-inventory --user hsb3 --no-report
```

### Output Files

The tool generates three main outputs:

1. **`github_inventory_detailed.csv`** - Your repositories with columns:
   - name, description, url, visibility, is_fork
   - creation_date, last_update_date, default_branch
   - number_of_branches, primary_language, size

2. **`starred_repos.csv`** - Your starred repositories with columns:
   - name, full_name, owner, description, url, visibility
   - is_fork, creation_date, last_update_date, last_push_date
   - default_branch, number_of_branches, primary_language, size
   - stars, forks, watchers, open_issues, license, topics
   - homepage, archived, disabled

3. **`github_inventory_report.md`** - Comprehensive Markdown report with:
   - Summary statistics
   - Top languages breakdown
   - Formatted tables with your most active repositories
   - Your most starred repositories

## Examples

### Complete Analysis

```bash
# Full analysis with custom username
gh-inventory --user octocat

# Quick analysis of just your repos
gh-inventory --user hsb3 --owned-only --no-report

# Large account with limit
gh-inventory --user sindresorhus --limit 100
```

### Report Generation

```bash
# Generate fresh data and report
gh-inventory --user hsb3

# Update report from existing data
gh-inventory --report-only

# Custom report with specific user
gh-inventory --report-only --user octocat
```

## Data Collected

### Repository Information
- Basic metadata (name, description, URL, visibility)
- Repository statistics (size, branches, creation/update dates)
- Language information and topics
- Fork status and branch details

### Starred Repository Information  
- All repository metadata plus:
- Star counts and fork counts
- Watchers and open issues
- License information
- Homepage and topics
- Archived/disabled status

## Requirements

- Requires GitHub CLI (`gh`) to be installed and authenticated
- Python 3.12+
- Internet connection for GitHub API access

## Troubleshooting

### GitHub CLI Authentication Issues

```bash
# Check if authenticated
gh auth status

# Re-authenticate if needed
gh auth login
```

### Rate Limiting
The tool respects GitHub API rate limits. For large numbers of repositories, the process may take some time.

### Missing Data
Some repository information may not be available for private repositories you don't have access to, or repositories that have been deleted.

## Development

### Setup Development Environment

```bash
git clone https://github.com/hsb3/github-inventory.git
cd github-inventory
uv venv
source .venv/bin/activate
uv add -e ".[dev]"
```

### Code Quality

```bash
# Format code
black src/

# Lint code  
ruff src/

# Run tests
pytest
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

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request
