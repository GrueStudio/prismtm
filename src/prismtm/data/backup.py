import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from .io import atomic_write, DATA_JSON, load_json_file
from prismtm.logs import get_logger

log = get_logger('data.backup')

class BackupManager:
    PROJECT_BACKUP_DIR = Path(".prsm") / "backups"
    PRISM_PROJECT_DIR = Path(".prsm")
    USER_BACKUP_DIR = Path.home() / ".local" / "share" / "prismtm" / "backups"
    PRISM_USER_DIR = Path.home() / ".local" / "share" / "prismtm" / "data"

    def _generate_backup_id(self, custom_name: Optional[str] = None) -> str:
        """Generate a backup ID with timestamp and optional custom name"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if custom_name:
            # Sanitize custom name for filesystem
            safe_name = "".join(c for c in custom_name if c.isalnum() or c in ('-', '_')).strip()
            return f"{timestamp}_{safe_name}"
        return timestamp

    def _create_backup_metadata(self, backup_id: str, backup_type: str,
                              source_path: Path, files_copied: List[str],
                              custom_name: Optional[str] = None) -> Dict[str, Any]:
        """Create metadata for a backup"""
        return {
            "backup_id": backup_id,
            "backup_type": backup_type,  # "project" or "user"
            "created_at": datetime.now().isoformat(),
            "source_path": str(source_path),
            "custom_name": custom_name,
            "files_count": len(files_copied),
            "files": files_copied,
            "prism_version": "1.0"  # You might want to track this
        }

    def _copy_directory_contents(self, source: Path, destination: Path) -> List[str]:
        """Copy all files from source to destination, return list of copied files"""
        copied_files = []

        if not source.exists():
            return copied_files

        # Create destination directory
        destination.mkdir(parents=True, exist_ok=True)

        # Copy all files and subdirectories
        for item in source.rglob("*"):
            if item.is_file():
                # Calculate relative path from source
                relative_path = item.relative_to(source)
                dest_file = destination / relative_path

                # Create parent directories if needed
                dest_file.parent.mkdir(parents=True, exist_ok=True)

                # Copy file with metadata
                shutil.copy2(item, dest_file)
                copied_files.append(str(relative_path))

        return copied_files

    def backup_project(self, backup_name: Optional[str] = None) -> Path:
        """Create a backup of the current project's .prsm directory"""
        if not BackupManager.PROJECT_BACKUP_DIR.exists():
            raise FileNotFoundError(f"Project source directory {BackupManager.PROJECT_BACKUP_DIR} does not exist")

        # Generate backup ID and create backup directory
        backup_id = self._generate_backup_id(backup_name)
        backup_dir = self.PROJECT_BACKUP_DIR / backup_id

        # Copy all files from .prsm (excluding the backups directory itself)
        source_files = []
        backup_dir.mkdir(parents=True, exist_ok=True)

        for item in BackupManager.PRISM_PROJECT_DIR.iterdir():
            if item.name == "backups":  # Don't backup the backups directory
                continue
            elif item.is_file():
                shutil.copy2(item, backup_dir / item.name)
                source_files.append(item.name)
            elif item.is_dir():
                copied_files = self._copy_directory_contents(item, backup_dir / item.name)
                source_files.extend([f"{item.name}/{f}" for f in copied_files])

        # Create metadata file
        metadata = self._create_backup_metadata(
            backup_id, "project", BackupManager.PROJECT_BACKUP_DIR, source_files, backup_name
        )

        metadata_file = backup_dir / "backups.json"
        atomic_write(DATA_JSON, metadata_file, metadata, create_dirs=True)

        return backup_dir

    def backup_user(self, backup_name: Optional[str] = None) -> Path:
        """Create a backup of the user's prismtm directory"""
        if not BackupManager.USER_BACKUP_DIR.exists():
            raise FileNotFoundError(f"User source directory {BackupManager.USER_BACKUP_DIR} does not exist")

        # Generate backup ID and create backup directory
        backup_id = self._generate_backup_id(backup_name)
        backup_dir = self.USER_BACKUP_DIR / backup_id

        # Copy all files from user directory (excluding the backups directory)
        copied_files = []

        for item in BackupManager.PRISM_USER_DIR.iterdir():
            if item.name != "backups":  # Don't backup the backups directory
                if item.is_file():
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, backup_dir / item.name)
                    copied_files.append(item.name)
                elif item.is_dir():
                    files_in_dir = self._copy_directory_contents(item, backup_dir / item.name)
                    copied_files.extend([f"{item.name}/{f}" for f in files_in_dir])

        # Create metadata file
        metadata = self._create_backup_metadata(
            backup_id, "user", BackupManager.USER_BACKUP_DIR, copied_files, backup_name
        )

        metadata_file = backup_dir / "backups.json"
        atomic_write(DATA_JSON, metadata_file, metadata, create_dirs=True)

        return backup_dir

    def list_project_backups(self) -> List[Dict[str, Any]]:
        """List all available project backups"""
        backups = []

        if not self.PROJECT_BACKUP_DIR.exists():
            return backups

        for backup_dir in self.PROJECT_BACKUP_DIR.iterdir():
            if backup_dir.is_dir():
                metadata_file = backup_dir / "backups.json"
                if metadata_file.exists():
                    try:
                        metadata = load_json_file(metadata_file)
                    except Exception:
                        # If metadata is corrupted, create basic info from directory
                        metadata = {
                            "backup_id": backup_dir.name,
                            "backup_type": "project",
                            "created_at": "unknown",
                            "files_count": len(list(backup_dir.rglob("*"))),
                            "status": "metadata_corrupted"
                        }
                    if metadata != None:
                        metadata['backup_folder'] = backup_dir
                        backups.append(metadata)

        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return backups

    def list_user_backups(self) -> List[Dict[str, Any]]:
        """List all available user backups"""
        backups = []

        if not self.USER_BACKUP_DIR.exists():
            return backups

        for backup_dir in self.USER_BACKUP_DIR.iterdir():
            if backup_dir.is_dir():
                metadata_file = backup_dir / "backups.json"
                if metadata_file.exists():
                    try:
                        metadata = load_json_file(metadata_file)
                        backups.append(metadata)
                    except Exception:
                        # If metadata is corrupted, create basic info from directory
                        backups.append({
                            "backup_id": backup_dir.name,
                            "backup_type": "user",
                            "created_at": "unknown",
                            "files_count": len(list(backup_dir.rglob("*"))),
                            "status": "metadata_corrupted"
                        })

        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return backups

    def restore_project_backup(self, backup_id: str, create_safety_backup: bool = True) -> bool:
        """Restore a project backup"""
        backup_dir = self.PROJECT_BACKUP_DIR / backup_id

        if not backup_dir.exists():
            raise FileNotFoundError(f"Backup {backup_id} not found")

        # Create safety backup before restoration
        if create_safety_backup and BackupManager.PROJECT_BACKUP_DIR.exists():
            safety_backup_name = f"pre_restore_{backup_id}"
            self.backup_project(safety_backup_name)

        # Remove existing files (except backups directory)
        if BackupManager.PROJECT_BACKUP_DIR.exists():
            for item in BackupManager.PROJECT_BACKUP_DIR.iterdir():
                if item.name == "backups":
                    continue
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
        else:
            BackupManager.PROJECT_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        # Restore files from backup
        for item in backup_dir.iterdir():
            if item.name == "backups.json":
                continue
            dest_path = BackupManager.PROJECT_BACKUP_DIR / item.name
            if item.is_file():
                shutil.copy2(item, dest_path)
            elif item.is_dir():
                shutil.copytree(item, dest_path)

        return True

    def restore_user_backup(self, backup_id: str, create_safety_backup: bool = True) -> bool:
        """Restore a user backup"""
        backup_dir = self.USER_BACKUP_DIR / backup_id

        if not backup_dir.exists():
            raise FileNotFoundError(f"Backup {backup_id} not found")

        # Create safety backup before restoration
        if create_safety_backup and BackupManager.USER_BACKUP_DIR.exists():
            safety_backup_name = f"pre_restore_{backup_id}"
            self.backup_user(safety_backup_name)

        # Remove existing files (except backups directory)
        if BackupManager.PRISM_USER_DIR.exists():
            for item in BackupManager.USER_BACKUP_DIR.iterdir():
                if item.name in ["backups", "logs"]:
                    continue
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
        else:
            BackupManager.USER_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        # Restore files from backup
        for item in backup_dir.iterdir():
            if item.name in ["backups", "logs"]:
                continue
            dest_path = BackupManager.USER_BACKUP_DIR / item.name
            if item.is_file():
                shutil.copy2(item, dest_path)
            elif item.is_dir():
                shutil.copytree(item, dest_path)

        return True

    def delete_backup(self, backup_id: str, backup_type: str) -> bool:
        """Delete a specific backup"""
        if backup_type == "project":
            backup_dir = self.PROJECT_BACKUP_DIR / backup_id
        elif backup_type == "user":
            backup_dir = self.USER_BACKUP_DIR / backup_id
        else:
            raise ValueError("backup_type must be 'project' or 'user'")

        if backup_dir.exists():
            shutil.rmtree(backup_dir)
            return True
        return False

    def cleanup_old_backups(self, backup_type: str, keep_count: int = 10) -> int:
        """Clean up old backups, keeping only the most recent ones"""
        if backup_type == "project":
            backups = self.list_project_backups()
        elif backup_type == "user":
            backups = self.list_user_backups()
        else:
            raise ValueError("backup_type must be 'project' or 'user'")

        # Sort by creation time (newest first) and remove excess
        backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        deleted_count = 0

        for backup in backups[keep_count:]:
            if self.delete_backup(backup["backup_id"], backup_type):
                deleted_count += 1

        return deleted_count

    def get_backup_info(self, backup_id: str, backup_type: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific backup"""
        if backup_type == "project":
            backup_dir = self.PROJECT_BACKUP_DIR / backup_id
        elif backup_type == "user":
            backup_dir = self.USER_BACKUP_DIR / backup_id
        else:
            raise ValueError("backup_type must be 'project' or 'user'")

        metadata_file = backup_dir / "backups.json"
        if metadata_file.exists():
            try:
                return load_json_file(metadata_file)
            except Exception:
                return None
        return None
