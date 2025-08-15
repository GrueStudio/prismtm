import json
import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID


# ============================================================================
# SCHEMA LOADER
# ============================================================================

class SchemaLoader:
    """Loads and manages JSON schema files."""
    
    def __init__(self, schema_dir: str = None):
        """Initialize with schema directory path."""
        if schema_dir is None:
            # Default to schemas/ directory relative to this file
            schema_dir = Path(__file__).parent / "schemas"
        
        self.schema_dir = Path(schema_dir)
        self._schemas_cache = {}
    
    def load_schema(self, schema_name: str) -> Dict[str, Any]:
        """Load a schema file by name."""
        if schema_name in self._schemas_cache:
            return self._schemas_cache[schema_name]
        
        # Map schema names to filenames
        schema_files = {
            "project": "project.schema.json",
            "bugs": "bugs.schema.json", 
            "orphans": "orphans.schema.json",
            "user_config": "user-config.schema.json",
            "user_data": "user-data.schema.json"
        }
        
        filename = schema_files.get(schema_name)
        if not filename:
            raise ValueError(f"Unknown schema: {schema_name}")
        
        schema_path = self.schema_dir / filename
        
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            
            # Cache the schema
            self._schemas_cache[schema_name] = schema
            return schema
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in schema file {filename}: {e}")
    
    def get_all_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Load all schemas and return as a dictionary."""
        schema_names = ["project", "bugs", "orphans", "user_config", "user_data"]
        return {name: self.load_schema(name) for name in schema_names}
    
    def validate_data(self, data: Dict[str, Any], schema_name: str) -> bool:
        """Validate data against a specific schema."""
        from jsonschema import validate, ValidationError
        
        schema = self.load_schema(schema_name)
        
        try:
            validate(instance=data, schema=schema)
            return True
        except ValidationError as e:
            print(f"Validation error for {schema_name}: {e.message}")
            return False


# ============================================================================
# UPDATED FILE MANAGER WITH SCHEMA LOADING
# ============================================================================

class PrismFileManager:
    """Handles reading and writing YAML files with schema validation."""
    
    def __init__(self, project_root: str = None, user_data_dir: str = None, schema_dir: str = None):
        self.project_root = Path(project_root) if project_root else Path(".")
        self.user_data_dir = Path(user_data_dir) if user_data_dir else Path("~/.local/share/prismtm/data")
        
        # Expand user directory
        self.user_data_dir = self.user_data_dir.expanduser()
        
        # Initialize schema loader
        self.schema_loader = SchemaLoader(schema_dir)
    
    def get_project_file_path(self, filename: str) -> Path:
        """Get path to project file."""
        return self.project_root / ".prsm" / filename
    
    def get_user_file_path(self, filename: str) -> Path:
        """Get path to user file."""
        return self.user_data_dir / filename
    
    def ensure_directories(self):
        """Ensure all necessary directories exist."""
        # Create project .prsm directory
        project_dir = self.project_root / ".prsm"
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Create user data directory
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
    
    def write_yaml_file(self, filepath: Path, data: Dict[str, Any], schema_name: str = None):
        """Write data to YAML file with optional schema validation."""
        # Validate against schema if provided
        if schema_name:
            if not self.schema_loader.validate_data(data, schema_name):
                raise ValueError(f"Data validation failed for schema: {schema_name}")
        
        # Create backup if file exists
        if filepath.exists():
            backup_path = filepath.with_suffix(filepath.suffix + ".backup")
            import shutil
            shutil.copy2(filepath, backup_path)
        
        # Write atomically using temp file
        temp_path = filepath.with_suffix(filepath.suffix + ".tmp")
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            # Atomic move
            temp_path.replace(filepath)
            
        except Exception as e:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise e
    
    def read_yaml_file(self, filepath: Path, schema_name: str = None) -> Dict[str, Any]:
        """Read and validate YAML file."""
        if not filepath.exists():
            return {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            # Validate against schema if provided
            if schema_name:
                if not self.schema_loader.validate_data(data, schema_name):
                    raise ValueError(f"File validation failed for schema: {schema_name}")
            
            return data
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}")
    
    # Project scope file operations
    def save_project_data(self, project_data, validate: bool = True):
        """Save ProjectData to project.yml."""
        from prism_yaml_schemas import PrismYAMLEncoder  # Import the encoder
        
        data = PrismYAMLEncoder.serialize_project_data(project_data)
        filepath = self.get_project_file_path("project.yml")
        schema_name = "project" if validate else None
        self.write_yaml_file(filepath, data, schema_name)
    
    def load_project_data(self, validate: bool = True):
        """Load ProjectData from project.yml."""
        filepath = self.get_project_file_path("project.yml")
        schema_name = "project" if validate else None
        return self.read_yaml_file(filepath, schema_name)
    
    def save_project_bugs(self, bugs, validate: bool = True):
        """Save ProjectBugs to bugs.yml."""
        from prism_yaml_schemas import PrismYAMLEncoder
        
        data = PrismYAMLEncoder.serialize_project_bugs(bugs)
        filepath = self.get_project_file_path("bugs.yml")
        schema_name = "bugs" if validate else None
        self.write_yaml_file(filepath, data, schema_name)
    
    def load_project_bugs(self, validate: bool = True):
        """Load ProjectBugs from bugs.yml."""
        filepath = self.get_project_file_path("bugs.yml")
        schema_name = "bugs" if validate else None
        return self.read_yaml_file(filepath, schema_name)
    
    def save_orphan_tasks(self, orphans, validate: bool = True):
        """Save OrphanTasks to orphans.yml."""
        from prism_yaml_schemas import PrismYAMLEncoder
        
        data = PrismYAMLEncoder.serialize_orphan_tasks(orphans)
        filepath = self.get_project_file_path("orphans.yml")
        schema_name = "orphans" if validate else None
        self.write_yaml_file(filepath, data, schema_name)
    
    def load_orphan_tasks(self, validate: bool = True):
        """Load OrphanTasks from orphans.yml."""
        filepath = self.get_project_file_path("orphans.yml")
        schema_name = "orphans" if validate else None
        return self.read_yaml_file(filepath, schema_name)
    
    # User scope file operations
    def save_user_config(self, config, validate: bool = True):
        """Save UserConfig to config.yml."""
        from prism_yaml_schemas import PrismYAMLEncoder
        
        data = PrismYAMLEncoder.serialize_user_config(config)
        filepath = self.get_user_file_path("config.yml")
        schema_name = "user_config" if validate else None
        self.write_yaml_file(filepath, data, schema_name)
    
    def load_user_config(self, validate: bool = True):
        """Load UserConfig from config.yml."""
        filepath = self.get_user_file_path("config.yml")
        schema_name = "user_config" if validate else None
        return self.read_yaml_file(filepath, schema_name)
    
    def save_user_data(self, user_data, validate: bool = True):
        """Save UserData to data.yml."""
        from prism_yaml_schemas import PrismYAMLEncoder
        
        data = PrismYAMLEncoder.serialize_user_data(user_data)
        filepath = self.get_user_file_path("data.yml")
        schema_name = "user_data" if validate else None
        self.write_yaml_file(filepath, data, schema_name)
    
    def load_user_data(self, validate: bool = True):
        """Load UserData from data.yml."""
        filepath = self.get_user_file_path("data.yml")
        schema_name = "user_data" if validate else None
        return self.read_yaml_file(filepath, schema_name)


# ============================================================================
# MIGRATION UTILITIES
# ============================================================================

class SchemaMigration:
    """Handles schema migrations for version updates."""
    
    def __init__(self, file_manager: PrismFileManager):
        self.file_manager = file_manager
        self.schema_loader = file_manager.schema_loader
    
    def get_file_schema_version(self, filepath: Path) -> Optional[str]:
        """Extract schema version from a YAML file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            # Look for version in various places
            if 'meta' in data and 'version' in data['meta']:
                return data['meta']['version']
            elif 'version' in data:
                return data['version']
            elif '$schema_version' in data:
                return data['$schema_version']
            
            return None
            
        except Exception:
            return None
    
    def needs_migration(self, filepath: Path, target_version: str) -> bool:
        """Check if a file needs migration to target version."""
        current_version = self.get_file_schema_version(filepath)
        if not current_version:
            return True  # Assume needs migration if no version found
        
        # Simple version comparison (you might want semver here)
        return current_version != target_version
    
    def migrate_project_file(self, filepath: Path, from_version: str, to_version: str):
        """Migrate a project file from one schema version to another."""
        # This is where you'd implement specific migration logic
        # For now, just a placeholder
        print(f"Migrating {filepath} from {from_version} to {to_version}")
        
        # Example migration logic:
        if from_version == "0.1.0" and to_version == "0.2.0":
            # Load data without validation
            data = self.file_manager.read_yaml_file(filepath, schema_name=None)
            
            # Perform migration transformations
            # e.g., add new required fields, rename fields, etc.
            if 'meta' in data:
                data['meta']['schema_version'] = to_version
            
            # Save with new schema validation
            self.file_manager.write_yaml_file(filepath, data, schema_name="project")


