"""
Prism Task Manager - A hierarchical task management system for software development.

This package provides tools for organizing work through a hierarchical structure:
Phase → Milestone → Block → Task → Subtask
"""

from .version import VERSION, APP_SCHEMA_VERSION
from .models import (
    TaskStatus,
    TaskPath,
    TaskTree,
    ProjectBugList,
    GlobalBugList
)
from .data import DataCore

__version__ = VERSION
__author__ = "GenGrue"
__email__ = "dev.grue.studio@gmail.com"

__all__ = [
    "VERSION",
    "APP_SCHEMA_VERSION",
    "TaskStatus",
    "TaskPath",
    "TaskTree",
    "ProjectBugList",
    "GlobalBugList",
    "DataCore"
]
