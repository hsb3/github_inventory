# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GitHub Inventory is a CLI tool that uses the GitHub CLI (`gh`) to gather comprehensive information about GitHub repositories and starred projects. It exports data to CSV files and generates detailed Markdown reports.

**Core Architecture:**
- `src/github_inventory/cli.py` - Command-line interface and argument parsing
- `src/github_inventory/inventory.py` - Repository data collection using GitHub CLI subprocess calls
- `src/github_inventory/report.py` - Markdown report generation and CSV data reading
- `src/github_inventory/batch.py` - Batch processing with JSON/YAML configuration support
- Main entry point: `ghscan` script in pyproject.toml calls `github_inventory.cli:main`

**Key Dependencies:**
- Requires GitHub CLI (`gh`) installed and authenticated
- Uses `pandas>=1.3.0` for data processing
- Uses `pydantic>=2.0.0` for configuration validation
- Uses `pyyaml>=6.0.0` for YAML config file support
- Uses `pre-commit>=3.0.0` for automated code quality hooks
- Uses Python `subprocess` module to execute `gh` commands

## Development Commands

### Setup

```bash
make setup    # Recommended: sets up venv, installs deps, configures pre-commit
# OR manually:
uv venv --python 3.12
uv sync --all-extras
```

### Code Quality

```bash
# Format code
make format   # Uses ruff format + black

# Lint code
make lint     # Uses ruff check

# Type checking
make typecheck # Uses mypy

# Install pre-commit hooks
make hooks
```

### Makefile Commands (Recommended)

```bash
make          # Show help menu with available commands
make setup    # Complete setup: install deps, hooks, run tests
make install  # Install dependencies only
make hooks    # Install and run pre-commit hooks
make format   # Format code with ruff + black
make lint     # Lint code with ruff
make typecheck # Type check with mypy
make test     # Run tests
make clean    # Clean cache and build files (including .venv)
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
PYTHONPATH=src python -m pytest tests/test_report.py -v

# Test quick command
make test
```

### Running the Tool

```bash
# Install as CLI command
uv pip install -e .

# Basic usage
ghscan --user <username>

# Common development test (replace username with your GitHub username)
ghscan --user username --owned-only --no-report

# Run example via Makefile
make example  # Runs sindresorhus with 50 repo limit
```

## Key Implementation Details

**GitHub CLI Integration:**
- All data collection done via `subprocess` calls to `gh` commands
- Uses JSON output format for structured data parsing
- Implements pagination for starred repositories via `--paginate` flag
- Branch counting done via direct GitHub API calls using `gh api`

**Data Collection Flow:**
1. `collect_owned_repositories()` - Uses `gh repo list` with JSON output
2. `collect_starred_repositories()` - Uses `gh api user/starred --paginate`
3. Both functions call `get_branch_count()` for each repo individually
4. Data formatted and written to CSV via `write_to_csv()`

**CLI Entry Points:**
- Package defines `ghscan` script that calls `github_inventory.cli:main`
- CLI supports modes: full collection, owned-only, starred-only, report-only
- Batch processing: `--batch` (defaults) or `--config filename.yaml/json`
- Username is required via `--user` flag or `GITHUB_USERNAME` environment variable
- Environment variables loaded from `.env` file (copy from `.env.example`)

**Configuration Management:**
- Centralized configuration using Pydantic validation (`src/github_inventory/config.py`)
- All environment variables are validated and provide helpful error messages
- Configuration supports defaults that automatically adapt to the specified username
- Path override logic is centralized and simplified compared to previous versions

## Testing and Authentication

The tool requires GitHub CLI authentication. Test with:

```bash
gh auth status
```

If authentication fails:

```bash
gh auth login
```

The tool collects repository metadata including private repository information, so proper authentication scope is required.

## Markdown Style Guidelines

When editing README.md or other markdown files, follow these formatting rules to pass pymarkdown linting:

- **MD022**: Always add blank lines above and below headings
- **MD040**: Specify language for all fenced code blocks (e.g., ```bash, ```python)
- Avoid line lengths over 80 characters when possible (MD013 disabled but good practice)

These files are excluded from markdown linting: TODO.md, CLAUDE.md
