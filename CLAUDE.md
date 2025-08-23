# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GitHub Inventory is a CLI tool that uses the GitHub CLI (`gh`) to gather comprehensive information about GitHub repositories and starred projects. It exports data to CSV files and generates detailed Markdown reports.

**Core Architecture:**
- `src/github_inventory/cli.py` - Command-line interface and argument parsing
- `src/github_inventory/inventory.py` - Repository data collection using GitHub CLI subprocess calls
- `src/github_inventory/report.py` - Markdown report generation and CSV data reading
- `main.py` - Entry point that imports from cli module

**Key Dependencies:**
- Requires GitHub CLI (`gh`) installed and authenticated
- Uses `pandas>=1.3.0` for data processing
- Uses Python `subprocess` module to execute `gh` commands

## Development Commands

### Setup

```bash
uv venv
source .venv/bin/activate  # or 'activate' shortcut
uv pip install -e ".[dev]"
```

### Code Quality

```bash
# Format code
black src/

# Lint code
ruff src/

# Run tests (when available)
pytest
```

### Running the Tool

```bash
# Install as CLI command
uv pip install -e .

# Basic usage
ghscan --user <username>

# Common development test
ghscan --user hsb3 --owned-only --no-report
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
- Default username is "hsb3" but can be overridden with `--user` flag

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
