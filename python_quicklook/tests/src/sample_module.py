#!/usr/bin/env python3
"""
Sample Python module for testing codebase analysis tools.
"""

import os
import sys
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class User:
    """Represents a user in the system."""
    username: str
    email: str
    active: bool = True

    def get_display_name(self) -> str:
        """Get the user's display name."""
        return f"{self.username} <{self.email}>"


class DatabaseManager:
    """Handles database operations."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connected = False

    def connect(self) -> bool:
        """Establish database connection."""
        # Mock connection logic
        self.connected = True
        return True

    def get_users(self) -> List[User]:
        """Retrieve all users from database."""
        if not self.connected:
            raise RuntimeError("Not connected to database")
        return []

    def create_user(self, user: User) -> bool:
        """Create a new user in the database."""
        if not self.connected:
            return False
        return True


def process_user_data(users: List[User], filter_active: bool = True) -> Dict[str, List[str]]:
    """Process user data and return categorized results."""
    result = {"active": [], "inactive": []}

    for user in users:
        category = "active" if user.active else "inactive"
        result[category].append(user.username)

    if filter_active:
        return {"active": result["active"]}
    return result


def main():
    """Main function to demonstrate the module."""
    db = DatabaseManager("sqlite:///users.db")
    if db.connect():
        users = db.get_users()
        processed = process_user_data(users)
        print(f"Processed {len(processed)} user categories")


if __name__ == "__main__":
    main()
