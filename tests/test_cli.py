from __future__ import annotations

import json
from pathlib import Path

from dynamic_story_scaffold.cli import main


def test_install_command_initializes_database(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "state" / "story.sqlite3"

    exit_code = main(
        [
            "--database",
            str(db_path),
            "install",
            "--json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["installed"] is True
    assert payload["schema_version"] == 1
    assert Path(payload["database_path"]) == db_path
    assert db_path.exists()


def test_db_status_reports_initialized_database(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "story.sqlite3"

    assert main(["--database", str(db_path), "install", "--json"]) == 0
    capsys.readouterr()

    assert main(["--database", str(db_path), "db", "status", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema_version"] == 1
    assert payload["installation_count"] == 1
