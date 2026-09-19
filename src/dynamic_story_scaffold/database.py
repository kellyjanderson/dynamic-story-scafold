from __future__ import annotations

import platform
import sqlite3
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .paths import database_path

SCHEMA_VERSION = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


MIGRATIONS: dict[int, tuple[str, ...]] = {
    1: (
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS installations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_version TEXT NOT NULL,
            python_version TEXT NOT NULL,
            os_name TEXT NOT NULL,
            platform TEXT NOT NULL,
            database_path TEXT NOT NULL,
            installed_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS builds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_version TEXT NOT NULL,
            git_commit TEXT,
            git_branch TEXT,
            project_root TEXT NOT NULL,
            output_dir TEXT NOT NULL,
            status TEXT NOT NULL
                CHECK (status IN ('running', 'succeeded', 'failed')),
            started_at TEXT NOT NULL,
            finished_at TEXT,
            error TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            build_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            path TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(build_id) REFERENCES builds(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_artifacts_build_id
        ON artifacts(build_id)
        """,
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
    ),
}


@dataclass(frozen=True)
class DatabaseStatus:
    path: Path
    schema_version: int
    installation_count: int
    build_count: int


class Database:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else database_path()

    @contextmanager
    def connect(self, *, create_parent: bool = False) -> Iterator[sqlite3.Connection]:
        if create_parent:
            self.path.parent.mkdir(parents=True, exist_ok=True)

        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def install(self, *, package_version: str) -> DatabaseStatus:
        with self.connect(create_parent=True) as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            self._apply_migrations(connection)
            connection.execute(
                """
                INSERT INTO installations (
                    package_version,
                    python_version,
                    os_name,
                    platform,
                    database_path,
                    installed_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    package_version,
                    platform.python_version(),
                    platform.system(),
                    sys.platform,
                    str(self.path),
                    utc_now(),
                ),
            )
        return self.status()

    def ensure_schema(self) -> None:
        with self.connect(create_parent=True) as connection:
            self._apply_migrations(connection)

    def status(self) -> DatabaseStatus:
        if not self.path.exists():
            return DatabaseStatus(
                path=self.path,
                schema_version=0,
                installation_count=0,
                build_count=0,
            )

        with self.connect() as connection:
            self._ensure_migration_table(connection)
            version = connection.execute(
                "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
            ).fetchone()[0]
            if version == 0:
                return DatabaseStatus(
                    path=self.path,
                    schema_version=0,
                    installation_count=0,
                    build_count=0,
                )
            installations = connection.execute(
                "SELECT COUNT(*) FROM installations"
            ).fetchone()[0]
            builds = connection.execute("SELECT COUNT(*) FROM builds").fetchone()[0]

        return DatabaseStatus(
            path=self.path,
            schema_version=int(version),
            installation_count=int(installations),
            build_count=int(builds),
        )

    @staticmethod
    def _ensure_migration_table(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )

    def _apply_migrations(self, connection: sqlite3.Connection) -> None:
        self._ensure_migration_table(connection)
        applied = {
            int(row[0])
            for row in connection.execute(
                "SELECT version FROM schema_migrations"
            ).fetchall()
        }

        for version in sorted(MIGRATIONS):
            if version in applied:
                continue
            if version > SCHEMA_VERSION:
                break

            for statement in MIGRATIONS[version]:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (version, utc_now()),
            )
