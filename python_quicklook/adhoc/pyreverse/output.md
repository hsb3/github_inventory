# Code Structure Analysis - PyReverse Method
Generated on: Mon Aug 25 09:32:36 EDT 2025

### Detailed Analysis:

#### Module: batch
**Classes:**
- RunConfig
- ConfigsToRun
**Functions:**
- get_default_configs()
- load_config_from_file()
- create_output_directory()
- process_single_account()
- run_batch_processing()

#### Module: cli
**Classes:**
- PathManager
  - __init__()
  - _get_output_base()
  - get_owned_csv_path()
  - get_starred_csv_path()
  - get_report_md_path()
  - _is_default_path()
  - ensure_output_directory()
**Functions:**
- handle_batch_processing()
- collect_repository_data()
- generate_outputs()
- open_directory()
- create_parser()
- print_summary()
- main()

#### Module: exceptions
**Classes:**
- GitHubInventoryError
  - __init__()
  - __str__()
- GitHubCLIError
  - __init__()
- ConfigurationError
  - __init__()
- DataProcessingError
  - __init__()
- AuthenticationError
  - __init__()
- FileOperationError
  - __init__()

#### Module: github_client
**Classes:**
- GitHubClient
  - run_command()
  - api_request()
- CLIGitHubClient
  - run_command()
  - api_request()
- APIGitHubClient
  - __init__()
  - run_command()
  - api_request()
- MockGitHubClient
  - __init__()
  - set_response()
  - run_command()
  - api_request()
**Functions:**
- create_github_client()

#### Module: report
**Functions:**
- read_csv_data()
- format_number()
- format_size_mb()
- truncate_description()
- create_owned_repos_table()
- create_starred_repos_table()
- create_summary_section()
- create_footer()
- generate_markdown_report()

#### Module: inventory
**Functions:**
- run_gh_command()
- get_repo_list()
- get_branch_count()
- format_date()
- collect_owned_repositories()
- get_starred_repos()
- collect_starred_repositories()
- write_to_csv()
