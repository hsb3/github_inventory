# Private Notes for `Github Inventory` Project

## Kanban

### **backlog**

- [ ] fix test_cli.py for code base change
- [ ] add configurable limits for reports (owned & starred)
- [ ] move CONTRIBUTING.md to root?
- [ ] determine what value of config file name and extension is looked for.  how handle when there is both a yaml and json

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

---

## Developer Notes

### Objectives & Deliverables

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

do this for:
- langchain-ai, limit=100
- aider-ai
- danny-avila
- coleam00
- dlt-hub

i can run report generator for all the accounts.
output will be a folder in docs like 'docs/langchain-ai'
with repos.csv, starred_repos.csv, README.md (the report)



---
## my `.env` file
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
