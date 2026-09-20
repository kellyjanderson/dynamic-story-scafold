from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from dynamic_story_scaffold.maintenance_cli import app

runner = CliRunner()


def test_setup_initializes_database(tmp_path: Path) -> None:
    db_path = tmp_path / "state" / "story.sqlite3"
    result = runner.invoke(
        app,
        ["setup", "--database", str(db_path), "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ready"] is True
    assert payload["revision"] == "0004"
    assert payload["expected_revision"] == "0004"
    assert Path(payload["database_path"]) == db_path
    assert db_path.exists()


def test_db_status_is_read_only(tmp_path: Path) -> None:
    db_path = tmp_path / "missing.sqlite3"

    result = runner.invoke(
        app,
        ["db", "status", "--database", str(db_path), "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ready"] is False
    assert payload["revision"] is None
    assert not db_path.exists()


def test_db_migrate_is_maintenance_only_schema_upgrade(tmp_path: Path) -> None:
    db_path = tmp_path / "story.sqlite3"

    result = runner.invoke(
        app,
        ["db", "migrate", "--database", str(db_path), "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ready"] is True
    assert payload["revision"] == "0004"

    status = runner.invoke(
        app,
        ["db", "status", "--database", str(db_path), "--json"],
    )
    assert json.loads(status.output)["installation_count"] == 0
