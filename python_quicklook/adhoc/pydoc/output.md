# Code Structure Analysis - PyDoc Method
Generated on: Mon Aug 25 08:36:51 EDT 2025

## Module: github_inventory.batch
### Classes:
- **ConfigsToRun**
  - __class_getitem__()
  - __get_pydantic_core_schema__()
  - __get_pydantic_json_schema__()
  - __pydantic_init_subclass__()
  - _get_value()
  - construct()
  - from_orm()
  - model_construct()
  - model_json_schema()
  - model_parametrized_name()
  - model_rebuild()
  - model_validate()
  - model_validate_json()
  - model_validate_strings()
  - parse_file()
  - parse_obj()
  - parse_raw()
  - schema()
  - schema_json()
  - update_forward_refs()
  - validate()
  - __copy__()
  - __deepcopy__()
  - __delattr__()
  - __eq__()
  - __getattr__()
  - __getstate__()
  - __init__()
  - __iter__()
  - __pretty__()
  - __replace__()
  - __repr__()
  - __repr_args__()
  - __repr_name__()
  - __repr_recursion__()
  - __repr_str__()
  - __rich_repr__()
  - __setattr__()
  - __setstate__()
  - __str__()
  - _calculate_keys()
  - _copy_and_set_values()
  - _iter()
  - _setattr_handler()
  - copy()
  - dict()
  - json()
  - model_copy()
  - model_dump()
  - model_dump_json()
  - model_post_init()
- **RunConfig**
  - __class_getitem__()
  - __get_pydantic_core_schema__()
  - __get_pydantic_json_schema__()
  - __pydantic_init_subclass__()
  - _get_value()
  - construct()
  - from_orm()
  - model_construct()
  - model_json_schema()
  - model_parametrized_name()
  - model_rebuild()
  - model_validate()
  - model_validate_json()
  - model_validate_strings()
  - parse_file()
  - parse_obj()
  - parse_raw()
  - schema()
  - schema_json()
  - update_forward_refs()
  - validate()
  - __copy__()
  - __deepcopy__()
  - __delattr__()
  - __eq__()
  - __getattr__()
  - __getstate__()
  - __init__()
  - __iter__()
  - __pretty__()
  - __replace__()
  - __repr__()
  - __repr_args__()
  - __repr_name__()
  - __repr_recursion__()
  - __repr_str__()
  - __rich_repr__()
  - __setattr__()
  - __setstate__()
  - __str__()
  - _calculate_keys()
  - _copy_and_set_values()
  - _iter()
  - _setattr_handler()
  - copy()
  - dict()
  - json()
  - model_copy()
  - model_dump()
  - model_dump_json()
  - model_post_init()

### Functions:
- **create_output_directory**(account: str, base_dir: str = 'docs') -> pathlib._local.Path
- **get_default_configs**() -> github_inventory.batch.ConfigsToRun
- **load_config_from_file**(config_file: str) -> github_inventory.batch.ConfigsToRun
- **process_single_account**(config: github_inventory.batch.RunConfig, base_dir: str = 'docs') -> bool
- **run_batch_processing**(configs: github_inventory.batch.ConfigsToRun, base_dir: str = 'docs') -> None

## Module: github_inventory.cli
### Classes:
- **PathManager**
  - __init__()
  - _get_output_base()
  - _is_default_path()
  - ensure_output_directory()
  - get_owned_csv_path()
  - get_report_md_path()
  - get_starred_csv_path()

### Functions:
- **collect_repository_data**(args, path_manager: github_inventory.cli.PathManager, client=None) -> tuple
- **create_parser**()
- **generate_outputs**(owned_repos: List[Dict[str, Any]], starred_repos: List[Dict[str, Any]], args, path_manager: github_inventory.cli.PathManager) -> bool
- **handle_batch_processing**(args) -> None
- **main**()
- **open_directory**(directory_path)
- **print_summary**(owned_repos, starred_repos)

## Module: github_inventory.exceptions
### Classes:
- **AuthenticationError**
  - __init__()
  - __str__()
- **ConfigurationError**
  - __init__()
  - __str__()
- **DataProcessingError**
  - __init__()
  - __str__()
- **FileOperationError**
  - __init__()
  - __str__()
- **GitHubCLIError**
  - __init__()
  - __str__()
- **GitHubInventoryError**
  - __init__()
  - __str__()

### Functions:

## Module: github_inventory.github_client
### Classes:
- **APIGitHubClient**
  - __init__()
  - api_request()
  - run_command()
- **CLIGitHubClient**
  - api_request()
  - run_command()
- **GitHubClient**
  - api_request()
  - run_command()
- **MockGitHubClient**
  - __init__()
  - api_request()
  - run_command()
  - set_response()

### Functions:
- **create_github_client**(client_type: str = 'cli', github_token: Optional[str] = None) -> github_inventory.github_client.GitHubClient

## Module: github_inventory.inventory
### Classes:

### Functions:
- **collect_owned_repositories**(username, limit=None, client: Optional[github_inventory.github_client.GitHubClient] = None)
- **collect_starred_repositories**(username=None, limit=None, client: Optional[github_inventory.github_client.GitHubClient] = None)
- **format_date**(date_str)
- **get_branch_count**(owner, repo_name, client: Optional[github_inventory.github_client.GitHubClient] = None)
- **get_repo_list**(username, limit=None, client: Optional[github_inventory.github_client.GitHubClient] = None)
- **get_starred_repos**(username=None, limit=None, client: Optional[github_inventory.github_client.GitHubClient] = None)
- **run_gh_command**(cmd, client: Optional[github_inventory.github_client.GitHubClient] = None)
- **write_to_csv**(repos, filename, headers=None)

## Module: github_inventory.report
### Classes:

### Functions:
- **create_footer**()
- **create_owned_repos_table**(repos_data, limit_applied=None)
- **create_starred_repos_table**(starred_data, limit_applied=None)
- **create_summary_section**(username='hsb3')
- **format_number**(value)
- **format_size_mb**(value)
- **generate_markdown_report**(owned_repos=None, starred_repos=None, username='hsb3', output_file='github_inventory_report.md', limit_applied=None)
- **read_csv_data**(filename)
- **truncate_description**(description, max_length=80)
