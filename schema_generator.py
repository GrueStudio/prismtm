#!/usr/bin/env python3
"""
JSON Schema Generator Script

Generates JSON Schemas from Pydantic models in models.py.
"""

import json
import importlib.util
import inspect
import argparse
from pathlib import Path
from pydantic import BaseModel

# Try to import version from package __init__.py
try:
    from src.prismtm.version import VERSION, APP_SCHEMA_VERSION
    DEFAULT_VERSION = VERSION
except (ImportError, ValueError):
    try:
        from src.prismtm.version import VERSION, APP_SCHEMA_VERSION
        DEFAULT_VERSION = VERSION
    except ImportError:
        DEFAULT_VERSION = "0.0.0"
print("Default schema version:", DEFAULT_VERSION)


class SchemaGenerator:
    def __init__(self, base_version=None):
        self.base_version = base_version or DEFAULT_VERSION
        self.schemas_dir = Path("schemas")

    def generate_schema_from_pydantic_model(self, cls):
        """Generate JSON schema from Pydantic model."""
        if not (inspect.isclass(cls) and issubclass(cls, BaseModel)):
            raise ValueError(f"{cls.__name__} is not a Pydantic BaseModel")

        # Generate schema using Pydantic's built-in method
        schema = cls.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        return schema

    def find_schema_classes(self, models_module):
        """Find all Pydantic models marked with _schema_scope."""
        schema_classes = []

        def collect_classes(obj):
            for _, member in inspect.getmembers(obj, inspect.isclass):
                # Skip classes not from our module
                if getattr(member, '__module__', None) != models_module.__name__:
                    continue

                # Check if it's a Pydantic model with schema scope
                if (inspect.isclass(member) and
                    issubclass(member, BaseModel) and
                    hasattr(member, '_schema_scope')):
                    schema_classes.append(member)

                # Recursively check nested classes
                collect_classes(member)

        collect_classes(models_module)
        return schema_classes

    def generate_schemas(self, version=None):
        """Generate all schemas from models.py."""
        version_to_use = version or self.base_version
        models_path = Path("src/prismtm/models.py")
        if not models_path.exists():
            raise FileNotFoundError("src/prismtm/models.py not found")

        # Import the models module
        spec = importlib.util.spec_from_file_location("models", models_path)
        models_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(models_module)

        # Find all schema classes
        schema_classes = self.find_schema_classes(models_module)
        if not schema_classes:
            print("No Pydantic models with _schema_scope found")
            return

        # Create version directory
        version_dir = self.schemas_dir / f"v{version_to_use}"
        version_dir.mkdir(parents=True, exist_ok=True)

        # Generate schema for each class
        for cls in schema_classes:
            try:
                schema = self.generate_schema_from_pydantic_model(cls)

                scope_attr = getattr(cls, '_schema_scope', None)
                filename_attr = getattr(cls, '_schema_filename', None)

                # Handle case where attributes might be Field objects or direct values
                if hasattr(scope_attr, 'default'):
                    scope = scope_attr.default
                else:
                    scope = scope_attr

                if hasattr(filename_attr, 'default'):
                    filename = filename_attr.default
                else:
                    filename = filename_attr

                if not scope or not filename:
                    print(f"Skipping {cls.__name__}: missing _schema_scope or _schema_filename")
                    continue

                schema_filename = f"{scope}_{filename}.schema.json"

                # Write schema file
                schema_path = version_dir / schema_filename
                with open(schema_path, "w", encoding="utf-8") as f:
                    json.dump(schema, f, indent=2, ensure_ascii=False)

                print(f"Generated: {schema_path}")

            except Exception as e:
                print(f"Error generating schema for {cls.__name__}: {e}")
                import traceback
                traceback.print_exc()

        print(f"Schema generation complete! Files saved to {version_dir}")
        print(f"\n⚠️  IMPORTANT: If this is a new schema version, remember to update")
        print(f"   APP_SCHEMA_VERSION in src/prismtm/version.py to '{version_to_use}'")
        print(f"   Current APP_SCHEMA_VERSION: {DEFAULT_VERSION}")


def main():
    parser = argparse.ArgumentParser(description="Generate JSON schemas from Pydantic models")
    parser.add_argument("--version", "-v", help="Schema version (default: uses APP_SCHEMA_VERSION from version.py)")
    args = parser.parse_args()

    generator = SchemaGenerator()
    version_to_use = args.version or generator.base_version
    print(f"Generating schemas with version: {version_to_use}")

    try:
        generator.generate_schemas(version=args.version)
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
