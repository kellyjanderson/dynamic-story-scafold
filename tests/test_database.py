from __future__ import annotations

import sqlite3
from pathlib import Path

from dynamic_story_scaffold.database import Database, SCHEMA_VERSION
from dynamic_story_scaffold.paths import DATA_DIR_ENV, database_path


def test_database_path_uses_override(monkeypatch, tmp_path: Path) -> None:
    data_root = tmp_path / "portable-data"
    monkeypatch.setenv(DATA_DIR_ENV, str(data_root))

    assert database_path() == data_root / "story-scaffold.sqlite3"


def test_install_creates_database(monkeypatch, tmp_path: Path) -> None:
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
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

    assert version == SCHEMA_VERSION
    assert {
        "installations",
        "builds",
        "artifacts",
        "settings",
    }.issubset(tables)


def test_record_build_uses_application_database(tmp_path: Path) -> None:
    database = Database(tmp_path / "data" / "story.sqlite3")
    artifact = tmp_path / "dist" / "package.whl"
    artifact.parent.mkdir()
    artifact.write_bytes(b"wheel")

    build_id = database.record_build(
        package_version="1.2.3",
        project_root=tmp_path,
        output_dir=artifact.parent,
        git_commit="deadbeef",
        git_branch="feature/test",
        artifacts=[("wheel", artifact, artifact.stat().st_size, "abc123")],
    )

    rows = database.recent_builds()
    assert len(rows) == 1
    assert rows[0]["id"] == build_id
    assert rows[0]["git_commit"] == "deadbeef"


def test_status_before_install_is_empty(tmp_path: Path) -> None:
    database = Database(tmp_path / "missing" / "db.sqlite3")

    status = database.status()

    assert status.schema_version == 0
    assert status.installation_count == 0
    assert status.build_count == 0
