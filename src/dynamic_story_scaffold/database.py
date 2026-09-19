from __future__ import annotations

import platform
import sqlite3
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

from .paths import database_path

SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS installations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_version TEXT NOT NULL,
    python_version TEXT NOT NULL,
    os_name TEXT NOT NULL,
    platform TEXT NOT NULL,
    database_path TEXT NOT NULL,
    installed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS builds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_version TEXT NOT NULL,
    git_commit TEXT,
    git_branch TEXT,
    project_root TEXT NOT NULL,
    output_dir TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    build_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    FOREIGN KEY(build_id) REFERENCES builds(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_artifacts_build_id ON artifacts(build_id);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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

    def ensure_schema(self) -> None:
        with self.connect(create_parent=True) as connection:
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version > SCHEMA_VERSION:
                raise RuntimeError(
                    f"database schema {version} is newer than supported {SCHEMA_VERSION}"
                )
            if version < 1:
                connection.executescript(SCHEMA_SQL)
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            connection.execute("PRAGMA journal_mode = WAL")

    def install(self, *, package_version: str) -> DatabaseStatus:
        self.ensure_schema()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO installations (
                    package_version, python_version, os_name, platform,
                    database_path, installed_at
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

    def record_build(
        self,
        *,
        package_version: str,
        project_root: Path,
        output_dir: Path,
        git_commit: str | None,
        git_branch: str | None,
        artifacts: Iterable[tuple[str, Path, int, str]],
        status: str = "succeeded",
    ) -> int:
        self.ensure_schema()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO builds (
                    package_version, git_commit, git_branch, project_root,
                    output_dir, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    package_version,
                    git_commit,
                    git_branch,
                    str(project_root),
                    str(output_dir),
                    status,
                    utc_now(),
                ),
            )
            build_id = int(cursor.lastrowid)
            connection.executemany(
                """
                INSERT INTO artifacts (
                    build_id, kind, path, size_bytes, sha256
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (build_id, kind, str(path), size, sha256)
                    for kind, path, size, sha256 in artifacts
                ],
            )
        return build_id

    def recent_builds(self, *, limit: int = 20) -> list[sqlite3.Row]:
        self.ensure_schema()
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT id, package_version, git_commit, git_branch,
                       project_root, output_dir, status, created_at
                FROM builds
                ORDER BY id DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()

    def status(self) -> DatabaseStatus:
        if not self.path.exists():
            return DatabaseStatus(self.path, 0, 0, 0)

        with self.connect() as connection:
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version == 0:
                return DatabaseStatus(self.path, 0, 0, 0)
            installations = int(
                connection.execute("SELECT COUNT(*) FROM installations").fetchone()[0]
            )
            builds = int(connection.execute("SELECT COUNT(*) FROM builds").fetchone()[0])
        return DatabaseStatus(self.path, version, installations, builds)
