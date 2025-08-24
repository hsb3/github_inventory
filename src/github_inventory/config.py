#!/usr/bin/env python3
"""
Configuration management for GitHub Inventory tool
Handles hierarchical configuration loading from multiple sources
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


def get_config_paths() -> list[Path]:
    """
    Get configuration file paths in order of priority (highest to lowest).
    
    Returns:
        List of Path objects in priority order:
        1. Current directory .env (highest priority)
        2. ~/.config/ghscan/.env (XDG config directory)
        3. ~/.ghscan/.env (legacy global config)
    """
    config_paths = []
    
    # 1. Current directory .env (project-specific, highest priority)
    current_env = Path.cwd() / ".env"
    config_paths.append(current_env)
    
    # 2. XDG config directory (standard Linux/Unix config location)
    xdg_config_dir = Path.home() / ".config" / "ghscan"
    xdg_env = xdg_config_dir / ".env"
    config_paths.append(xdg_env)
    
    # 3. Legacy global config directory (backward compatibility)
    legacy_config_dir = Path.home() / ".ghscan"
    legacy_env = legacy_config_dir / ".env"
    config_paths.append(legacy_env)
    
    return config_paths


def load_hierarchical_config() -> None:
    """
    Load configuration from multiple sources in hierarchical order.
    
    Configuration precedence (highest to lowest):
    1. Current directory .env file
    2. ~/.config/ghscan/.env (XDG standard)
    3. ~/.ghscan/.env (legacy location)
    4. Environment variables (already loaded)
    
    Later configs will not override earlier ones due to dotenv behavior.
    """
    config_paths = get_config_paths()
    
    # Load configs in reverse order so higher priority configs override lower ones
    for config_path in reversed(config_paths):
        if config_path.exists():
            load_dotenv(config_path, override=False)


def get_config_info() -> dict[str, str]:
    """
    Get information about current configuration sources.
    
    Returns:
        Dictionary with config file paths and their existence status
    """
    config_paths = get_config_paths()
    config_info = {}
    
    for i, config_path in enumerate(config_paths, 1):
        priority_names = ["Current directory", "XDG config", "Legacy global"]
        name = priority_names[i-1] if i <= len(priority_names) else f"Config {i}"
        
        config_info[name] = {
            "path": str(config_path),
            "exists": config_path.exists(),
            "readable": config_path.exists() and os.access(config_path, os.R_OK)
        }
    
    return config_info


def ensure_global_config_dir() -> Path:
    """
    Ensure the global configuration directory exists.
    Prefers XDG standard location over legacy location.
    
    Returns:
        Path to the global configuration directory
    """
    # Prefer XDG config directory
    xdg_config_dir = Path.home() / ".config" / "ghscan"
    legacy_config_dir = Path.home() / ".ghscan"
    
    # If legacy directory exists but XDG doesn't, use legacy
    if legacy_config_dir.exists() and not xdg_config_dir.exists():
        return legacy_config_dir
    
    # Otherwise use XDG standard location
    xdg_config_dir.mkdir(parents=True, exist_ok=True)
    return xdg_config_dir