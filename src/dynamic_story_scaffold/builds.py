from __future__ import annotations

import hashlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .database import Database, utc_now
from .version import package_version


@dataclass(frozen=True)
class ArtifactRecord:
    path: Path
    kind: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class BuildRecord:
    id: int
    status: str
    package_version: str
    project_root: Path
    output_dir: Path
    git_commit: str | None
    git_branch: str | None
    artifacts: tuple[ArtifactRecord, ...] = ()
    error: str | None = None


def _git_value(project_root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = result.stdout.strip()
    return value or None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_kind(path: Path) -> str:
    lower = path.name.lower()
    if lower.endswith(".whl"):
        return "wheel"
    if lower.endswith(".tar.gz"):
        return "sdist"
    return "other"


class BuildManager:
    def __init__(self, database: Database | None = None) -> None:
        self.database = database or Database()

    def build(
        self,
        *,
        project_root: str | Path = ".",
        output_dir: str | Path = "dist",
        clean: bool = False,
    ) -> BuildRecord:
        root = Path(project_root).expanduser().resolve()
        out = Path(output_dir).expanduser()
        if not out.is_absolute():
            out = root / out
        out = out.resolve()

        self.database.ensure_schema()

        if clean and out.exists():
            self._clean_artifacts(out)
        out.mkdir(parents=True, exist_ok=True)

        version = package_version()
        git_commit = _git_value(root, "rev-parse", "HEAD")
        git_branch = _git_value(root, "branch", "--show-current")
        build_id = self._start_build(
            version=version,
            project_root=root,
            output_dir=out,
            git_commit=git_commit,
            git_branch=git_branch,
        )

        before = {
            path.resolve(): (path.stat().st_size, path.stat().st_mtime_ns)
            for path in self._iter_artifact_paths(out)
        }
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "build",
                    "--outdir",
                    str(out),
                    str(root),
                ],
                cwd=root,
                check=True,
            )
            candidates = []
            for path in self._iter_artifact_paths(out):
                resolved = path.resolve()
                signature = (path.stat().st_size, path.stat().st_mtime_ns)
                if clean or before.get(resolved) != signature:
                    candidates.append(path)
            artifacts = tuple(self._record_artifacts(build_id, candidates))
            self._finish_build(build_id, status="succeeded", error=None)
            return BuildRecord(
                id=build_id,
                status="succeeded",
                package_version=version,
                project_root=root,
                output_dir=out,
                git_commit=git_commit,
                git_branch=git_branch,
                artifacts=artifacts,
            )
        except Exception as exc:
            self._finish_build(build_id, status="failed", error=str(exc))
            raise

    def list_builds(self, *, limit: int = 20) -> tuple[BuildRecord, ...]:
        self.database.ensure_schema()
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, status, package_version, project_root, output_dir,
                       git_commit, git_branch, error
                FROM builds
                ORDER BY id DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()

            records: list[BuildRecord] = []
            for row in rows:
                artifacts = tuple(
                    ArtifactRecord(
                        path=Path(item["path"]),
                        kind=item["kind"],
                        size_bytes=int(item["size_bytes"]),
                        sha256=item["sha256"],
                    )
                    for item in connection.execute(
                        """
                        SELECT path, kind, size_bytes, sha256
                        FROM artifacts
                        WHERE build_id = ?
                        ORDER BY id
                        """,
                        (row["id"],),
                    ).fetchall()
                )
                records.append(
                    BuildRecord(
                        id=int(row["id"]),
                        status=row["status"],
                        package_version=row["package_version"],
                        project_root=Path(row["project_root"]),
                        output_dir=Path(row["output_dir"]),
                        git_commit=row["git_commit"],
                        git_branch=row["git_branch"],
                        artifacts=artifacts,
                        error=row["error"],
                    )
                )
        return tuple(records)

    @staticmethod
    def _iter_artifact_paths(output_dir: Path) -> Iterable[Path]:
        if not output_dir.exists():
            return ()
        return tuple(
            sorted(
                (
                    path
                    for path in output_dir.iterdir()
                    if path.is_file()
                    and (
                        path.name.lower().endswith(".whl")
                        or path.name.lower().endswith(".tar.gz")
                    )
                ),
                key=lambda path: path.name,
            )
        )

    @staticmethod
    def _clean_artifacts(output_dir: Path) -> None:
        for path in BuildManager._iter_artifact_paths(output_dir):
            path.unlink()

    def _start_build(
        self,
        *,
        version: str,
        project_root: Path,
        output_dir: Path,
        git_commit: str | None,
        git_branch: str | None,
    ) -> int:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO builds (
                    package_version,
                    git_commit,
                    git_branch,
                    project_root,
                    output_dir,
                    status,
                    started_at
                ) VALUES (?, ?, ?, ?, ?, 'running', ?)
                """,
                (
                    version,
                    git_commit,
                    git_branch,
                    str(project_root),
                    str(output_dir),
                    utc_now(),
                ),
            )
            return int(cursor.lastrowid)

    def _finish_build(
        self,
        build_id: int,
        *,
        status: str,
        error: str | None,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE builds
                SET status = ?, error = ?, finished_at = ?
                WHERE id = ?
                """,
                (status, error, utc_now(), build_id),
            )

    def _record_artifacts(
        self,
        build_id: int,
        paths: Iterable[Path],
    ) -> list[ArtifactRecord]:
        records: list[ArtifactRecord] = []
        with self.database.connect() as connection:
            for path in paths:
                record = ArtifactRecord(
                    path=path.resolve(),
                    kind=_artifact_kind(path),
                    size_bytes=path.stat().st_size,
                    sha256=_sha256(path),
                )
                connection.execute(
                    """
                    INSERT INTO artifacts (
                        build_id,
                        kind,
                        path,
                        size_bytes,
                        sha256,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        build_id,
                        record.kind,
                        str(record.path),
                        record.size_bytes,
                        record.sha256,
                        utc_now(),
                    ),
                )
                records.append(record)
        return records
