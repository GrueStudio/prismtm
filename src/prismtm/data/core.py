"""
DataCore - Central data validation and migration handler for Prism Task Manager.

This module provides the main interface for validating project and user data files,
checking schema versions, coordinating migrations, and handling backups.
"""
from prismtm.recovery import FatalError, MigrationNeededError
from .io import atomic_write, load_model, DATA_YAML
from pathlib import Path
from typing import Union
from .validate import find_schema_versions, validate_scope_schema, USER_SCOPE, PROJECT_SCOPE
from prismtm.version import APP_SCHEMA_VERSION
from prismtm.models import TaskTree, ProjectBugList, GlobalBugList, ProjectTimeTracker, BaseYAMLModel
from prismtm.logs import get_logger

try:
    from importlib.resources import files
except ImportError:
    # Python < 3.9 fallback
    from importlib_resources import files

log = get_logger("data")

class UserScope:
    """Provides access to model files within a scope (project or user)."""

    def __init__(self, basepath : Path):
        self.basepath = basepath
        self.bugs : Union[BaseYAMLModel, None] = load_model(GlobalBugList, basepath / "bugs.yml")
        if self.bugs == None:
            self.bugs = GlobalBugList()

    def save_all(self):
        """Save all loaded models back to their files."""
        if self.bugs != None:
            atomic_write(DATA_YAML, self.basepath / "bugs.yml", self.bugs.model_dump())

class ProjectScope:
    """Provides access to model files within a scope (project or user)."""

    def __init__(self, basepath : Path):
        self.basepath = basepath
        self.tasktree = load_model(TaskTree, basepath / "tasktree.yml")
        self.bugs = load_model(ProjectBugList, basepath / "bugs.yml")
        self.time = load_model(ProjectTimeTracker, basepath / "time.yml")

    def save_all(self):
        """Save all loaded models back to their files."""
        if self.bugs != None and self.tasktree != None and self.time != None:
            atomic_write(DATA_YAML, self.basepath / "bugs.yml", self.bugs.model_dump())
            atomic_write(DATA_YAML, self.basepath / "tasktree.yml", self.tasktree.model_dump())
            atomic_write(DATA_YAML, self.basepath / "bugs.yml", self.time.model_dump())

class PrismContext:
    """Main context object providing access to project and user data."""

    def __init__(self):
        self.user = UserScope(DataCore.USER_DATA_DIR)
        self.project = ProjectScope(DataCore.PROJECT_DATA_DIR)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - save all changes."""
        self.save_all()

    def save_all(self):
        """Save all changes to both project and user files."""
        self.user.save_all()
        self.project.save_all()

class DataCore:
    PROJECT_DATA_DIR = Path(".prsm")
    USER_DATA_DIR = Path.home() / ".local" / "share" / "prismtm" / "data"
    context : PrismContext | None = None

    def load_context(self) -> PrismContext:
        if DataCore.context == None:
            DataCore.context = PrismContext()

        return DataCore.context

    def validate_context(self) -> bool:
        project_version, user_version = find_schema_versions()
        log.info(f"PROJECT: {project_version}; USER: {user_version}; APP: {APP_SCHEMA_VERSION};")
        if project_version != APP_SCHEMA_VERSION:
            raise MigrationNeededError("Project data and prism using inconcurrent versions, migrate data")
        elif user_version != APP_SCHEMA_VERSION:
            raise MigrationNeededError("User data and prism using inconcurrent versions, migrate data")
        elif not validate_scope_schema(USER_SCOPE, user_version):
            raise FatalError("user scope schema is not valid")
        elif not validate_scope_schema(PROJECT_SCOPE, project_version):
            raise FatalError("project scope schema is not valid")

        return True
