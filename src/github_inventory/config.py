#!/usr/bin/env python3
"""
Configuration Management Module for GitHub Inventory

Provides centralized configuration management using Pydantic for validation
and consistent handling of environment variables and user settings.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator


class Config(BaseModel):
    """Centralized configuration for GitHub Inventory tool
    
    This class handles all configuration settings including:
    - Environment variable loading and validation
    - Default path generation
    - User preferences and limits
    - Output directory management
    """
    
    # Core settings
    username: str = Field(
        default="",
        description="GitHub username to analyze"
    )
    
    # Output configuration
    output_base: str = Field(
        default="docs",
        description="Base directory for output files"
    )
    
    owned_csv: Optional[str] = Field(
        default=None,
        description="Path to owned repositories CSV file"
    )
    
    starred_csv: Optional[str] = Field(
        default=None,
        description="Path to starred repositories CSV file"
    )
    
    report_md: Optional[str] = Field(
        default=None,
        description="Path to markdown report file"
    )
    
    # Report display limits
    report_owned_limit: int = Field(
        default=30,
        ge=-1,
        description="Maximum owned repositories to display in report (-1 for unlimited)"
    )
    
    report_starred_limit: int = Field(
        default=25,
        ge=-1,
        description="Maximum starred repositories to display in report (-1 for unlimited)"
    )
    
    # Environment variables loaded
    _env_loaded: bool = False
    
    class Config:
        """Pydantic configuration"""
        validate_assignment = True
        extra = "forbid"
    
    @validator('username', pre=True, always=True)
    def set_username(cls, v):
        """Set username from environment if not provided"""
        if not v:
            return os.getenv("GITHUB_USERNAME", "")
        return v
    
    @validator('report_owned_limit', pre=True, always=True)
    def validate_owned_limit(cls, v):
        """Validate and set owned repositories display limit"""
        if isinstance(v, str):
            return int(v)
        return v
    
    @validator('report_starred_limit', pre=True, always=True)
    def validate_starred_limit(cls, v):
        """Validate and set starred repositories display limit"""
        if isinstance(v, str):
            return int(v)
        return v


def get_output_base() -> str:
    """Get the base output directory from environment or default"""
    return os.getenv("OUTPUT_BASE", "docs")


def load_config(
    username: Optional[str] = None,
    owned_csv: Optional[str] = None,
    starred_csv: Optional[str] = None,
    report_md: Optional[str] = None,
    load_env: bool = True
) -> Config:
    """Load and validate configuration from environment and parameters
    
    Args:
        username: GitHub username (overrides environment)
        owned_csv: Path to owned repositories CSV
        starred_csv: Path to starred repositories CSV  
        report_md: Path to markdown report
        load_env: Whether to load .env file
    
    Returns:
        Config: Validated configuration object
        
    Raises:
        ValueError: If configuration validation fails
    """
    if load_env:
        load_dotenv()
    
    # Get base configuration from environment
    config_data = {
        'output_base': get_output_base(),
        'report_owned_limit': int(os.getenv("REPORT_OWNED_LIMIT", "30")),
        'report_starred_limit': int(os.getenv("REPORT_STARRED_LIMIT", "25"))
    }
    
    # Override with provided parameters
    if username:
        config_data['username'] = username
    
    # Create config instance
    config = Config(**config_data)
    
    # Set default paths if not provided
    if not owned_csv and not config.owned_csv:
        if config.username:
            config.owned_csv = os.getenv(
                "OWNED_REPOS_CSV", 
                f"{config.output_base}/{config.username}/repos.csv"
            )
    elif owned_csv:
        config.owned_csv = owned_csv
    
    if not starred_csv and not config.starred_csv:
        if config.username:
            config.starred_csv = os.getenv(
                "STARRED_REPOS_CSV",
                f"{config.output_base}/{config.username}/starred_repos.csv"
            )
    elif starred_csv:
        config.starred_csv = starred_csv
    
    if not report_md and not config.report_md:
        if config.username:
            config.report_md = os.getenv(
                "REPORT_OUTPUT_MD",
                f"{config.output_base}/{config.username}/README.md"
            )
    elif report_md:
        config.report_md = report_md
    
    return config


def validate_config(config: Config) -> None:
    """Validate configuration and provide helpful error messages
    
    Args:
        config: Configuration to validate
        
    Raises:
        ValueError: If configuration is invalid with descriptive message
    """
    if not config.username:
        raise ValueError(
            "GitHub username is required. Please provide it via:\n"
            "  - Command line: --user <username>\n"
            "  - Environment variable: GITHUB_USERNAME=<username>\n"
            "  - .env file: GITHUB_USERNAME=<username>"
        )
    
    # Validate paths are strings if provided
    for path_field, path_value in [
        ("owned_csv", config.owned_csv),
        ("starred_csv", config.starred_csv), 
        ("report_md", config.report_md)
    ]:
        if path_value is not None and not isinstance(path_value, str):
            raise ValueError(f"{path_field} must be a string path, got {type(path_value)}")


def ensure_output_directory(config: Config) -> None:
    """Ensure output directories exist for the configuration
    
    Args:
        config: Configuration with output paths
    """
    paths_to_check = [config.owned_csv, config.starred_csv, config.report_md]
    
    for path in paths_to_check:
        if path:
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)


def update_paths_for_username(config: Config, new_username: str) -> Config:
    """Update output paths when username changes dynamically
    
    This handles the complex path override logic that was previously
    scattered in cli.py by centralizing the path update rules.
    
    Args:
        config: Current configuration
        new_username: New username to use for paths
        
    Returns:
        Config: Updated configuration with new paths
    """
    # Only update paths that use the old username pattern or are default
    old_username = config.username
    base_output = config.output_base
    
    # Update owned CSV path
    if (config.owned_csv == f"{base_output}/{old_username}/repos.csv" or
        config.owned_csv and config.owned_csv.endswith("github_inventory_detailed.csv")):
        config.owned_csv = f"{base_output}/{new_username}/repos.csv"
    
    # Update starred CSV path  
    if (config.starred_csv == f"{base_output}/{old_username}/starred_repos.csv" or
        config.starred_csv and config.starred_csv.endswith("starred_repos.csv")):
        config.starred_csv = f"{base_output}/{new_username}/starred_repos.csv"
    
    # Update report MD path
    if (config.report_md == f"{base_output}/{old_username}/README.md" or
        config.report_md and config.report_md.endswith("github_inventory_report.md")):
        config.report_md = f"{base_output}/{new_username}/README.md"
    
    # Update username
    config.username = new_username
    
    return config


# Default configuration instance - can be imported and used directly
default_config = None


def get_default_config() -> Config:
    """Get a default configuration instance
    
    Returns:
        Config: Default configuration loaded from environment
    """
    global default_config
    if default_config is None:
        default_config = load_config()
    return default_config