from __future__ import annotations

import subprocess
from pathlib import Path

from dynamic_story_scaffold.builds import BuildManager
from dynamic_story_scaffold.database import Database


def test_build_manager_records_artifacts(monkeypatch, tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    output_dir = project_root / "dist"
    database = Database(tmp_path / "data" / "story.sqlite3")

    monkeypatch.setattr(
        "dynamic_story_scaffold.builds._git_value",
        lambda root, *args: (
            "deadbeef" if args == ("rev-parse", "HEAD") else "feature/test"
        ),
    )

    def fake_run(command, **kwargs):
        assert command[1:3] == ["-m", "build"]
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "dynamic_story_scaffold-0.1.0-py3-none-any.whl").write_bytes(
            b"wheel-v1"
        )
        (output_dir / "dynamic_story_scaffold-0.1.0.tar.gz").write_bytes(
            b"sdist-v1"
        )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("dynamic_story_scaffold.builds.subprocess.run", fake_run)

    record = BuildManager(database).build(
        project_root=project_root,
        output_dir=output_dir,
    )

    assert record.status == "succeeded"
    assert record.git_commit == "deadbeef"
    assert record.git_branch == "feature/test"
    assert {artifact.kind for artifact in record.artifacts} == {"wheel", "sdist"}
    assert all(len(artifact.sha256) == 64 for artifact in record.artifacts)

    listed = BuildManager(database).list_builds()
    assert len(listed) == 1
    assert listed[0].id == record.id
    assert len(listed[0].artifacts) == 2


def test_build_manager_detects_overwritten_same_name(monkeypatch, tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    output_dir = project_root / "dist"
    output_dir.mkdir()
    wheel = output_dir / "dynamic_story_scaffold-0.1.0-py3-none-any.whl"
    wheel.write_bytes(b"old-wheel")

    database = Database(tmp_path / "data" / "story.sqlite3")
    monkeypatch.setattr(
        "dynamic_story_scaffold.builds._git_value",
        lambda root, *args: None,
    )

    def fake_run(command, **kwargs):
        wheel.write_bytes(b"new-wheel-content")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("dynamic_story_scaffold.builds.subprocess.run", fake_run)

    record = BuildManager(database).build(
        project_root=project_root,
        output_dir=output_dir,
    )

    assert len(record.artifacts) == 1
    assert record.artifacts[0].path == wheel.resolve()
