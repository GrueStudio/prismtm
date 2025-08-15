#!/usr/bin/env python3
"""
Migration Script Generator for Prism Task Manager

This script analyzes schema differences between versions and generates
migration classes that work with the existing migration engine.
"""

import os
import json
import argparse
import logging
from typing import Dict, Any, List, Set, Tuple, Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SchemaDiff:
    """Represents the differences between two schema versions."""

    def __init__(self, from_version: str, to_version: str):
        self.from_version = from_version
        self.to_version = to_version
        self.added_fields: Dict[str, Dict[str, Any]] = {}
        self.removed_fields: Dict[str, Dict[str, Any]] = {}
        self.modified_fields: Dict[str, Dict[str, Any]] = {}
        self.renamed_fields: Dict[str, Tuple[str, str]] = {}  # old_name -> new_name
        self.type_changes: Dict[str, Tuple[str, str]] = {}  # field -> (old_type, new_type)
        self.enum_changes: Dict[str, Tuple[List[str], List[str]]] = {}  # field -> (old_values, new_values)
        self.structural_changes: List[str] = []

class MigrationGenerator:
    """Generates migration scripts by comparing schema versions."""

    def __init__(self, schemas_dir: str = "schemas"):
        self.schemas_dir = Path(schemas_dir)
        self.migrations_dir = self.schemas_dir / "migrations"
        self.migrations_dir.mkdir(exist_ok=True)

    def load_schema(self, version: str, schema_name: str) -> Optional[Dict[str, Any]]:
        """Load a specific schema file for a given version."""
        schema_path = self.schemas_dir / version / f"{schema_name}.schema.json"
        if not schema_path.exists():
            logging.warning(f"Schema not found: {schema_path}")
            return None

        try:
            with open(schema_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load schema {schema_path}: {e}")
            return None

    def get_available_versions(self) -> List[str]:
        """Get all available schema versions, sorted."""
        versions = []
        for path in self.schemas_dir.iterdir():
            if path.is_dir() and path.name.startswith('v'):
                versions.append(path.name)
        return sorted(versions, key=lambda v: [int(s) for s in v[1:].split('.')])

    def get_schema_names(self, version: str) -> Set[str]:
        """Get all schema names for a given version."""
        version_dir = self.schemas_dir / version
        if not version_dir.exists():
            return set()

        schema_names = set()
        for schema_file in version_dir.glob("*.schema.json"):
            schema_names.add(schema_file.stem.replace('.schema', ''))
        return schema_names

    def extract_properties(self, schema: Dict[str, Any], path: str = "") -> Dict[str, Dict[str, Any]]:
        """Extract all properties from a schema with their full paths."""
        properties = {}

        if "properties" in schema:
            for prop_name, prop_def in schema["properties"].items():
                full_path = f"{path}.{prop_name}" if path else prop_name
                properties[full_path] = prop_def

                # Recursively extract nested properties
                if "properties" in prop_def:
                    nested_props = self.extract_properties(prop_def, full_path)
                    properties.update(nested_props)

                # Handle array items
                if prop_def.get("type") == "array" and "items" in prop_def:
                    items_def = prop_def["items"]
                    if "properties" in items_def:
                        nested_props = self.extract_properties(items_def, f"{full_path}[]")
                        properties.update(nested_props)

        return properties

    def compare_schemas(self, from_schema: Dict[str, Any], to_schema: Dict[str, Any]) -> SchemaDiff:
        """Compare two schemas and return the differences."""
        from_props = self.extract_properties(from_schema)
        to_props = self.extract_properties(to_schema)

        diff = SchemaDiff("", "")  # Will be set by caller

        # Find added fields
        for prop_path in to_props:
            if prop_path not in from_props:
                diff.added_fields[prop_path] = to_props[prop_path]

        # Find removed fields
        for prop_path in from_props:
            if prop_path not in to_props:
                diff.removed_fields[prop_path] = from_props[prop_path]

        # Find modified fields
        for prop_path in from_props:
            if prop_path in to_props:
                from_def = from_props[prop_path]
                to_def = to_props[prop_path]

                # Check type changes
                from_type = from_def.get("type", "unknown")
                to_type = to_def.get("type", "unknown")
                if from_type != to_type:
                    diff.type_changes[prop_path] = (from_type, to_type)

                # Check enum changes
                from_enum = from_def.get("enum", [])
                to_enum = to_def.get("enum", [])
                if from_enum != to_enum and (from_enum or to_enum):
                    diff.enum_changes[prop_path] = (from_enum, to_enum)

                # Check other modifications
                if from_def != to_def:
                    diff.modified_fields[prop_path] = {
                        "from": from_def,
                        "to": to_def
                    }

        return diff

    def detect_field_renames(self, diff: SchemaDiff) -> None:
        """Detect potential field renames based on type similarity."""
        # Simple heuristic: if a field was removed and another was added with the same type,
        # it might be a rename
        for removed_field, removed_def in diff.removed_fields.items():
            removed_type = removed_def.get("type")
            for added_field, added_def in diff.added_fields.items():
                added_type = added_def.get("type")
                if removed_type == added_type and removed_type:
                    # Ask user or use naming similarity heuristics
                    similarity = self.calculate_field_similarity(removed_field, added_field)
                    if similarity > 0.6:  # Threshold for potential rename
                        diff.renamed_fields[removed_field] = added_field
                        logging.info(f"Detected potential rename: {removed_field} -> {added_field}")

    def calculate_field_similarity(self, field1: str, field2: str) -> float:
        """Calculate similarity between two field names."""
        # Simple Levenshtein distance-based similarity
        def levenshtein_distance(s1: str, s2: str) -> int:
            if len(s1) < len(s2):
                return levenshtein_distance(s2, s1)
            if len(s2) == 0:
                return len(s1)

            previous_row = list(range(len(s2) + 1))
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row

            return previous_row[-1]

        distance = levenshtein_distance(field1.lower(), field2.lower())
        max_len = max(len(field1), len(field2))
        return 1 - (distance / max_len) if max_len > 0 else 0

    def generate_migration_code(self, from_version: str, to_version: str,
                              schema_name: str, diff: SchemaDiff) -> str:
        """Generate the migration class code."""
        class_name = f"Migration_{from_version.replace('.', '_')}_{to_version.replace('.', '_')}_{schema_name.replace('_', '')}"

        upgrade_code = self.generate_upgrade_method(diff, schema_name)
        downgrade_code = self.generate_downgrade_method(diff, schema_name)

        template = f'''"""
Migration from {from_version} to {to_version} for {schema_name}

Auto-generated migration script. Review and modify as needed.
"""

import logging
from typing import Dict, Any, List
from migration import Migration, MigrationData

logger = logging.getLogger(__name__)

class {class_name}(Migration):
    """Migration for {schema_name} from {from_version} to {to_version}."""

    VERSION = "{to_version}"

    def upgrade(self, data: MigrationData) -> MigrationData:
        """Upgrade {schema_name} data from {from_version} to {to_version}."""
        logger.info(f"Upgrading {{schema_name}} from {from_version} to {to_version}")

        if not isinstance(data, dict):
            logger.warning("Data is not a dictionary, returning as-is")
            return data

        migrated_data = data.copy()

{upgrade_code}

        logger.info(f"Successfully upgraded {{schema_name}} to {to_version}")
        return migrated_data

    def downgrade(self, data: MigrationData) -> MigrationData:
        """Downgrade {schema_name} data from {to_version} to {from_version}."""
        logger.info(f"Downgrading {{schema_name}} from {to_version} to {from_version}")

        if not isinstance(data, dict):
            logger.warning("Data is not a dictionary, returning as-is")
            return data

        migrated_data = data.copy()

{downgrade_code}

        logger.info(f"Successfully downgraded {{schema_name}} to {from_version}")
        return migrated_data
'''
        return template

    def generate_upgrade_method(self, diff: SchemaDiff, schema_name: str) -> str:
        """Generate the upgrade method code."""
        code_lines = []

        # Handle field renames first
        for old_field, new_field in diff.renamed_fields.items():
            code_lines.append(f"        # Rename field: {old_field} -> {new_field}")
            code_lines.append(f"        if '{old_field}' in migrated_data:")
            code_lines.append(f"            migrated_data['{new_field}'] = migrated_data.pop('{old_field}')")
            code_lines.append("")

        # Handle added fields
        for field_path, field_def in diff.added_fields.items():
            if field_path not in diff.renamed_fields.values():  # Skip if it's a rename target
                default_value = self.get_default_value(field_def)
                code_lines.append(f"        # Add new field: {field_path}")
                code_lines.append(f"        if '{field_path}' not in migrated_data:")
                code_lines.append(f"            migrated_data['{field_path}'] = {default_value}")
                code_lines.append("")

        # Handle type changes
        for field_path, (old_type, new_type) in diff.type_changes.items():
            code_lines.append(f"        # Convert {field_path} from {old_type} to {new_type}")
            code_lines.append(f"        if '{field_path}' in migrated_data:")
            conversion_code = self.generate_type_conversion(old_type, new_type)
            code_lines.append(f"            migrated_data['{field_path}'] = {conversion_code}(migrated_data['{field_path}'])")
            code_lines.append("")

        # Handle enum changes
        for field_path, (old_values, new_values) in diff.enum_changes.items():
            code_lines.append(f"        # Update enum values for {field_path}")
            code_lines.append(f"        if '{field_path}' in migrated_data:")
            enum_mapping = self.generate_enum_mapping(old_values, new_values)
            code_lines.append(f"            enum_mapping = {enum_mapping}")
            code_lines.append(f"            migrated_data['{field_path}'] = enum_mapping.get(migrated_data['{field_path}'], migrated_data['{field_path}'])")
            code_lines.append("")

        # Handle removed fields (in downgrade, we'll need to add them back)
        for field_path in diff.removed_fields:
            if field_path not in diff.renamed_fields:  # Skip if it's a rename source
                code_lines.append(f"        # Remove deprecated field: {field_path}")
                code_lines.append(f"        migrated_data.pop('{field_path}', None)")
                code_lines.append("")

        return "\n".join(code_lines) if code_lines else "        # No changes needed"

    def generate_downgrade_method(self, diff: SchemaDiff, schema_name: str) -> str:
        """Generate the downgrade method code (reverse of upgrade)."""
        code_lines = []

        # Reverse field renames
        for old_field, new_field in diff.renamed_fields.items():
            code_lines.append(f"        # Reverse rename: {new_field} -> {old_field}")
            code_lines.append(f"        if '{new_field}' in migrated_data:")
            code_lines.append(f"            migrated_data['{old_field}'] = migrated_data.pop('{new_field}')")
            code_lines.append("")

        # Remove added fields
        for field_path in diff.added_fields:
            if field_path not in diff.renamed_fields.values():
                code_lines.append(f"        # Remove field that was added: {field_path}")
                code_lines.append(f"        migrated_data.pop('{field_path}', None)")
                code_lines.append("")

        # Reverse type changes
        for field_path, (old_type, new_type) in diff.type_changes.items():
            code_lines.append(f"        # Convert {field_path} from {new_type} back to {old_type}")
            code_lines.append(f"        if '{field_path}' in migrated_data:")
            conversion_code = self.generate_type_conversion(new_type, old_type)
            code_lines.append(f"            migrated_data['{field_path}'] = {conversion_code}(migrated_data['{field_path}'])")
            code_lines.append("")

        # Reverse enum changes
        for field_path, (old_values, new_values) in diff.enum_changes.items():
            code_lines.append(f"        # Reverse enum values for {field_path}")
            code_lines.append(f"        if '{field_path}' in migrated_data:")
            enum_mapping = self.generate_enum_mapping(new_values, old_values)
            code_lines.append(f"            enum_mapping = {enum_mapping}")
            code_lines.append(f"            migrated_data['{field_path}'] = enum_mapping.get(migrated_data['{field_path}'], migrated_data['{field_path}'])")
            code_lines.append("")

        # Add back removed fields with default values
        for field_path, field_def in diff.removed_fields.items():
            if field_path not in diff.renamed_fields:
                default_value = self.get_default_value(field_def)
                code_lines.append(f"        # Add back removed field: {field_path}")
                code_lines.append(f"        if '{field_path}' not in migrated_data:")
                code_lines.append(f"            migrated_data['{field_path}'] = {default_value}")
                code_lines.append("")

        return "\n".join(code_lines) if code_lines else "        # No changes needed"

    def get_default_value(self, field_def: Dict[str, Any]) -> str:
        """Get a default value for a field based on its definition."""
        if "default" in field_def:
            return repr(field_def["default"])

        field_type = field_def.get("type", "string")
        if field_type == "string":
            return '""'
        elif field_type == "integer":
            return "0"
        elif field_type == "number":
            return "0.0"
        elif field_type == "boolean":
            return "False"
        elif field_type == "array":
            return "[]"
        elif field_type == "object":
            return "{}"
        else:
            return "None"

    def generate_type_conversion(self, from_type: str, to_type: str) -> str:
        """Generate type conversion code."""
        if from_type == to_type:
            return "lambda x: x"

        conversions = {
            ("string", "integer"): "int",
            ("string", "number"): "float",
            ("integer", "string"): "str",
            ("number", "string"): "str",
            ("integer", "number"): "float",
            ("number", "integer"): "int",
        }

        return conversions.get((from_type, to_type), "lambda x: x")

    def generate_enum_mapping(self, old_values: List[str], new_values: List[str]) -> Dict[str, str]:
        """Generate a mapping between old and new enum values."""
        # Simple heuristic: map by similarity
        mapping = {}
        used_new_values = set()

        for old_val in old_values:
            best_match = None
            best_similarity = 0

            for new_val in new_values:
                if new_val not in used_new_values:
                    similarity = self.calculate_field_similarity(old_val, new_val)
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = new_val

            if best_match and best_similarity > 0.5:
                mapping[old_val] = best_match
                used_new_values.add(best_match)
            else:
                # If no good match, keep the old value (might cause validation errors)
                mapping[old_val] = old_val

        return mapping

    def generate_migration_for_schema(self, from_version: str, to_version: str, schema_name: str) -> bool:
        """Generate a migration script for a specific schema."""
        from_schema = self.load_schema(from_version, schema_name)
        to_schema = self.load_schema(to_version, schema_name)

        if not from_schema and not to_schema:
            logging.warning(f"Neither version has schema '{schema_name}', skipping")
            return False

        if not from_schema:
            logging.info(f"Schema '{schema_name}' is new in {to_version}, creating add-only migration")
            # Create a migration that just validates the new schema exists
            diff = SchemaDiff(from_version, to_version)
        elif not to_schema:
            logging.info(f"Schema '{schema_name}' was removed in {to_version}, creating removal migration")
            # Create a migration that removes/archives the schema
            diff = SchemaDiff(from_version, to_version)
            diff.structural_changes.append(f"Schema {schema_name} removed")
        else:
            diff = self.compare_schemas(from_schema, to_schema)
            diff.from_version = from_version
            diff.to_version = to_version
            self.detect_field_renames(diff)

        # Generate migration code
        migration_code = self.generate_migration_code(from_version, to_version, schema_name, diff)

        # Write migration file
        migration_filename = f"{from_version}_to_{to_version}_{schema_name}.py"
        migration_path = self.migrations_dir / migration_filename

        with open(migration_path, 'w') as f:
            f.write(migration_code)

        logging.info(f"Generated migration: {migration_path}")
        return True

    def generate_migrations_between_versions(self, from_version: str, to_version: str) -> None:
        """Generate all migration scripts between two versions."""
        from_schemas = self.get_schema_names(from_version)
        to_schemas = self.get_schema_names(to_version)
        all_schemas = from_schemas | to_schemas

        logging.info(f"Generating migrations from {from_version} to {to_version}")
        logging.info(f"Schemas to process: {sorted(all_schemas)}")

        for schema_name in sorted(all_schemas):
            self.generate_migration_for_schema(from_version, to_version, schema_name)

    def generate_all_migrations(self) -> None:
        """Generate migration scripts for all version transitions."""
        versions = self.get_available_versions()

        if len(versions) < 2:
            logging.warning("Need at least 2 versions to generate migrations")
            return

        for i in range(len(versions) - 1):
            from_version = versions[i]
            to_version = versions[i + 1]
            self.generate_migrations_between_versions(from_version, to_version)

def main():
    """Main function to handle command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate migration scripts for Prism Task Manager",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        '--from-version',
        help="Source version (e.g., 'v0.0.0')"
    )
    parser.add_argument(
        '--to-version',
        help="Target version (e.g., 'v0.1.0')"
    )
    parser.add_argument(
        '--schema',
        help="Specific schema to migrate (e.g., 'project_bugs')"
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help="Generate migrations for all version transitions"
    )
    parser.add_argument(
        '--schemas-dir',
        default='schemas',
        help="Directory containing schema versions (default: 'schemas')"
    )

    args = parser.parse_args()

    generator = MigrationGenerator(args.schemas_dir)

    if args.all:
        generator.generate_all_migrations()
    elif args.from_version and args.to_version:
        if args.schema:
            generator.generate_migration_for_schema(args.from_version, args.to_version, args.schema)
        else:
            generator.generate_migrations_between_versions(args.from_version, args.to_version)
    else:
        parser.print_help()
        return

    logging.info("Migration generation complete!")

if __name__ == "__main__":
    main()
