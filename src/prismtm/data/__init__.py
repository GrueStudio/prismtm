"""
Data management submodule providing core functionality for data operations.
"""

# Import the main concierge class
from .core import DataCore
from .backup import BackupManager
# Import the engine classes for direct access if needed
from .migrate import MigrationEngine

# Define what gets imported with `from data import *`
__all__ = [
    'DataCore',
    'BackupManager',
    'MigrationEngine'
]
