import os
import sys
import yaml
import json
import shutil
import argparse
import logging
import importlib.util
from typing import List, Dict, Type, Optional
try:
    from importlib.resources import files
except ImportError:
    # Python &lt; 3.9 fallback
    from importlib_resources import files

# Import the abstract base class to check against
from .migration import Migration, MigrationData

# Configure logging for better feedback
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constants and Configuration ---
def get_schema_dir():
    """Get schema directory, handling both development and installed package."""
    try:
        # Try to use bundled schemas from installed package
        schema_files = files('prism_task_manager') / 'schemas'
        return str(schema_files)
    except (ImportError, FileNotFoundError):
        # Fallback to development path
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schemas')

SCHEMA_DIR = get_schema_dir()
MIGRATIONS_DIR = os.path.join(SCHEMA_DIR, 'migrations')

GLOBAL_DATA_DIR = os.path.join(os.path.expanduser('~'), '.local', 'share', 'prismtm')
LOCAL_PROJECT_DIR = '.prsm'

# --- Migration Engine Class ---
class MigrationEngine:
    """
    A robust migration engine for Prism's YAML data using an abstract class pattern.

    This class discovers available schema versions and dynamically imports
    migration classes to migrate global and local project files to the latest version.
    """
    def __init__(self):
        """Initializes the engine by discovering all schema versions and migration classes."""
        self.migrations: Dict[str, Migration] = {}
        self.available_versions = self._discover_versions()
        self.latest_version = self.available_versions[-1] if self.available_versions else 'v0.0.0'
        logging.info(f"Discovered schema versions: {self.available_versions}")
        logging.info(f"Latest schema version: {self.latest_version}")
        self._load_migration_classes()

    def _discover_versions(self) -> List[str]:
        """
        Scans the SCHEMA_DIR for version directories (e.g., 'v0.0.0').
        The versions are returned as a sorted list of strings.
        """
        versions = []
        if os.path.exists(SCHEMA_DIR):
            for name in os.listdir(SCHEMA_DIR):
                full_path = os.path.join(SCHEMA_DIR, name)
                if os.path.isdir(full_path) and name.startswith('v'):
                    versions.append(name)

        # Sort versions to ensure migrations are applied in the correct order.
        return sorted(versions, key=lambda v: [int(s) for s in v[1:].split('.')])

    def _load_migration_classes(self):
        """
        Dynamically discovers, imports, and instantiates concrete Migration classes
        from Python scripts in the `schemas/migrations` directory.
        """
        if not os.path.exists(MIGRATIONS_DIR):
            logging.warning(f"Migrations directory '{MIGRATIONS_DIR}' not found.")
            return

        for filename in os.listdir(MIGRATIONS_DIR):
            if filename.endswith('.py') and not filename.startswith('__') and filename != 'migration.py':
                module_name = filename[:-3]
                file_path = os.path.join(MIGRATIONS_DIR, filename)

                # Dynamic import
                try:
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module # Add the module to sys.modules
                    spec.loader.exec_module(module)

                    # Find a class that inherits from Migration
                    migration_class = self._find_migration_class_in_module(module)

                    if migration_class:
                        migration_instance = migration_class()
                        migration_key = f"{module_name}"
                        self.migrations[migration_key] = migration_instance
                        logging.info(f"Successfully loaded migration class '{migration_class.__name__}' from '{filename}'.")
                    else:
                        logging.warning(f"File '{filename}' does not contain a concrete Migration class.")
                except Exception as e:
                    logging.error(f"Failed to import migration script '{filename}': {e}")

    def _find_migration_class_in_module(self, module) -> Optional[Type[Migration]]:
        """
        Helper method to find a concrete subclass of Migration in a loaded module.
        """
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and # Is a class
                issubclass(attr, Migration) and # Inherits from Migration
                attr is not Migration): # Is not the abstract class itself

                return attr
        return None

    def get_migration_path(self, current_version: str) -> List[str]:
        """
        Determines the sequence of migrations needed to get from
        current_version to the latest version.

        Args:
            current_version: The version string of the user's current data.

        Returns:
            A list of migration step keys (e.g., ['v0.0.0_to_v0.0.1']).
        """
        try:
            current_index = self.available_versions.index(current_version)
        except ValueError:
            logging.error(f"Current version '{current_version}' not found in available schemas.")
            return []

        migration_path = []
        for i in range(current_index, len(self.available_versions) - 1):
            from_version = self.available_versions[i]
            to_version = self.available_versions[i + 1]
            migration_key = f"{from_version}_to_{to_version}"

            # Check if a specific migration class instance exists for this step.
            if migration_key in self.migrations:
                migration_path.append(migration_key)
            else:
                logging.warning(f"No specific migration class found for '{migration_key}'. Skipping.")

        return migration_path

    def migrate_file(self, file_path: str, current_version: str):
        """
        Performs the migration for a single YAML file.

        Args:
            file_path: The full path to the YAML file to migrate.
            current_version: The version of the file's data.
        """
        if not os.path.exists(file_path):
            logging.error(f"File not found: {file_path}")
            return

        migration_path = self.get_migration_path(current_version)
        if not migration_path:
            logging.info(f"No migration needed for {file_path} from version {current_version}.")
            return

        backup_path = f"{file_path}.bak"
        shutil.copy2(file_path, backup_path)
        logging.info(f"Created backup at {backup_path}")

        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)

            logging.info(f"Starting migration for {file_path}...")
            for migration_key in migration_path:
                from_ver, to_ver = migration_key.split('_to_')
                logging.info(f"Migrating from {from_ver} to {to_ver}...")

                migration_instance = self.migrations[migration_key]
                data = migration_instance.upgrade(data)

            with open(file_path, 'w') as f:
                yaml.dump(data, f, sort_keys=False, default_flow_style=False)

            logging.info(f"Successfully migrated {file_path} to version {self.latest_version}.")

        except Exception as e:
            logging.error(f"Migration failed for {file_path}. Restoring from backup. Error: {e}")
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, file_path)
        finally:
            if os.path.exists(backup_path):
                os.remove(backup_path)

    def migrate_project_files(self, target_version: str) -> bool:
        """Migrates all local project files in the .prsm directory."""
        logging.info("Starting local project migration...")
        if not os.path.exists(LOCAL_PROJECT_DIR):
            logging.warning(f"Local project directory '{LOCAL_PROJECT_DIR}' not found. Exiting.")
            return False

        # Example: Assume version is read from a metadata file.
        current_version = 'v0.0.0'

        files_to_migrate = ['project.yml', 'bugs.yml', 'tasks.yml']
        success = True
        for file_name in files_to_migrate:
            file_path = os.path.join(LOCAL_PROJECT_DIR, file_name)
            try:
                self.migrate_file(file_path, current_version)
            except Exception as e:
                logging.error(f"Failed to migrate {file_path}: {e}")
                success = False

        return success

    def migrate_user_files(self, target_version: str) -> bool:
        """Migrates all global files in the user's shared directory."""
        logging.info("Starting global file migration...")
        if not os.path.exists(GLOBAL_DATA_DIR):
            logging.warning(f"Global data directory '{GLOBAL_DATA_DIR}' not found. Exiting.")
            return False

        # Example: Assume version is read from a metadata file.
        current_version = 'v0.0.0'

        files_to_migrate = ['global_bugs.yml', 'global_projects.yml']
        success = True
        for file_name in files_to_migrate:
            file_path = os.path.join(GLOBAL_DATA_DIR, file_name)
            try:
                self.migrate_file(file_path, current_version)
            except Exception as e:
                logging.error(f"Failed to migrate {file_path}: {e}")
                success = False

        return success

    def run_local_migration(self):
        """Migrates all local project files in the .prsm directory."""
        return self.migrate_project_files(self.latest_version)

    def run_global_migration(self):
        """Migrates all global files in the user's shared directory."""
        return self.migrate_user_files(self.latest_version)

def main():
    """Main function to handle command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Prism YAML Migration Engine",
        formatter_class=argparse.RawTextHelpFormatter
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--local',
        action='store_true',
        help="Migrate local project files in the '.prsm' directory."
    )
    group.add_argument(
        '--global',
        action='store_true',
        dest='global_flag', # Use a different dest to avoid conflict with the built-in 'global' keyword
        help="Migrate global files in the user's share directory."
    )

    args = parser.parse_args()

    engine = MigrationEngine()

    if args.local:
        engine.run_local_migration()
    elif args.global_flag:
        engine.run_global_migration()

if __name__ == "__main__":
    main()
