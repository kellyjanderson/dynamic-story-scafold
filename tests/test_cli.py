from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from dynamic_story_scaffold.cli import app

runner = CliRunner()


def test_runtime_cli_exposes_paths_without_initializing_database(
    monkeypatch, tmp_path: Path
) -> None:
    data_dir = tmp_path / "runtime-data"
    monkeypatch.setenv("DYNAMIC_STORY_SCAFFOLD_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["paths", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert Path(payload["data_directory"]) == data_dir
    assert Path(payload["database_path"]) == data_dir / "story-scaffold.sqlite3"
    assert not data_dir.exists()


def test_runtime_cli_does_not_expose_install_or_build_commands() -> None:
    for command in ("install", "builds", "db"):
        result = runner.invoke(app, [command])
        assert result.exit_code != 0
        assert "no such command" in result.output.lower()


def test_runtime_command_requires_prepared_application_state(tmp_path: Path) -> None:
    db_path = tmp_path / "missing.sqlite3"

    result = runner.invoke(
        app,
        [
            "run",
            "show",
            "not-a-real-id",
            "--database",
            str(db_path),
            "--json",
        ],
    )

    assert result.exit_code == 2
    assert "dss-maintain setup" in result.output
    assert not db_path.exists()