# ============================================================================
# TESTING UTILITIES
# ============================================================================

class SchemaTestUtils:
    """Utilities for testing schema validation."""
    
    def __init__(self, schema_loader: SchemaLoader):
        self.schema_loader = schema_loader
    
    def generate_valid_sample(self, schema_name: str) -> Dict[str, Any]:
        """Generate a valid sample data structure for testing."""
        # This would generate minimal valid data structures for each schema
        samples = {
            "project": {
                "meta": {
                    "name": "Test Project",
                    "version": "0.1.0",
                    "created_at": "2025-01-01T00:00:00",
                    "updated_at": "2025-01-01T00:00:00"
                },
                "navigation": {
                    "current_phase_id": None,
                    "current_milestone_id": None,
                    "current_block_id": None,
                    "current_task_id": None,
                    "current_subtask_id": None
                },
                "timer": None,
                "phases": {}
            },
            "bugs": {
                "bugs": {}
            },
            "orphans": {
                "orphans": {}
            },
            "user_config": {
                "display": {
                    "show_colors": true,
                    "show_progress_bars": true,
                    "default_time_format": "24h",
                    "timezone": "local"
                },
                "behavior": {
                    "auto_start_timer": true,
                    "confirm_destructive_actions": true,
                    "auto_backup_interval": 24
                },
                "bug_import": {
                    "import_duplicates": false,
                    "auto_categorize_bugs": true,
                    "merge_similar_tags": true
                },
                "reporting": {
                    "default_report_period": "week",
                    "include_orphans_in_reports": false
                }
            },
            "user_data": {
                "global_bugs": {},
                "known_projects": {},
                "productivity_stats": {}
            }
        }
        
        return samples.get(schema_name, {})
    
    def generate_invalid_samples(self, schema_name: str) -> List[Dict[str, Any]]:
        """Generate invalid sample data for testing validation."""
        base_valid = self.generate_valid_sample(schema_name)
        invalid_samples = []
        
        if schema_name == "project":
            # Missing required field
            invalid_1 = base_valid.copy()
            del invalid_1["meta"]["name"]
            invalid_samples.append(invalid_1)
            
            # Invalid version format
            invalid_2 = base_valid.copy()
            invalid_2["meta"]["version"] = "invalid-version"
            invalid_samples.append(invalid_2)
            
            # Invalid UUID format
            invalid_3 = base_valid.copy()
            invalid_3["navigation"]["current_phase_id"] = "not-a-uuid"
            invalid_samples.append(invalid_3)
        
        elif schema_name == "bugs":
            # Invalid severity
            invalid_1 = base_valid.copy()
            invalid_1["bugs"]["test-id"] = {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Test Bug",
                "severity": "invalid-severity",  # Invalid
                "status": "open",
                "tags": [],
                "reporter": "test",
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00"
            }
            invalid_samples.append(invalid_1)
        
        return invalid_samples
    
    def test_all_schemas(self) -> Dict[str, bool]:
        """Test all schemas with valid and invalid data."""
        results = {}
        
        for schema_name in ["project", "bugs", "orphans", "user_config", "user_data"]:
            try:
                # Test valid sample
                valid_sample = self.generate_valid_sample(schema_name)
                valid_result = self.schema_loader.validate_data(valid_sample, schema_name)
                
                # Test invalid samples
                invalid_samples = self.generate_invalid_samples(schema_name)
                invalid_results = []
                for invalid_sample in invalid_samples:
                    # These should return False (validation should fail)
                    invalid_result = self.schema_loader.validate_data(invalid_sample, schema_name)
                    invalid_results.append(not invalid_result)  # We want False, so invert
                
                # Schema passes if valid data validates and invalid data fails
                results[schema_name] = valid_result and all(invalid_results)
                
            except Exception as e:
                print(f"Error testing schema {schema_name}: {e}")
                results[schema_name] = False
        
        return results


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def example_usage():
    """Demonstrate how to use the schema system."""
    
    # Initialize file manager with schema validation
    fm = PrismFileManager(
        project_root="/path/to/project",
        user_data_dir="~/.local/share/prismtm/data",
        schema_dir="./schemas"  # Directory containing .json schema files
    )
    
    # Ensure directories exist
    fm.ensure_directories()
    
    # Load schemas directly
    schema_loader = fm.schema_loader
    project_schema = schema_loader.load_schema("project")
    print(f"Loaded project schema with {len(project_schema)} top-level properties")
    
    # Validate some data
    test_data = {
        "meta": {
            "name": "Test Project",
            "version": "0.1.0",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00"
        },
        "navigation": {},
        "phases": {}
    }
    
    is_valid = schema_loader.validate_data(test_data, "project")
    print(f"Test data validation: {'✓ PASS' if is_valid else '✗ FAIL'}")
    
    # Test migration checking
    migration = SchemaMigration(fm)
    project_file = fm.get_project_file_path("project.yml")
    needs_migration = migration.needs_migration(project_file, "0.2.0")
    print(f"Needs migration: {needs_migration}")
    
    # Run schema tests
    test_utils = SchemaTestUtils(schema_loader)
    test_results = test_utils.test_all_schemas()
    print("Schema test results:")
    for schema, passed in test_results.items():
        print(f"  {schema}: {'✓ PASS' if passed else '✗ FAIL'}")


