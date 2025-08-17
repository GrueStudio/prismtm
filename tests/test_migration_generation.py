"""Unit tests for migration generator."""

import pytest
import json
from unittest.mock import patch, mock_open
from migration_generator import MigrationGenerator, SchemaDiff


class TestSchemaDiff:
    """Test schema difference detection."""

    def test_detect_added_fields(self):
        """Test detecting added fields."""
        old_schema = {
            "properties": {
                "name": {"type": "string"}
            }
        }
        new_schema = {
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"}
            }
        }

        generator = MigrationGenerator()
        diff = generator.compare_schemas(old_schema, new_schema)
        assert "email" in diff.added_fields
        assert len(diff.removed_fields) == 0

    def test_detect_removed_fields(self):
        """Test detecting removed fields."""
        old_schema = {
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"}
            }
        }
        new_schema = {
            "properties": {
                "name": {"type": "string"}
            }
        }

        generator = MigrationGenerator()
        diff = generator.compare_schemas(old_schema, new_schema)
        assert "email" in diff.removed_fields
        assert len(diff.added_fields) == 0

    def test_detect_type_changes(self):
        """Test detecting type changes."""
        old_schema = {
            "properties": {
                "age": {"type": "string"}
            }
        }
        new_schema = {
            "properties": {
                "age": {"type": "integer"}
            }
        }

        generator = MigrationGenerator()
        diff = generator.compare_schemas(old_schema, new_schema)
        assert "age" in diff.type_changes
        assert diff.type_changes["age"] == ("string", "integer")


class TestMigrationGenerator:
    """Test migration script generation."""

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.mkdir')
    def test_generate_migration(self, mock_mkdir, mock_exists, mock_json_load, mock_file):
        """Test generating a migration script."""
        mock_exists.return_value = True

        # Mock schema files
        old_schema = {"properties": {"name": {"type": "string"}}}
        new_schema = {"properties": {"name": {"type": "string"}, "email": {"type": "string"}}}

        mock_json_load.side_effect = [old_schema, new_schema]

        generator = MigrationGenerator()

        with patch('builtins.open', mock_open()) as mock_write:
            result = generator.generate_migration_for_schema("v0.0.0", "v0.1.0", "test_schema")
            assert result is True
            # Verify that a file was written
            mock_write.assert_called()
            # Verify mkdir was called
            mock_mkdir.assert_called()
