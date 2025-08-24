# Private Notes for `Github Inventory` Project

## Kanban

### **backlog**

### **in progress**

### **completed**

- [x] use Claude Code CLI with Github MCP to create inventory; repo name, url
- [x] create PRD for small project
- [x] create a small python project to programmatically assemble this information
- [x] add test suite
- [x] add code quality checks
- [x] add makefile for dev commands
- [x] add a .env file with basic config information; add .env.example as well
- [x] bug: fix/remove corrupted characters from readme.md
- [x] add quickstart to readme
- [x] change repo size KB -> MB in report
- [x] add test for --limit (apply to both owned and starred)
- [x] create readme; note prerequisite of installed github cli + authenticated session
- [x] implement change order #1
- [x] add PR and Issue template
- [x] add basic github workflows to prevent destructive changes to main branch
- [x] add pull request and issue submission instructions in docs/
- [x] add readme to docs/ with explanation of contents of docs/ --- exclude hidden folders
- [x] fix test_cli.py for code base change
- [x] add configurable limits for reports (owned & starred)
- [x] move CONTRIBUTING.md to root?
- [x] determine what value of config file name and extension is looked for.  how handle when there is both a yaml and json

---

## Developer Notes

### PRD

- create csv files with detailed information for owned and starred repos
- assemble the csv information into a report in .md format

### **technical choices**

- use gh cli to retrieve information
- use python 3.12
- no .python-version file -> pyproject.toml
- ruff, black, pytest, mypy for code quality -> pyproject.toml [dev dependencies]

### change order - #1

add functionality so that if i have a list of github accounts:

class RunConfig(BaseModel):
    account: str,
    limit: Optional(int) = None

class ConfigsToRun:
    List[RunConfig]

*do this for:*

- langchain-ai, limit=100
- aider-ai
- danny-avila
- coleam00
- dlt-hub

i can run report generator for all the accounts.
output will be a folder in docs like 'docs/langchain-ai'
with repos.csv, starred_repos.csv, README.md (the report)

### my `.env` file

```python
# GitHub Inventory Configuration
# Default configuration values

# Default GitHub username
GITHUB_USERNAME=hsb3

# Default output file paths
OWNED_REPOS_CSV=docs/hsb3/repos.csv
STARRED_REPOS_CSV=docs/hsb3/starred_repos.csv
REPORT_OUTPUT_MD=docs/hs3/README.md

# GitHub CLI settings (optional - uses system gh config by default)
# GITHUB_TOKEN=your_personal_access_token
```

### CLI command & option testing

`ghscan --help`

```bash
ghscan --help
usage: ghscan [-h] [--user USER] [--owned-only] [--starred-only] [--report-only] [--owned-csv OWNED_CSV] [--starred-csv STARRED_CSV] [--report-md REPORT_MD] [--no-report] [--limit LIMIT] [--version] [--open] [--batch] [--config CONFIG]
              [--client-type {cli,api}] [--github-token GITHUB_TOKEN]

GitHub Repository Inventory Tool

options:
  -h, --help            show this help message and exit
  --user USER, -u USER  GitHub username (default: hsb3)
  --owned-only          Only collect owned repositories
  --starred-only        Only collect starred repositories
  --report-only         Only generate markdown report from existing CSV files
  --owned-csv OWNED_CSV
                        Output file for owned repositories CSV (default: docs/hsb3/repos.csv)
  --starred-csv STARRED_CSV
                        Output file for starred repositories CSV (default: docs/hsb3/starred_repos.csv)
  --report-md REPORT_MD
                        Output file for markdown report (default: docs/hsb3/README.md)
  --no-report           Skip generating markdown report
  --limit LIMIT         Limit number of repositories to process (useful for large accounts)
  --version             show program's version number and exit
  --open                Open the output directory (docs) in your default file manager
  --batch               Run batch processing with default account configurations
  --config CONFIG       Run batch processing with custom configuration file (JSON/YAML)
  --client-type {cli,api}
                        GitHub client type to use: 'cli' (default) uses GitHub CLI, 'api' makes direct API calls
  --github-token GITHUB_TOKEN
                        GitHub personal access token (required when using --client-type=api)
```
