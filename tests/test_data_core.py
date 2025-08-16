"""Unit tests for DataCore class."""

import pytest
import tempfile
import yaml
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.prismtm.data import DataCore
from src.prismtm.version import APP_SCHEMA_VERSION
from src.prismtm.models import TaskTree, ProjectBugList, GlobalBugList, TaskStatus, BugStatus


class TestDataCore:
    """Test DataCore functionality."""

    def test_get_schema_versions(self):
        """Test getting available schema versions."""
        with patch.object(DataCore, 'get_schema_dir') as mock_schema_dir:
            # Mock schema directory structure
            mock_dir = MagicMock()
            mock_dir.exists.return_value = True
            mock_dir.iterdir.return_value = [
                MagicMock(is_dir=lambda: True, name='v0.0.0'),
                MagicMock(is_dir=lambda: True, name='v0.1.0'),
                MagicMock(is_dir=lambda: True, name='v1.0.0'),
                MagicMock(is_dir=lambda: False, name='readme.txt'),  # Should be ignored
            ]
            mock_schema_dir.return_value = mock_dir

            versions = DataCore.get_schema_versions()
            # Should be sorted newest to oldest
            assert versions == ['1.0.0', '0.1.0', '0.0.0']

    def test_get_latest_schema_version(self):
        """Test getting the latest schema version."""
        with patch.object(DataCore, 'get_schema_versions') as mock_versions:
            mock_versions.return_value = ['1.0.0', '0.1.0', '0.0.0']
            assert DataCore.get_latest_schema_version() == '1.0.0'

            # Empty versions
            mock_versions.return_value = []
            assert DataCore.get_latest_schema_version() == '0.0.0'

    def test_check_required_files_exist(self):
        """Test checking for required files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create some test files
            (temp_path / "project_tasks.yaml").touch()
            (temp_path / "project_bugs.yaml").touch()

            file_mapping = {
                "project_tasks.yaml": "project_tasks.schema.json",
                "project_bugs.yaml": "project_bugs.schema.json",
                "user_bugs.yaml": "user_bugs.schema.json"
            }

            existing, missing = DataCore.check_required_files_exist(temp_path, file_mapping)

            assert "project_tasks.yaml" in existing
            assert "project_bugs.yaml" in existing
            assert "user_bugs.yaml" in missing

    def test_validate_returns_versions(self):
        """Test that validate returns version tuple."""
        with patch.object(DataCore, 'validate_project_data') as mock_project, \
             patch.object(DataCore, 'validate_user_data') as mock_user:

            mock_project.return_value = (True, '0.1.0', [])
            mock_user.return_value = (True, '0.1.0', [])

            project_ver, user_ver, app_ver = DataCore.validate()

            assert project_ver == '0.1.0'
            assert user_ver == '0.1.0'
            assert app_ver == APP_SCHEMA_VERSION

    def test_validate_with_actual_models(self):
        """Test validation with actual model data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create valid TaskTree data
            task_tree = TaskTree(
                current_task_path="pa/0.1.x/0.1.0/setup",
                nav_path="pa/0.1.x/0.1.0",
                phases=[
                    TaskTree.Phase(
                        name="pa",
                        version_match="0.1.*",
                        milestones=[
                            TaskTree.Milestone(
                                versions="0.1.x",
                                reason="Initial development",
                                blocks=[
                                    TaskTree.Block(
                                        version="0.1.0",
                                        reason="Core functionality",
                                        tasks=[
                                            TaskTree.Task(
                                                name="setup",
                                                reason="Setup project structure"
                                            )
                                        ]
                                    )
                                ]
                            )
                        ]
                    )
                ]
            )

            # Create valid ProjectBugList data
            project_bugs = ProjectBugList(
                bugs={
                    "prism": [
                        ProjectBugList.Bug(
                            id="bug-001",
                            title="Test bug",
                            version="0.1.0",
                            description="A test bug",
                            status=BugStatus.OPEN,
                            priority="medium",
                            opened_at=datetime.now()
                        )
                    ]
                }
            )

            # Write test data files
            with open(temp_path / "project_tasks.yaml", 'w') as f:
                yaml.dump(task_tree.model_dump(), f)

            with open(temp_path / "project_bugs.yaml", 'w') as f:
                yaml.dump(project_bugs.model_dump(), f)

            # Mock schema loading and validation
            with patch.object(DataCore, 'get_schema_dir') as mock_schema_dir, \
                 patch.object(DataCore, 'get_schema_versions') as mock_versions, \
                 patch('src.data_core.validate_data_against_schema') as mock_validate:

                mock_versions.return_value = ['0.1.0']
                mock_validate.return_value = (True, [])

                # Test project data validation
                is_valid, version, errors = DataCore.validate_project_data(temp_path)

                assert is_valid is True
                assert version == '0.1.0'
                assert errors == []

    def test_check_migration_needed(self):
        """Test checking if migration is needed."""
        with patch.object(DataCore, 'validate') as mock_validate:
            # No migration needed
            mock_validate.return_value = ('0.1.0', '0.1.0', '0.1.0')
            result = DataCore.check_migration_needed()
            assert result == {'project': False, 'user': False}

            # Migration needed
            mock_validate.return_value = ('0.0.0', '0.0.0', '0.1.0')
            result = DataCore.check_migration_needed()
            assert result == {'project': True, 'user': True}

    @patch('src.data_core.MigrationEngine')
    def test_migrate_project_data(self, mock_engine_class):
        """Test project data migration."""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.migrate_project_files.return_value = True

        result = DataCore.migrate_project_data('1.0.0')

        assert result is True
        mock_engine.migrate_project_files.assert_called_once_with('1.0.0')

    @patch('src.data_core.MigrationEngine')
    def test_migrate_user_data(self, mock_engine_class):
        """Test user data migration."""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.migrate_user_files.return_value = True

        result = DataCore.migrate_user_data()

        assert result is True
        mock_engine.migrate_user_files.assert_called_once_with(APP_SCHEMA_VERSION)

    def test_model_validation_with_invalid_data(self):
        """Test that models properly validate data."""
        # Test invalid task path
        with pytest.raises(ValueError, match="Invalid task path format"):
            TaskTree(
                current_task_path="invalid//path",
                nav_path="pa/0.1.x"
            )

        # Test invalid version format
        with pytest.raises(ValueError, match="Invalid version format"):
            TaskTree.Block(
                version="invalid.version",
                reason="Test block"
            )

        # Test invalid date sequence
        with pytest.raises(ValueError, match="finished_at must be after started_at"):
            TaskTree.Task(
                name="test",
                reason="Test task",
                started_at=datetime(2024, 1, 2),
                finished_at=datetime(2024, 1, 1)
            )

    def test_task_path_parsing(self):
        """Test TaskPath utility functionality."""
        from src.models import TaskPath

        # Valid path parsing
        path = TaskPath("pa/0.1.x/0.1.0/setup")
        assert path.phase == "pa"
        assert path.milestone == "0.1.x"
        assert path.block == "0.1.0"
        assert path.task == "setup"

        # Partial path parsing
        path = TaskPath("pa/0.1.x")
        assert path.phase == "pa"
        assert path.milestone == "0.1.x"
        assert path.block is None
        assert path.task is None

        # Invalid path
        with pytest.raises(ValueError):
            TaskPath("invalid//path")

        # Version validation
        assert TaskPath.validate_version("0.1.0") is True
        assert TaskPath.validate_version("1.2.x") is True
        assert TaskPath.validate_version("invalid") is False
