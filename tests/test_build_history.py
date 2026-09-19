from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from dynamic_story_scaffold.build_history import record_build
from dynamic_story_scaffold.database import Build, Database


def test_record_build_records_hatch_artifacts(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "dynamic_story_scaffold-0.1.0-py3-none-any.whl").write_bytes(b"wheel")
    (dist / "dynamic_story_scaffold-0.1.0.tar.gz").write_bytes(b"sdist")

    database = Database(tmp_path / "story.sqlite3")
    build_id, artifact_count = record_build(dist, database)

    assert artifact_count == 2
    with database.session() as session:
        build = session.scalar(select(Build).where(Build.id == build_id))
        assert build is not None
        assert Path(build.project_root) == tmp_path.resolve()
        assert Path(build.output_dir) == dist.resolve()
        assert len(build.artifacts) == 2
        assert {item.kind for item in build.artifacts} == {"wheel", "sdist"}
