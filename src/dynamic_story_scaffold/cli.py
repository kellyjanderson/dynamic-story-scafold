from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

import typer

from .application import ReplayMismatch, SimulationApplication
from .database import Database, DatabaseNotReady
from .paths import data_dir, database_path

app = typer.Typer(no_args_is_help=True)
scene_app = typer.Typer(no_args_is_help=True)
run_app = typer.Typer(no_args_is_help=True)
round_app = typer.Typer(no_args_is_help=True)
app.add_typer(scene_app, name="scene")
app.add_typer(run_app, name="run")
app.add_typer(round_app, name="round")


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


@app.command("paths")
def paths_command(json_output: bool = typer.Option(False, "--json")) -> None:
    """Show the installed application's runtime-state locations."""

    _emit(
        {
            "os_name": platform.system(),
            "sys_platform": sys.platform,
            "data_directory": str(data_dir()),
            "database_path": str(database_path()),
        },
        json_output,
    )


def _application(path: Path | None) -> SimulationApplication:
    return SimulationApplication(_database(path))


def _service_command(action, *, json_output: bool) -> None:
    try:
        _emit(action(), json_output)
    except (
        FileNotFoundError,
        KeyError,
        ValueError,
        ReplayMismatch,
        DatabaseNotReady,
        RuntimeError,
    ) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from exc


@scene_app.command("validate")
def scene_validate(
    path: Path,
    database: Path | None = typer.Option(None, "--database"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _service_command(
        lambda: _application(database).validate_scene(path),
        json_output=json_output,
    )


@run_app.command("start")
def run_start(
    path: Path,
    seed: int | None = typer.Option(None, "--seed"),
    database: Path | None = typer.Option(None, "--database"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _service_command(
        lambda: _application(database).start_run(path, seed=seed),
        json_output=json_output,
    )


@run_app.command("advance")
def run_advance(
    run_or_branch_id: str,
    database: Path | None = typer.Option(None, "--database"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _service_command(
        lambda: _application(database).advance_run(run_or_branch_id),
        json_output=json_output,
    )


@run_app.command("show")
def run_show(
    run_or_branch_id: str,
    database: Path | None = typer.Option(None, "--database"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _service_command(
        lambda: _application(database).show_run(run_or_branch_id),
        json_output=json_output,
    )


@round_app.command("show")
def round_show(
    round_id: str,
    database: Path | None = typer.Option(None, "--database"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _service_command(
        lambda: _application(database).show_round(round_id),
        json_output=json_output,
    )


@run_app.command("replay")
def run_replay(
    round_id: str,
    database: Path | None = typer.Option(None, "--database"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _service_command(
        lambda: _application(database).replay_round(round_id),
        json_output=json_output,
    )
