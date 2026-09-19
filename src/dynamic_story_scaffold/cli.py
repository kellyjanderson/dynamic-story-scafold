from __future__ import annotations

import json
import platform
import sys
from importlib.metadata import version
from pathlib import Path

import typer
from sqlalchemy import select

from .build_history import record_build
from .database import Build, Database
from .paths import data_dir, database_path

app = typer.Typer(no_args_is_help=True)
db_app = typer.Typer(no_args_is_help=True)
builds_app = typer.Typer(no_args_is_help=True)
app.add_typer(db_app, name="db")
app.add_typer(builds_app, name="builds")


def _database(path: Path | None) -> Database:
    return Database(path) if path is not None else Database()


def _emit(payload: object, json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps(payload, indent=2, sort_keys=True, default=str))
    else:
        if isinstance(payload, dict):
            for key, value in payload.items():
                typer.echo(f"{key}: {value}")
        elif isinstance(payload, list):
            for item in payload:
                typer.echo(item)
        else:
            typer.echo(payload)


@app.command()
def install(
    database: Path | None = typer.Option(None, "--database"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    db = _database(database)
    status = db.install(package_version=version("dynamic-story-scaffold"))
    _emit(
        {
            "installed": True,
            "package_version": version("dynamic-story-scaffold"),
            "database_path": str(status.path),
            "revision": status.revision,
            "installation_count": status.installation_count,
        },
        json_output,
    )


@app.command("paths")
def paths_command(json_output: bool = typer.Option(False, "--json")) -> None:
    _emit(
        {
            "os_name": platform.system(),
            "sys_platform": sys.platform,
            "data_directory": str(data_dir()),
            "database_path": str(database_path()),
        },
        json_output,
    )


@db_app.command("status")
def db_status(
    database: Path | None = typer.Option(None, "--database"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    status = _database(database).status()
    _emit(
        {
            "database_path": str(status.path),
            "revision": status.revision,
            "installation_count": status.installation_count,
            "build_count": status.build_count,
        },
        json_output,
    )


@builds_app.command("record")
def builds_record(
    directory: Path = typer.Argument(Path("dist")),
    database: Path | None = typer.Option(None, "--database"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    build_id, artifact_count = record_build(directory, _database(database))
    _emit(
        {"build_id": build_id, "artifact_count": artifact_count},
        json_output,
    )


@builds_app.command("list")
def builds_list(
    limit: int = typer.Option(20, "--limit", min=1),
    database: Path | None = typer.Option(None, "--database"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    db = _database(database)
    db.migrate()
    with db.session() as session:
        rows = session.scalars(
            select(Build).order_by(Build.id.desc()).limit(limit)
        ).all()
        payload = [
            {
                "id": row.id,
                "package_version": row.package_version,
                "git_commit": row.git_commit,
                "git_branch": row.git_branch,
                "output_dir": row.output_dir,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    _emit(payload, json_output)
