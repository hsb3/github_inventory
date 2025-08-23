# Documentation Directory

This directory contains documentation and example outputs for the GitHub Inventory tool.

## Contents

### Documentation Files
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Guidelines for submitting issues and pull requests
- **[GITHUB_CLI.md](GITHUB_CLI.md)** - GitHub CLI setup and authentication guide

### Example Output
- **[output_example/](output_example/)** - Sample output files demonstrating the tool's functionality
  - `README.md` - Generated report for sindresorhus (limited to 50 repos)
  - `repos.csv` - Repository data in CSV format
  - `starred_repos.csv` - Starred repositories data

### Generated User Data
The tool automatically creates user-specific directories when run:
- **`{username}/`** - Generated data for each analyzed GitHub user
  - `README.md` - Comprehensive inventory report
  - `repos.csv` - Owned repositories data
  - `starred_repos.csv` - Starred repositories data

#### Current User Data Directories
- **aider-ai/** - Analysis of aider-ai GitHub account
- **coleam00/** - Analysis of coleam00 GitHub account  
- **danny-avila/** - Analysis of danny-avila GitHub account
- **dlt-hub/** - Analysis of dlt-hub GitHub account
- **hsb3/** - Analysis of hsb3 GitHub account
- **langchain-ai/** - Analysis of langchain-ai GitHub account
- **testuser/** - Test user data directory

## File Structure
Each user directory follows this structure:
```
docs/{username}/
├── README.md           # Main inventory report
├── repos.csv          # Owned repositories (CSV)
└── starred_repos.csv   # Starred repositories (CSV)
```

## Generated Report Format
The `README.md` files contain:
- **Overview** - Account summary and methodology
- **Owned Repositories** - Table of repositories owned by the user
- **Starred Repositories** - Table of repositories starred by the user
- **Statistics** - Language breakdown, repository counts, visibility stats

## CSV Data Format

### repos.csv columns:
- `name` - Repository name
- `description` - Repository description
- `url` - GitHub URL
- `visibility` - public/private
- `is_fork` - TRUE/FALSE
- `creation_date` - When repository was created
- `last_update_date` - Last update timestamp
- `default_branch` - Default branch name (usually 'main')
- `number_of_branches` - Total branch count
- `primary_language` - Main programming language
- `size` - Repository size in KB

### starred_repos.csv columns:
- `name` - Repository name
- `full_name` - Owner/repository format
- `description` - Repository description
- `url` - GitHub URL
- `visibility` - public/private
- `is_fork` - TRUE/FALSE
- `creation_date` - Repository creation date
- `last_update_date` - Last update timestamp
- `primary_language` - Main programming language
- `stars` - Star count
- `forks` - Fork count
- `size` - Repository size in KB

## Usage Examples

### Analyze a specific user:
```bash
gh-inventory --user octocat
```
Creates: `docs/octocat/README.md`, `docs/octocat/repos.csv`, `docs/octocat/starred_repos.csv`

### Limit results for large accounts:
```bash
gh-inventory --user sindresorhus --limit 50
```

### Generate only CSV data:
```bash
gh-inventory --user hsb3 --no-report
```

### Batch processing multiple users:
```bash
gh-inventory --batch config_example.json
```

## Notes
- All timestamps are in the format: YYYY-MM-DD
- Repository sizes are converted from KB to MB in reports (but stored as KB in CSV)
- Private repositories require proper GitHub CLI authentication
- Generated files are excluded from git tracking (see `.gitignore`)

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on submitting issues and pull requests.