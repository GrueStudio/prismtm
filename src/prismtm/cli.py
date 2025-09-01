"""
Command Line Interface for Prism Task Manager.
"""

import click
import os
from pathlib import Path

from prismtm.recovery import FatalError
from .version import VERSION
from .data import DataCore, BackupManager
from .models import TaskTree, ProjectBugList, GlobalBugList, ProjectTimeTracker

@click.group()
@click.version_option(version=VERSION, prog_name="prsm")
def main():
    """
    Prism Task Manager - A hierarchical task management system.

    This project is currently in development (Pre-Alpha phase).
    """
    pass


@main.command()
@click.option('--timetracking/--no-timetracking', default=None, help='Enable time tracking')
@click.option('--bugtracking/--no-bugtracking', default=None, help='Enable bug tracking')
def init(timetracking, bugtracking):
    """Initialize a new Prism project in the current directory."""
    current_dir = Path.cwd()
    prsm_dir = current_dir / '.prsm'

    # Check if already initialized
    if prsm_dir.exists():
        click.echo("❌ Project already initialized (.prsm directory exists)")
        return

    click.echo(f"🚀 Initializing Prism project in {current_dir}")

    # Ask for optional features if not specified
    if timetracking is None:
        timetracking = click.confirm("📊 Enable time tracking?", default=False)

    if bugtracking is None:
        bugtracking = click.confirm("🐛 Enable bug tracking?", default=False)

    try:
        # Create .prsm directory
        prsm_dir.mkdir(exist_ok=True)
        click.echo("📁 Created .prsm directory")

        # Create required tasktree.yml
        tasktree_file = prsm_dir / 'tasktree.yml'
        empty_tasktree = TaskTree(
            current_task_path="",
            nav_path=""
        )
        tasktree_file.write_text(empty_tasktree.to_yaml())
        click.echo("📋 Created tasktree.yml")

        # Create optional files based on user choice
        if timetracking:
            time_file = prsm_dir / 'time.yml'
            empty_time = ProjectTimeTracker()
            time_file.write_text(empty_time.to_yaml())
            click.echo("⏱️  Created time.yml")

        if bugtracking:
            bugs_file = prsm_dir / 'bugs.yml'
            empty_bugs = ProjectBugList()
            bugs_file.write_text(empty_bugs.to_yaml())
            click.echo("🐛 Created bugs.yml")

        click.echo("✅ Project initialized successfully!")
        click.echo("💡 Use 'prsm status' to verify your project setup")

    except Exception as e:
        click.echo(f"❌ Error initializing project: {e}")


@main.command()
def status():
    """Show the current project status and file information."""
    click.echo("🔧 Prism Task Manager")
    click.echo(f"📦 Version: {VERSION}")
    click.echo("📋 Current Phase: Pre-Alpha")
    click.echo("")
    data = DataCore()

    # Check if we're in a Prism project
    prsm_dir = Path.cwd() / '.prsm'
    if not prsm_dir.exists():
        click.echo("❌ Not in a Prism project directory")
        click.echo("💡 Run 'prsm init' to initialize a project")
        return

    click.echo("📁 Project Status:")
    click.echo(f"   📍 Location: {Path.cwd()}")

    try:
        data.validate_context()
    except FatalError as e:
        click.echo(f"Validation error: {e}")

    # Try to load and validate files using DataCore
    try:
        with data.load_context() as context:
            click.echo("")
            click.echo("🔍 File Validation:")

            # Check tasktree
            if hasattr(context.project, 'tasktree'):
                phases = len(context.project.tasktree.phases) if context.project.tasktree.phases else 0
                click.echo(f"   📋 TaskTree: {phases} phases")

            # Check time tracking
            if hasattr(context.project, 'time'):
                sessions = len(context.project.time.sessions) if context.project.time.sessions else 0
                click.echo(f"   ⏱️  Time Tracking: {sessions} sessions logged")

            # Check bug tracking
            if hasattr(context.project, 'bugs'):
                bugs = len(context.project.bugs.bugs) if context.project.bugs.bugs else 0
                click.echo(f"   🐛 Bug Tracking: {bugs} bugs tracked")

            click.echo("✅ All files loaded successfully!")

    except Exception as e:
        click.echo(f"⚠️  Warning: Error loading project files: {e}")


