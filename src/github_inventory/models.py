#!/usr/bin/env python3
"""
Pydantic models for GitHub repository data
Provides typed data structures for repository information
"""

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, Field


class RepositoryBase(BaseModel):
    """Base model for common repository fields"""

    name: str
    description: Optional[str] = ""
    url: str
    visibility: str
    is_fork: bool
    creation_date: Optional[str] = ""
    last_update_date: Optional[str] = ""
    default_branch: str
    number_of_branches: Union[int, str] = Field(
        description="Number of branches - int for successful API calls, 'unknown' for failures"
    )
    primary_language: Optional[str] = ""
    size: Optional[int] = Field(
        default=None, description="Repository size in KB for owned repos, or in bytes for starred repos"
    )


class OwnedRepository(RepositoryBase):
    """Model for owned repository data from 'gh repo list' command"""

    class Config:
        # Allow converting string boolean values to actual booleans
        str_to_bool = True


class StarredRepository(RepositoryBase):
    """Model for starred repository data from GitHub API"""

    full_name: str
    owner: str
    last_push_date: Optional[str] = ""
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    open_issues: int = 0
    license: Optional[str] = ""
    topics: Optional[str] = ""  # Comma-separated string of topics
    homepage: Optional[str] = ""
    archived: bool = False
    disabled: bool = False

    class Config:
        # Allow converting string boolean values to actual booleans
        str_to_bool = True


class BranchCount(BaseModel):
    """Model for branch count information"""

    repository_name: str
    owner: str
    count: Union[int, str]  # int for success, "unknown" for failure
    
    @property
    def is_known(self) -> bool:
        """Check if branch count is a known integer value"""
        return isinstance(self.count, int)