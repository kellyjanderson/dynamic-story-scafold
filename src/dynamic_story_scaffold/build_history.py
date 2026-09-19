from __future__ import annotations

import hashlib
from importlib.metadata import version
from pathlib import Path

from git import InvalidGitRepositoryError, Repo

from .database import Artifact, Build, Database, utc_now


def _git_metadata(project_root: Path) -> tuple[str | None, str | None]:
    try:
        repo = Repo(project_root, search_parent_directories=True)
    except InvalidGitRepositoryError:
        return None, None

    commit = repo.head.commit.hexsha
    branch = None if repo.head.is_detached else repo.active_branch.name
    return commit, branch


def _digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def record_build(directory: Path, database: Database) -> tuple[int, int]:
    directory = directory.resolve()
    project_root = directory.parent.resolve()
    artifacts = sorted(
        [*directory.glob("*.whl"), *directory.glob("*.tar.gz")],
        key=lambda path: path.name,
    )
    if not artifacts:
        raise ValueError(f"no wheel or sdist artifacts found in {directory}")

    git_commit, git_branch = _git_metadata(project_root)
    database.migrate()
    with database.session() as session:
        build = Build(
            package_version=version("dynamic-story-scaffold"),
            git_commit=git_commit,
            git_branch=git_branch,
            project_root=str(project_root),
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
        return build.id, len(build.artifacts)
