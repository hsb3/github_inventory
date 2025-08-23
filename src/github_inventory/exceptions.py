#!/usr/bin/env python3
"""
GitHub Inventory Custom Exceptions

This module provides a hierarchy of custom exceptions for consistent error handling
throughout the GitHub Inventory application.
"""


class GitHubInventoryError(Exception):
    """Base exception for all GitHub Inventory errors"""

    def __init__(self, message: str, details: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class GitHubCLIError(GitHubInventoryError):
    """Raised when GitHub CLI commands fail"""

    def __init__(self, command: str, stderr: str | None = None, exit_code: int | None = None) -> None:
        message = f"GitHub CLI command failed: {command}"
        super().__init__(message, stderr)
        self.command = command
        self.stderr = stderr
        self.exit_code = exit_code


class ConfigurationError(GitHubInventoryError):
    """Raised when configuration is invalid or cannot be loaded"""

    def __init__(self, config_file: str | None = None, message: str = "Configuration error") -> None:
        if config_file:
            message = f"Configuration error in {config_file}"
        super().__init__(message)
        self.config_file = config_file


class DataProcessingError(GitHubInventoryError):
    """Raised when data processing fails (JSON parsing, CSV operations, etc.)"""

    def __init__(self, operation: str, details: str | None = None) -> None:
        message = f"Data processing failed: {operation}"
        super().__init__(message, details)
        self.operation = operation


class AuthenticationError(GitHubInventoryError):
    """Raised when GitHub authentication fails"""

    def __init__(self, message: str = "GitHub authentication failed") -> None:
        super().__init__(message)


class FileOperationError(GitHubInventoryError):
    """Raised when file operations fail"""

    def __init__(self, filepath: str, operation: str, details: str | None = None) -> None:
        message = f"File operation failed: {operation} on {filepath}"
        super().__init__(message, details)
        self.filepath = filepath
        self.operation = operation