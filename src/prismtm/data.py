"""
DataCore - Central data validation and migration handler for Prism Task Manager.

This module provides the main interface for validating project and user data files,
checking schema versions, and coordinating migrations.
"""

import os
import json
import yaml
import tempfile
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List, Union
from packaging import version
try:
    from importlib.resources import files
except ImportError:
    # Python < 3.9 fallback
    from importlib_resources import files

from .migrate import MigrationEngine
from .validate import find_schema_version, validate_file_schema
from .version import APP_SCHEMA_VERSION
from .models import TaskTree, ProjectBugList, GlobalBugList, ProjectTimeTracker

class FileScope:
    """Provides access to model files within a scope (project or user)."""

    def __init__(self, scope_type: str, data_dir: Path, context: 'PrismContext'):
        self.scope_type = scope_type
        self.data_dir = data_dir
        self.context = context
        self._loaded_models = {}

    def __getattr__(self, name: str):
        """Dynamically load and return model for requested file."""
        if name.startswith('_'):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

        # Check if already loaded
        if name in self._loaded_models:
            return self._loaded_models[name]

        # Map file names to model classes
        model_map = {
            'tasktree': TaskTree,
            'bugs': ProjectBugList if self.scope_type == 'project' else GlobalBugList,
            'time': ProjectTimeTracker
        }

        if name not in model_map:
            raise AttributeError(f"Unknown file '{name}' for {self.scope_type} scope")

        model_class = model_map[name]
        file_path = self.data_dir / f"{name}.yml"

        # Load or create model
        model = model_class.from_yaml_file(str(file_path))
        if model is None:
            model = model_class()

        self._loaded_models[name] = model
        return model

    def save_all(self):
        """Save all loaded models back to their files."""
        for name, model in self._loaded_models.items():
            file_path = self.data_dir / f"{name}.yml"
            model.to_yaml_file(str(file_path))

