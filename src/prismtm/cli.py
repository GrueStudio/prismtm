"""
Command Line Interface for Prism Task Manager.
"""

import click
from .version import VERSION


@click.group()
@click.version_option(version=VERSION, prog_name="prsm")
def main():
    """
    Prism Task Manager - A hierarchical task management system.

    This project is currently in development (Pre-Alpha phase).
    """
    pass


@main.command()
def status():
    """Show the current development status of Prism Task Manager."""
    click.echo("🔧 Prism Task Manager is currently in development!")
    click.echo(f"📦 Version: {VERSION}")
    click.echo("📋 Current Phase: Pre-Alpha")
    click.echo("")
    click.echo("🚧 This tool is not yet ready for production use.")
    click.echo("📖 Check the documentation for development progress.")
    click.echo("")
    click.echo("💡 Available commands will be added as development progresses.")


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
