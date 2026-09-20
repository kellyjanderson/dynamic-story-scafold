from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect, select

from dynamic_story_scaffold.database import Build, Database
from dynamic_story_scaffold.paths import DATA_DIR_ENV, database_path


def test_database_path_uses_override(monkeypatch, tmp_path: Path) -> None:
    data_root = tmp_path / "portable-data"
    monkeypatch.setenv(DATA_DIR_ENV, str(data_root))
    assert database_path() == data_root / "story-scaffold.sqlite3"


def test_install_runs_alembic_and_records_install(monkeypatch, tmp_path: Path) -> None:
    data_root = tmp_path / "app-data"
    monkeypatch.setenv(DATA_DIR_ENV, str(data_root))

    database = Database()
    first = database.install(package_version="1.2.3")
    second = database.install(package_version="1.2.3")

    assert first.path.exists()
    assert first.revision == "0002"
    assert second.revision == "0002"
    assert second.installation_count == 2

    tables = set(inspect(database.engine()).get_table_names())
    assert {"alembic_version", "installations", "builds", "artifacts", "settings"} <= tables


def test_status_before_install_is_empty(tmp_path: Path) -> None:
    status = Database(tmp_path / "missing" / "db.sqlite3").status()
    assert status.revision is None
    assert status.installation_count == 0
    assert status.build_count == 0


def test_build_table_is_queryable_after_migration(tmp_path: Path) -> None:
    database = Database(tmp_path / "story.sqlite3")
    database.migrate()
    with database.session() as session:
        assert session.scalars(select(Build)).all() == []
