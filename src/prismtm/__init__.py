"""
Prism Task Manager - A hierarchical task management system for software development.

This package provides tools for organizing work through a hierarchical structure:
Phase → Milestone → Block → Task → Subtask
"""

from .version import VERSION, APP_SCHEMA_VERSION
from .models import (
    TaskStatus,
    BugStatus,
    BugSeverity,
    TaskPath,
    TaskTree,
    ProjectBugList,
    GlobalBugList,
    ProjectTimeTracker,
)
from .data import DataCore

__version__ = VERSION
__author__ = "Your Name"
__email__ = "your.email@example.com"

__all__ = [
    "VERSION",
    "APP_SCHEMA_VERSION",
    "TaskStatus",
    "BugStatus",
    "BugSeverity",
    "TaskPath",
    "TaskTree",
    "ProjectBugList",
    "GlobalBugList",
    "ProjectTimeTracker",
    "DataCore",
]
