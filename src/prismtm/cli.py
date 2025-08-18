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


@migrate.command()
def project():
    """Migrate project data to latest schema version."""
    click.echo("🚧 Project migration is coming soon!")


if __name__ == "__main__":
    main()