# ============================================================================
# DIRECTORY STRUCTURE EXAMPLE
# ============================================================================

def create_schema_directory_structure():
    """Show the expected directory structure for schemas."""
    structure = """
    Your project structure should look like:
    
    project-root/
    ├── src/
    │   ├── prism_models.py           # Data models
    │   ├── prism_yaml_schemas.py     # Serialization utilities  
    │   └── schema_loader.py          # This file
    ├── schemas/
    │   ├── project.schema.json       # Project hierarchy schema
    │   ├── bugs.schema.json          # Bug tracking schema
    │   ├── orphans.schema.json       # Orphan tasks schema
    │   ├── user-config.schema.json   # User configuration schema
    │   └── user-data.schema.json     # User data schema
    ├── tests/
    │   ├── test_schemas.py           # Schema validation tests
    │   └── test_migrations.py        # Migration tests
    └── .prsm/
        ├── project.yml               # Project data (validated)
        ├── bugs.yml                  # Project bugs (validated)
        └── orphans.yml               # Orphan tasks (validated)
    
    ~/.local/share/prismtm/data/
    ├── config.yml                    # User config (validated)
    └── data.yml                      # Global data (validated)
    """
    
    return structure


if __name__ == "__main__":
    print("Prism Schema System")
    print("=" * 50)
    print(create_schema_directory_structure())
    print("\nRunning example usage...")
    example_usage()