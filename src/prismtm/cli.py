"""
Command Line Interface for Prism Task Manager.
"""

import click
import os
from pathlib import Path
from .version import VERSION
from .data import DataCore
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

    # Check if we're in a Prism project
    prsm_dir = Path.cwd() / '.prsm'
    if not prsm_dir.exists():
        click.echo("❌ Not in a Prism project directory")
        click.echo("💡 Run 'prsm init' to initialize a project")
        return

    click.echo("📁 Project Status:")
    click.echo(f"   📍 Location: {Path.cwd()}")

    # Check project files
    required_files = ['tasktree.yml']
    optional_files = ['time.yml', 'bugs.yml']

    click.echo("📋 Project Files:")
    for file in required_files:
        file_path = prsm_dir / file
        if file_path.exists():
            click.echo(f"   ✅ {file} (required)")
        else:
            click.echo(f"   ❌ {file} (required - missing!)")

    for file in optional_files:
        file_path = prsm_dir / file
        if file_path.exists():
            click.echo(f"   ✅ {file} (optional)")

    # Try to load and validate files using DataCore
    try:
        with DataCore.get_context() as context:
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
@click.option('--include-user/--no-include-user', default=False, help='Include user data in backup')
def create(name, include_user):
    """Create a backup of project data."""
    try:
        backup_manager = DataCore.get_backup_manager()
        backup_path = backup_manager.create_backup(name, include_user)
        click.echo(f"✅ Backup created: {backup_path}")

        if include_user:
            click.echo("📦 Included user data in backup")
        else:
            click.echo("💡 Use --include-user to backup user data as well")

    except Exception as e:
        click.echo(f"❌ Error creating backup: {e}")

@backup.command()
def list():
    """List all available backups."""
    try:
        backup_manager = DataCore.get_backup_manager()
        backups = backup_manager.list_backups()

        if not backups:
            click.echo("📭 No backups found")
            return

        click.echo("📦 Available backups:")
        click.echo("")

        for backup in backups:
            click.echo(f"🗂️  {backup['backup_folder']}")
            click.echo(f"   📅 Created: {backup['created_at']}")
            if backup['backup_name']:
                click.echo(f"   🏷️  Name: {backup['backup_name']}")
            click.echo(f"   📋 Project files: {len(backup['project_files'])}")
            if backup['includes_user_data']:
                click.echo(f"   👤 User files: {len(backup['user_files'])}")
            click.echo("")

    except Exception as e:
        click.echo(f"❌ Error listing backups: {e}")

@backup.command()
@click.argument('backup_folder')
@click.option('--include-user/--no-include-user', default=False, help='Restore user data as well')
@click.option('--files', help='Comma-separated list of specific files to restore')
@click.confirmation_option(prompt='Are you sure you want to restore from backup?')
def restore(backup_folder, include_user, files):
    """Restore from a backup."""
    try:
        backup_manager = DataCore.get_backup_manager()

        files_to_restore = None
        if files:
            files_to_restore = [f.strip() for f in files.split(',')]

        success = backup_manager.restore_backup(backup_folder, include_user, files_to_restore)

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
