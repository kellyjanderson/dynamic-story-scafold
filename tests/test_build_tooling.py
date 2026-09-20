from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_tool():
    path = Path(__file__).parents[1] / "scripts" / "record_build.py"
    spec = importlib.util.spec_from_file_location("dss_record_build", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_manifest_is_repository_artifact_not_application_state(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "dynamic-story-scaffold"\nversion = "1.2.3"\n',
        encoding="utf-8",
    )
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "dynamic_story_scaffold-1.2.3-py3-none-any.whl").write_bytes(b"wheel")
    (dist / "dynamic_story_scaffold-1.2.3.tar.gz").write_bytes(b"sdist")

    tool = _load_tool()
    tool._git_metadata = lambda _root: ("abc123", "feature/example")
    manifest = tool.build_manifest(dist)

    assert manifest["package_version"] == "1.2.3"
    assert manifest["git_commit"] == "abc123"
    assert manifest["git_branch"] == "feature/example"
    assert {item["kind"] for item in manifest["artifacts"]} == {"wheel", "sdist"}
    assert all("sha256" in item for item in manifest["artifacts"])
    assert not (tmp_path / "story-scaffold.sqlite3").exists()


def test_build_tool_writes_manifest_next_to_distribution(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "dynamic-story-scaffold"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "dynamic_story_scaffold-0.1.0-py3-none-any.whl").write_bytes(b"wheel")

    tool = _load_tool()
    tool._git_metadata = lambda _root: (None, None)
    assert tool.main(["record_build.py", str(dist)]) == 0

    payload = json.loads((dist / "build-manifest.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert len(payload["artifacts"]) == 1
