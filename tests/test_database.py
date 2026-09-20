from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import inspect

from dynamic_story_scaffold.database import Database, DatabaseNotReady
from dynamic_story_scaffold.paths import DATA_DIR_ENV, database_path


def test_database_path_uses_override(monkeypatch, tmp_path: Path) -> None:
    data_root = tmp_path / "portable-data"
    monkeypatch.setenv(DATA_DIR_ENV, str(data_root))
    assert database_path() == data_root / "story-scaffold.sqlite3"


def test_setup_runs_alembic_and_records_install(monkeypatch, tmp_path: Path) -> None:
    data_root = tmp_path / "app-data"
    monkeypatch.setenv(DATA_DIR_ENV, str(data_root))

    database = Database()
    first = database.setup(package_version="1.2.3")
    second = database.setup(package_version="1.2.3")

    assert first.path.exists()
    assert first.revision == "0004"
    assert first.expected_revision == "0004"
    assert first.ready is True
    assert second.installation_count == 2

    tables = set(inspect(database.engine()).get_table_names())
    assert {
        "alembic_version",
        "installations",
        "settings",
        "simulation_runs",
        "timeline_branches",
        "checkpoints",
        "simulation_rounds",
    } <= tables
    assert "builds" not in tables
    assert "artifacts" not in tables


def test_status_before_setup_is_empty_and_non_mutating(tmp_path: Path) -> None:
    path = tmp_path / "missing" / "db.sqlite3"
    status = Database(path).status()

    assert status.revision is None
    assert status.expected_revision == "0004"
    assert status.ready is False
    assert status.installation_count == 0
    assert not path.exists()


def test_runtime_schema_check_does_not_create_or_migrate_database(tmp_path: Path) -> None:
    path = tmp_path / "missing.sqlite3"
    database = Database(path)

    with pytest.raises(DatabaseNotReady, match="dss-maintain setup"):
        database.require_current_schema()

    assert not path.exists()


def test_upgrade_schema_is_explicit_maintenance_operation(tmp_path: Path) -> None:
    database = Database(tmp_path / "story.sqlite3")
    database.upgrade_schema()

    database.require_current_schema()
    assert database.status().ready is True
    assert database.status().installation_count == 0