@main.group()
def subtask():
    """Manage subtasks (coming soon)."""
    pass


@subtask.command()
@click.option('-p', '--path', help='Task path (e.g., "pa/0.2.x/0.2.2/task 1")')
@click.argument('name')
def add(path, name):
    """Add a new subtask."""
    click.echo("🚧 Subtask management is coming soon!")
    if path:
        click.echo(f"📍 Path: {path}")
    click.echo(f"📝 Subtask: {name}")


@main.group()
def migrate():
    """Data migration commands (coming soon)."""
    pass


@main.group()
def backup():
    """Backup and recovery commands."""
    pass

@backup.command()
@click.option('--name', help='Custom name for the backup')
@click.option('--user', '-u', 'scope', flag_value='user', help='Backup user scope data')
@click.option('--project', '-p', 'scope', flag_value='project', default=True, help='Backup project scope data (default)')
def create(name, scope):
    """Create a backup of project data."""
    try:
        backup_manager = BackupManager()
        if scope == "project":
            backup_path = backup_manager.backup_project(name)
            click.echo(f"✅ Backup created: {backup_path}")
        elif scope == "user":
            backup_path = backup_manager.backup_user(name)
            click.echo(f"✅ Backup created: {backup_path}")

    except Exception as e:
        click.echo(f"❌ Error creating backup: {e}")

@backup.command()
@click.option('--user', '-u', 'scope', flag_value='user', help='Backup user scope data')
@click.option('--project', '-p', 'scope', flag_value='project', default=True, help='Backup project scope data (default)')
def list(scope):
    """List all available backups."""
    try:
        backup_manager = BackupManager()
        backups = backup_manager.list_project_backups() if scope == "project" else backup_manager.list_user_backups()

        if not backups:
            click.echo("📭 No backups found")
            return

        click.echo("📦 Available backups:")
        click.echo("")

        for backup in backups:
            click.echo(f"🗂️  {backup['backup_folder']}")
            click.echo(f"   📅 Created: {backup['created_at']}")
            if backup['backup_id']:
                click.echo(f"   🏷️  Name: {backup['backup_id']}")
            click.echo(f"   📋 Project files: {backup['files_count']}")
            click.echo("")

    except Exception as e:
        click.echo(f"❌ Error listing backups: {e}")

@backup.command()
@click.argument('backup_folder')
@click.option('--user', '-u', 'scope', flag_value='user', help='Backup user scope data')
@click.option('--project', '-p', 'scope', flag_value='project', default=True, help='Backup project scope data (default)')
@click.confirmation_option(prompt='Are you sure you want to restore from backup?')
def restore(backup_folder, scope, files):
    """Restore from a backup."""
    try:
        backup_manager = BackupManager()
        success = backup_manager.restore_user_backup(backup_folder) if scope =="user" else backup_manager.restore_project_backup(backup_folder)

        if success:
            click.echo("✅ Backup restored successfully")
            click.echo("💡 A backup of your previous state was created as 'pre_restore_backup'")
        else:
            click.echo("❌ Failed to restore backup")

    except Exception as e:
        click.echo(f"❌ Error restoring backup: {e}")

@backup.command()
@click.option('--keep', default=10, help='Number of backups to keep (default: 10)')
@click.confirmation_option(prompt='Are you sure you want to cleanup old backups?')
def cleanup(keep):
    """Remove old backups, keeping only the most recent ones."""
    try:
        backup_manager = DataCore.get_backup_manager()
        removed_count = backup_manager.cleanup_old_backups(keep)

        if removed_count > 0:
            click.echo(f"✅ Removed {removed_count} old backup(s)")
        else:
            click.echo("📦 No backups needed to be removed")

    except Exception as e:
        click.echo(f"❌ Error cleaning up backups: {e}")

if __name__ == "__main__":
    main()
