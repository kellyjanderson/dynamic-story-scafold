from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from dynamic_story_scaffold.cli import app

runner = CliRunner()


def test_install_command_initializes_database(tmp_path: Path) -> None:
    db_path = tmp_path / "state" / "story.sqlite3"
    result = runner.invoke(
        app,
        ["install", "--database", str(db_path), "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["installed"] is True
    assert payload["revision"] == "0002"
    assert Path(payload["database_path"]) == db_path
    assert db_path.exists()


def test_db_status_reports_initialized_database(tmp_path: Path) -> None:
    db_path = tmp_path / "story.sqlite3"
    assert runner.invoke(app, ["install", "--database", str(db_path)]).exit_code == 0

    result = runner.invoke(
        app,
        ["db", "status", "--database", str(db_path), "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["revision"] == "0002"
    assert payload["installation_count"] == 1
