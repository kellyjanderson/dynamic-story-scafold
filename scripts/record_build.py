#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import tomllib

from git import InvalidGitRepositoryError, Repo


def _digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _git_metadata(project_root: Path) -> tuple[str | None, str | None]:
    try:
        repo = Repo(project_root, search_parent_directories=True)
    except InvalidGitRepositoryError:
        return None, None
    commit = repo.head.commit.hexsha
    branch = None if repo.head.is_detached else repo.active_branch.name
    return commit, branch


def build_manifest(directory: Path) -> dict[str, object]:
    directory = directory.resolve()
    project_root = directory.parent.resolve()
    pyproject = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))
    version = str(pyproject["project"]["version"])
    artifacts = sorted(
        [*directory.glob("*.whl"), *directory.glob("*.tar.gz")],
        key=lambda path: path.name,
    )
    if not artifacts:
        raise ValueError(f"no wheel or sdist artifacts found in {directory}")

    git_commit, git_branch = _git_metadata(project_root)
    return {
        "schema_version": 1,
        "package": "dynamic-story-scaffold",
        "package_version": version,
        "git_commit": git_commit,
        "git_branch": git_branch,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "artifacts": [
            {
                "kind": "wheel" if path.suffix == ".whl" else "sdist",
                "filename": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": _digest(path),
            }
            for path in artifacts
        ],
    }


def main(argv: list[str]) -> int:
    directory = Path(argv[1]) if len(argv) > 1 else Path("dist")
    manifest = build_manifest(directory)
    output = directory / "build-manifest.json"
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
