# Code Structure Analysis - Ripgrep Method
Generated on: Mon Aug 25 08:35:29 EDT 2025

## Classes
- class APIGitHubClient
- class AuthenticationError
- class CLIGitHubClient
- class ConfigsToRun
- class ConfigurationError
- class DataProcessingError
- class FileOperationError
- class GitHubClient
- class GitHubCLIError
- class GitHubInventoryError
- class MockGitHubClient
- class PathManager
- class RunConfig

## Functions (standalone)
- def collect_owned_repositories
- def collect_repository_data
- def collect_starred_repositories
- def create_footer
- def create_github_client
- def create_output_directory
- def create_owned_repos_table
- def create_parser
- def create_starred_repos_table
- def create_summary_section
- def format_date
- def format_number
- def format_size_mb
- def generate_markdown_report
- def generate_outputs
- def get_branch_count
- def get_default_configs
- def get_repo_list
- def get_starred_repos
- def handle_batch_processing
- def load_config_from_file
- def main
- def open_directory
- def print_summary
- def process_single_account
- def read_csv_data
- def run_batch_processing
- def run_gh_command
- def truncate_description
- def write_to_csv

## Methods (indented functions)
- def __init__
- def __str__
- def _get_output_base
- def _is_default_path
- def api_request
- def ensure_output_directory
- def get_owned_csv_path
- def get_report_md_path
- def get_starred_csv_path
- def run_command
- def set_response

## Detailed File Analysis
### Module: __init__
**File:** src/github_inventory/__init__.py

**Classes:**

**Functions:**

**Methods:**

**Imports:**

---

### Module: batch
**File:** src/github_inventory/batch.py

**Classes:**
- class RunConfig(BaseModel):
- class ConfigsToRun(BaseModel):

**Functions:**
- def get_default_configs(
- def load_config_from_file(
- def create_output_directory(
- def process_single_account(
- def run_batch_processing(

**Methods:**

**Imports:**
- import
- from
- from
- import
- from
- from
- from
- from

---

### Module: cli
**File:** src/github_inventory/cli.py

**Classes:**
- class PathManager:

**Functions:**
- def handle_batch_processing(
- def collect_repository_data(
- def generate_outputs(
- def open_directory(
- def create_parser(
- def print_summary(
- def main(

**Methods:**
- def __init__(
- def _get_output_base(
- def get_owned_csv_path(
- def get_starred_csv_path(
- def get_report_md_path(
- def _is_default_path(
- def ensure_output_directory(

**Imports:**
- import
- import
- import
- import
- import
- from
- from
- from
- from
- from
- from
- from

---

### Module: exceptions
**File:** src/github_inventory/exceptions.py

**Classes:**
- class GitHubInventoryError(Exception):
- class GitHubCLIError(GitHubInventoryError):
- class ConfigurationError(GitHubInventoryError):
- class DataProcessingError(GitHubInventoryError):
- class AuthenticationError(GitHubInventoryError):
- class FileOperationError(GitHubInventoryError):

**Functions:**

**Methods:**
- def __init__(
- def __str__(
- def __init__(
- def __init__(
- def __init__(
- def __init__(
- def __init__(

**Imports:**
- from

---

### Module: github_client
**File:** src/github_inventory/github_client.py

**Classes:**
- class GitHubClient(ABC):
- class CLIGitHubClient(GitHubClient):
- class APIGitHubClient(GitHubClient):
- class MockGitHubClient(GitHubClient):

**Functions:**
- def create_github_client(

**Methods:**
- def run_command(
- def api_request(
- def run_command(
- def api_request(
- def __init__(
- def run_command(
- def api_request(
- def __init__(
- def set_response(
- def run_command(
- def api_request(

**Imports:**
- import
- import
- import
- import
- import
- from
- from
- from

---

### Module: inventory
**File:** src/github_inventory/inventory.py

**Classes:**

**Functions:**
- def run_gh_command(
- def get_repo_list(
- def get_branch_count(
- def format_date(
- def collect_owned_repositories(
- def get_starred_repos(
- def collect_starred_repositories(
- def write_to_csv(

**Methods:**

**Imports:**
- import
- import
- from
- from
- from
- from

---

### Module: report
**File:** src/github_inventory/report.py

**Classes:**

**Functions:**
- def read_csv_data(
- def format_number(
- def format_size_mb(
- def truncate_description(
- def create_owned_repos_table(
- def create_starred_repos_table(
- def create_summary_section(
- def create_footer(
- def generate_markdown_report(

**Methods:**

**Imports:**
- import
- import
- from
- from

---

## Summary Statistics
- **Total Python files:**        7
- **Total classes:**       13
- **Total functions:**       30
- **Total methods:**       25
- **Total imports:**       39