class PrismContext:
    """Main context object providing access to project and user data."""

    def __init__(self):
        self.project = FileScope('project', DataCore.PROJECT_DATA_DIR, self)
        self.user = FileScope('user', DataCore.USER_DATA_DIR, self)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - save all changes."""
        self.save_all()

    def save_all(self):
        """Save all changes to both project and user files."""
        self.project.save_all()
        self.user.save_all()

class DataCore:
    """
    Central data validation and migration handler.

    Provides version checking, data validation, migration coordination,
    and serialization/parsing for both project-scoped and user-scoped data files.
    """

    # Current application schema version is now imported from version.py
    APP_SCHEMA_VERSION = APP_SCHEMA_VERSION

    # File paths
    PROJECT_DATA_DIR = Path(".prsm")
    USER_DATA_DIR = Path.home() / ".local" / "share" / "prismtm" / "data"

    # Required project files (flagship feature)
    REQUIRED_PROJECT_FILES = {
        "tasktree.yml": "project_tasks.schema.json"
    }

    # Optional project files (user-specific features)
    OPTIONAL_PROJECT_FILES = {
        "bugs.yml": "project_bugs.schema.json",
        "time.yml": "project_time.schema.json"
    }

    # All project files combined
    PROJECT_FILES = {**REQUIRED_PROJECT_FILES, **OPTIONAL_PROJECT_FILES}

    # Required user files
    USER_FILES = {
        "data.yml": "user_data.schema.json",
        "config.yml": "user_config.schema.json",
        "bugs.yml": "user_bugs.schema.json"
    }

    @classmethod
    def get_context(cls) -> PrismContext:
        """
        Get a context object for accessing project and user data.

        Usage:
            with DataCore.get_context() as context:
                context.project.tasktree.current_task_path = "phase1/milestone1/block1/task1"
                context.user.config.theme = "dark"
                # Changes are automatically saved on exit

        Returns:
            PrismContext instance that can be used as a context manager
        """
        return PrismContext()

    @classmethod
    def load_yaml_file(cls, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """
        Load and parse a YAML file.

        Args:
            file_path: Path to the YAML file

        Returns:
            Parsed data as dict, or None if file doesn't exist or parsing fails
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except (yaml.YAMLError, IOError) as e:
            print(f"Error loading YAML file {file_path}: {e}")
            return None

    @classmethod
    def save_yaml_file(cls, data: Dict[str, Any], file_path: Union[str, Path], create_dirs: bool = True) -> bool:
        """
        Serialize and save data to a YAML file using atomic updates.

        Args:
            data: Data to serialize
            file_path: Path to save the file
            create_dirs: Whether to create parent directories if they don't exist

        Returns:
            True if successful, False otherwise
        """
        file_path = Path(file_path)

        if create_dirs:
            file_path.parent.mkdir(parents=True, exist_ok=True)

        temp_file = None
        try:
            # Create temporary file in the same directory as target
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                dir=file_path.parent,
                prefix=f".{file_path.name}.",
                suffix='.tmp',
                delete=False
            ) as temp_file:
                # Write data to temporary file
                yaml.safe_dump(data, temp_file, default_flow_style=False, sort_keys=False, indent=2)
                temp_file.flush()
                os.fsync(temp_file.fileno())  # Ensure data is written to disk
                temp_path = temp_file.name

            # Atomically replace the original file
            os.replace(temp_path, file_path)
            return True

        except (yaml.YAMLError, IOError, OSError) as e:
            print(f"Error saving YAML file {file_path}: {e}")
            # Clean up temporary file if it exists
            if temp_file and hasattr(temp_file, 'name'):
                try:
                    os.unlink(temp_file.name)
                except OSError:
                    pass
            return False

    @classmethod
    def load_json_file(cls, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """
        Load and parse a JSON file.

        Args:
            file_path: Path to the JSON file

        Returns:
            Parsed data as dict, or None if file doesn't exist or parsing fails
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f) or {}
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading JSON file {file_path}: {e}")
            return None

    @classmethod
    def save_json_file(cls, data: Dict[str, Any], file_path: Union[str, Path], create_dirs: bool = True, indent: int = 2) -> bool:
        """
        Serialize and save data to a JSON file using atomic updates.

        Args:
            data: Data to save
            file_path: Path to save the file
            create_dirs: Whether to create parent directories if they don't exist
            indent: JSON indentation level

        Returns:
            True if successful, False otherwise
        """
        file_path = Path(file_path)

        if create_dirs:
            file_path.parent.mkdir(parents=True, exist_ok=True)

        temp_file = None
        try:
            # Create temporary file in the same directory as target
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                dir=file_path.parent,
                prefix=f".{file_path.name}.",
                suffix='.tmp',
                delete=False
            ) as temp_file:
                # Write data to temporary file
                json.dump(data, temp_file, indent=indent, ensure_ascii=False)
                temp_file.flush()
                os.fsync(temp_file.fileno())  # Ensure data is written to disk
                temp_path = temp_file.name

            # Atomically replace the original file
            os.replace(temp_path, file_path)
            return True

        except (json.JSONEncodeError, IOError, OSError) as e:
            print(f"Error saving JSON file {file_path}: {e}")
            # Clean up temporary file if it exists
            if temp_file and hasattr(temp_file, 'name'):
                try:
                    os.unlink(temp_file.name)
                except OSError:
                    pass
            return False

    @classmethod
    def load_project_file(cls, filename: str) -> Optional[Dict[str, Any]]:
        """
        Load a project-scoped data file.

        Args:
            filename: Name of the file (e.g., 'project_tasks.yaml')

        Returns:
            Parsed data or None if file doesn't exist
        """
        file_path = cls.PROJECT_DATA_DIR / filename
        if filename.endswith('.yaml') or filename.endswith('.yml'):
            return cls.load_yaml_file(file_path)
        elif filename.endswith('.json'):
            return cls.load_json_file(file_path)
        else:
            print(f"Unsupported file format: {filename}")
            return None

    @classmethod
    def save_project_file(cls, data: Dict[str, Any], filename: str) -> bool:
        """
        Save data to a project-scoped file.

        Args:
            data: Data to save
            filename: Name of the file (e.g., 'project_tasks.yaml')

        Returns:
            True if successful, False otherwise
        """
        file_path = cls.PROJECT_DATA_DIR / filename
        if filename.endswith('.yaml') or filename.endswith('.yml'):
            return cls.save_yaml_file(data, file_path)
        elif filename.endswith('.json'):
            return cls.save_json_file(data, file_path)
        else:
            print(f"Unsupported file format: {filename}")
            return False

    @classmethod
    def load_user_file(cls, filename: str) -> Optional[Dict[str, Any]]:
        """
        Load a user-scoped data file.

        Args:
            filename: Name of the file (e.g., 'user_config.yaml')

        Returns:
            Parsed data or None if file doesn't exist
        """
        file_path = cls.USER_DATA_DIR / filename
        if filename.endswith('.yaml') or filename.endswith('.yml'):
            return cls.load_yaml_file(file_path)
        elif filename.endswith('.json'):
            return cls.load_json_file(file_path)
        else:
            print(f"Unsupported file format: {filename}")
            return None

    @classmethod
    def save_user_file(cls, data: Dict[str, Any], filename: str) -> bool:
        """
        Save data to a user-scoped file.

        Args:
            data: Data to save
            filename: Name of the file (e.g., 'user_config.yaml')

        Returns:
            True if successful, False otherwise
        """
        file_path = cls.USER_DATA_DIR / filename
        if filename.endswith('.yaml') or filename.endswith('.yml'):
            return cls.save_yaml_file(data, file_path)
        elif filename.endswith('.json'):
            return cls.save_json_file(data, file_path)
        else:
            print(f"Unsupported file format: {filename}")
            return False

    @classmethod
    def get_schema_dir(cls) -> Path:
        """Get schema directory, handling both development and installed package."""
        try:
            schema_files = files('prismtm') / 'schemas'
            return Path(str(schema_files))
        except (ImportError, FileNotFoundError):
            # Fallback to development path
            return Path(__file__).parent.parent.parent / "schemas"

    @classmethod
    def get_schema_versions(cls) -> List[str]:
        """Get all available schema versions sorted from newest to oldest."""
        schema_dir = cls.get_schema_dir()
        if not schema_dir.exists():
            return []

        versions = []
        for version_dir in schema_dir.iterdir():
            if version_dir.is_dir() and version_dir.name.startswith('v'):
                versions.append(version_dir.name[1:])  # Remove 'v' prefix

        # Sort from newest to oldest for backwards validation
        return sorted(versions, key=version.parse, reverse=True)

    @classmethod
    def get_latest_schema_version(cls) -> str:
        """Get the latest available schema version."""
        versions = cls.get_schema_versions()
        return versions[0] if versions else "0.0.0"  # First item since sorted newest first

    @classmethod
    def check_required_files_exist(cls, data_dir: Path, file_mapping: Dict[str, str]) -> Tuple[List[str], List[str]]:
        """
        Check which required files exist and which are missing.

        Args:
            data_dir: Directory to check for files
            file_mapping: Dict mapping file names to schema names

        Returns:
            Tuple of (existing_files, missing_files)
        """
        existing_files = []
        missing_files = []

        if not data_dir.exists():
            return existing_files, list(file_mapping.keys())

        for file_name in file_mapping.keys():
            file_path = data_dir / file_name
            if file_path.exists():
                existing_files.append(file_name)
            else:
                missing_files.append(file_name)

        return existing_files, missing_files

    @classmethod
    def validate_files_backwards(cls, data_dir: Path, file_mapping: Dict[str, str]) -> Tuple[str, List[str]]:
        """
        Validate files by working backwards from newest schema version until successful.

        Args:
            data_dir: Directory containing the files to validate
            file_mapping: Dict mapping file names to schema names

        Returns:
            Tuple of (detected_version, validation_errors)
        """
        existing_files, missing_files = cls.check_required_files_exist(data_dir, file_mapping)

        if not existing_files:
            return "0.0.0", []  # No files means no version, but that's valid

        # Get schema versions from newest to oldest
        schema_versions = cls.get_schema_versions()
        if not schema_versions:
            return "0.0.0", ["No schema versions available"]

        validation_errors = []

        # Try each version from newest to oldest
        for schema_version in schema_versions:
            version_errors = []
            all_files_valid = True

            # Try to validate all existing files against this schema version
            for file_name in existing_files:
                file_path = str(data_dir / file_name)

                # Use the validation logic from validate.py
                try:
                    if not validate_file_schema(file_path, f"v{schema_version}"):
                        all_files_valid = False
                        version_errors.append(f"{file_name} failed validation against v{schema_version}")
                except Exception as e:
                    all_files_valid = False
                    version_errors.append(f"{file_name} validation error: {e}")

            # If all files validated successfully against this version, we found it
            if all_files_valid:
                return schema_version, []

            validation_errors.extend(version_errors)

        # If no version worked, return the oldest version with all errors
        oldest_version = schema_versions[-1] if schema_versions else "0.0.0"
        return oldest_version, validation_errors

    @classmethod
    def validate_project_data(cls) -> Tuple[bool, str, List[str]]:
        """
        Validate project data files using backwards schema validation.

        Returns:
            Tuple of (is_valid, detected_version, errors)
        """
        detected_version, errors = cls.validate_files_backwards(
            cls.PROJECT_DATA_DIR,
            cls.REQUIRED_PROJECT_FILES
        )

        # Check for missing files
        existing_files, missing_files = cls.check_required_files_exist(
            cls.PROJECT_DATA_DIR,
            cls.PROJECT_FILES
        )

        # Add missing file warnings (but don't fail validation)
        if missing_files:
            for missing_file in missing_files:
                errors.append(f"Optional file missing: {missing_file}")

        is_valid = len([e for e in errors if not e.startswith("Optional")]) == 0
        return is_valid, detected_version, errors

    @classmethod
    def validate_user_data(cls) -> Tuple[bool, str, List[str]]:
        """
        Validate user data files using backwards schema validation.

        Returns:
            Tuple of (is_valid, detected_version, errors)
        """
        detected_version, errors = cls.validate_files_backwards(
            cls.USER_DATA_DIR,
            cls.USER_FILES
        )

        # Check for missing files
        existing_files, missing_files = cls.check_required_files_exist(
            cls.USER_DATA_DIR,
            cls.USER_FILES
        )

        # Add missing file warnings (but don't fail validation)
        if missing_files:
            for missing_file in missing_files:
                errors.append(f"Optional file missing: {missing_file}")

        is_valid = len([e for e in errors if not e.startswith("Optional")]) == 0
        return is_valid, detected_version, errors

    @classmethod
    def validate(cls) -> Tuple[str, str, str]:
        """
        Validate all data and return version information.

        Uses backwards validation approach: starts from the most recent schema version
        and works backwards until validation succeeds, determining the actual data version.

        Returns:
            Tuple of (project_version, user_version, app_schema_version)
        """
        # Validate project data using backwards validation
        project_valid, project_version, project_errors = cls.validate_project_data()
        if not project_valid:
            print("Project data validation errors:")
            for error in project_errors:
                if not error.startswith("Optional"):
                    print(f"  - {error}")

        # Validate user data using backwards validation
        user_valid, user_version, user_errors = cls.validate_user_data()
        if not user_valid:
            print("User data validation errors:")
            for error in user_errors:
                if not error.startswith("Optional"):
                    print(f"  - {error}")

        return project_version, user_version, APP_SCHEMA_VERSION

    @classmethod
    def check_migration_needed(cls) -> Dict[str, bool]:
        """
        Check if migrations are needed for project or user data.

        Returns:
            Dict with 'project' and 'user' keys indicating if migration is needed
        """
        project_version, user_version, app_version = cls.validate()

        return {
            'project': version.parse(project_version) < version.parse(app_version),
            'user': version.parse(user_version) < version.parse(app_version)
        }

    @classmethod
    def migrate_project_data(cls, target_version: Optional[str] = None) -> bool:
        """
        Migrate project data to target version (or latest).

        Args:
            target_version: Version to migrate to (defaults to APP_SCHEMA_VERSION)

        Returns:
            True if migration successful, False otherwise
        """
        if target_version is None:
            target_version = APP_SCHEMA_VERSION

        try:
            engine = MigrationEngine()
            return engine.migrate_project_files(target_version)
        except Exception as e:
            print(f"Project migration failed: {e}")
            return False

    @classmethod
    def migrate_user_data(cls, target_version: Optional[str] = None) -> bool:
        """
        Migrate user data to target version (or latest).

        Args:
            target_version: Version to migrate to (defaults to APP_SCHEMA_VERSION)

        Returns:
            True if migration successful, False otherwise
        """
        if target_version is None:
            target_version = APP_SCHEMA_VERSION

        try:
            engine = MigrationEngine()
            return engine.migrate_user_files(target_version)
        except Exception as e:
            print(f"User migration failed: {e}")
            return False
