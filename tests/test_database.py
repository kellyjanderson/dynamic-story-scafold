from __future__ import annotations

import sqlite3
from pathlib import Path

from dynamic_story_scaffold.database import Database, SCHEMA_VERSION
from dynamic_story_scaffold.paths import DATA_DIR_ENV, database_path


def test_database_path_uses_override(monkeypatch, tmp_path: Path) -> None:
    data_root = tmp_path / "portable-data"
    monkeypatch.setenv(DATA_DIR_ENV, str(data_root))

    assert database_path() == data_root / "story-scaffold.sqlite3"


def test_install_creates_and_migrates_database(monkeypatch, tmp_path: Path) -> None:
    data_root = tmp_path / "app-data"
    monkeypatch.setenv(DATA_DIR_ENV, str(data_root))

    database = Database()
    first = database.install(package_version="1.2.3")

    assert first.path.exists()
    assert first.schema_version == SCHEMA_VERSION
    assert first.installation_count == 1

    second = database.install(package_version="1.2.3")
    assert second.schema_version == SCHEMA_VERSION
    assert second.installation_count == 2

    with sqlite3.connect(second.path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

    assert {
        "schema_migrations",
        "installations",
        "builds",
        "artifacts",
        "settings",
    }.issubset(tables)


def test_status_before_install_is_empty(tmp_path: Path) -> None:
    database = Database(tmp_path / "missing" / "db.sqlite3")

    status = database.status()

    assert status.schema_version == 0
    assert status.installation_count == 0
    assert status.build_count == 0
