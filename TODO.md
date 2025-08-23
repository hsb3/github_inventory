# Private Notes for `Github Inventory` Project

## Kanban

**backlog**
- [x] create readme; note prerequisite of installed github cli + authenticated session

**in progress**

**completed**
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

---

## Developer Notes

### Objectives & Deliverables

### PRD

- create csv files with detailed information for owned and starred repos
- assemble the csv information into a report in .md format

**technical choices**
- use gh cli to retrieve information
- use python 3.12
- no .python-version file -> pyproject.toml
- ruff, black, pytest, mypy for code quality -> pyproject.toml [dev dependencies]

## my `.env` file

```python
# GitHub Inventory Configuration
# Default configuration values

# Default GitHub username
GITHUB_USERNAME=hsb3

# Default output file paths
OWNED_REPOS_CSV=docs/output/repos.csv
STARRED_REPOS_CSV=docs/output/starred_repos.csv
REPORT_OUTPUT_MD=docs/output/GITHUB_REPORT.md

# GitHub CLI settings (optional - uses system gh config by default)
# GITHUB_TOKEN=your_personal_access_token

```
