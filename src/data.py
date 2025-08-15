"""
DataCore - Central data validation and migration handler for Prism Task Manager.

This module provides the main interface for validating project and user data files,
checking schema versions, and coordinating migrations.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List
from packaging import version
try:
    from importlib.resources import files
except ImportError:
    # Python < 3.9 fallback
    from importlib_resources import files

from .migrate import MigrationEngine
from .validate import find_schema_version, validate_file_schema
from .version import APP_SCHEMA_VERSION


class DataCore:
    """
    Central data validation and migration handler.

    Provides version checking, data validation, and migration coordination
    for both project-scoped and user-scoped data files.
    """

    # Current application schema version is now imported from version.py
    APP_SCHEMA_VERSION = APP_SCHEMA_VERSION

    # File paths
    PROJECT_DATA_DIR = Path(".prsm")
    USER_DATA_DIR = Path.home() / ".local" / "share" / "prismtm" / "data"

    # Expected project files
    PROJECT_FILES = {
        "project_tree.yaml": "project_tree.schema.json",
        "project_bugs.yaml": "project_bugs.schema.json",
        "project_tasks.yaml": "project_tasks.schema.json"
    }

    # Expected user files
    USER_FILES = {
        "user_data.yaml": "user_data.schema.json",
        "user_config.yaml": "user_config.schema.json",
        "user_bugs.yaml": "user_bugs.schema.json"
    }

    @classmethod
    def get_schema_dir(cls) -> Path:
        """Get schema directory, handling both development and installed package."""
        try:
            # Try to use bundled schemas from installed package
            schema_files = files('prism_task_manager') / 'schemas'
            return Path(str(schema_files))
        except (ImportError, FileNotFoundError):
            # Fallback to development path
            return Path(__file__).parent / "schemas"

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
            cls.PROJECT_FILES
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
