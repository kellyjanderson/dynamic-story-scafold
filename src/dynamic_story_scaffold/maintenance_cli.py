from __future__ import annotations

import json
from importlib.metadata import version
from pathlib import Path

import typer

from .database import Database

app = typer.Typer(
    no_args_is_help=True,
    help="Installer and technical-support maintenance commands for Dynamic Story Scaffold.",
)
db_app = typer.Typer(no_args_is_help=True)
app.add_typer(db_app, name="db")


def _database(path: Path | None) -> Database:
    return Database(path) if path is not None else Database()


def _emit(payload: object, json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return
    if isinstance(payload, dict):
        for key, value in payload.items():
            typer.echo(f"{key}: {value}")
        return
    typer.echo(payload)


@app.command()
def setup(
    database: Path | None = typer.Option(None, "--database"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Initialize or upgrade application state after package installation."""

    status = _database(database).setup(
        package_version=version("dynamic-story-scaffold")
    )
    _emit(
        {
            "ready": status.ready,
            "package_version": version("dynamic-story-scaffold"),
            "database_path": str(status.path),
            "revision": status.revision,
            "expected_revision": status.expected_revision,
            "installation_count": status.installation_count,
        },
        json_output,
    )


@db_app.command("migrate")
def db_migrate(
    database: Path | None = typer.Option(None, "--database"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Upgrade database schema for installer/technical-support use."""

    db = _database(database)
    db.upgrade_schema()
    status = db.status()
    _emit(
        {
            "ready": status.ready,
            "database_path": str(status.path),
            "revision": status.revision,
            "expected_revision": status.expected_revision,
        },
        json_output,
    )


@db_app.command("status")
def db_status(
    database: Path | None = typer.Option(None, "--database"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Inspect database readiness without modifying it."""

    status = _database(database).status()
    _emit(
        {
            "ready": status.ready,
            "database_path": str(status.path),
            "revision": status.revision,
            "expected_revision": status.expected_revision,
            "installation_count": status.installation_count,
        },
        json_output,
    )
