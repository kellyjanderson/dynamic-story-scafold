from __future__ import annotations

import hashlib
import subprocess
from importlib.metadata import version
from pathlib import Path

from .database import Artifact, Build, Database, utc_now


def _git(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def record_build(directory: Path, database: Database) -> Build:
    directory = directory.resolve()
    artifacts = sorted(
        [*directory.glob("*.whl"), *directory.glob("*.tar.gz")],
        key=lambda path: path.name,
    )
    if not artifacts:
        raise ValueError(f"no wheel or sdist artifacts found in {directory}")

    database.migrate()
    with database.session() as session:
        build = Build(
            package_version=version("dynamic-story-scaffold"),
            git_commit=_git("rev-parse", "HEAD"),
            git_branch=_git("branch", "--show-current"),
            output_dir=str(directory),
            created_at=utc_now(),
        )
        build.artifacts = [
            Artifact(
                kind="wheel" if path.suffix == ".whl" else "sdist",
                path=str(path.resolve()),
                size_bytes=path.stat().st_size,
                sha256=_digest(path),
            )
            for path in artifacts
        ]
        session.add(build)
        session.flush()
        session.refresh(build)
        build_id = build.id

    with database.session() as session:
        return session.get(Build, build_id)
