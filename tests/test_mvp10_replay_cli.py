from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dynamic_story_scaffold.application import SimulationApplication
from dynamic_story_scaffold.cli import app
from dynamic_story_scaffold.database import Database

EXAMPLE = Path(__file__).parents[1] / "examples" / "hollow_bank.yaml"
runner = CliRunner()


@pytest.mark.integration
def test_application_start_advance_inspect_and_replay_is_idempotent(tmp_path: Path) -> None:
    db = Database(tmp_path / "story.sqlite3")
    db.setup(package_version="test")
    service = SimulationApplication(db)

    validated = service.validate_scene(EXAMPLE)
    assert validated["valid"] is True
    assert validated["scene_id"] == "Hollow Bank First Contact"

    started = service.start_run(EXAMPLE, seed=4242)
    first_head = started["checkpoint_id"]
    advanced = service.advance_run(started["run_id"])

    assert advanced["run_id"] == started["run_id"]
    assert advanced["branch_id"] == started["branch_id"]
    assert advanced["input_checkpoint_id"] == first_head
    assert advanced["output_checkpoint_id"] != first_head
    assert advanced["entropy"]["root_seed"] == 4242
    assert advanced["intents"]
    assert advanced["resolutions"]
    assert "arbitrations" in advanced["execution"]
    assert "proposals" in advanced["execution"]
    assert isinstance(advanced["state_diff"], list)

    shown = service.show_round(advanced["round_id"])
    assert shown == advanced

    head_after_advance = service.show_run(started["run_id"])["checkpoint_id"]
    replay_one = service.replay_round(advanced["round_id"])
    replay_two = service.replay_round(advanced["round_id"])

    assert replay_one["matched"] is True
    assert replay_one["output_match"] is True
    assert replay_one["audit_match"] is True
    assert replay_two == replay_one
    assert service.show_run(started["run_id"])["checkpoint_id"] == head_after_advance


@pytest.mark.integration
def test_cli_json_covers_complete_hollow_bank_round_and_replay(tmp_path: Path) -> None:
    db_path = tmp_path / "cli.sqlite3"
    Database(db_path).setup(package_version="test")

    validated = runner.invoke(
        app,
        ["scene", "validate", str(EXAMPLE), "--database", str(db_path), "--json"],
    )
    assert validated.exit_code == 0, validated.output
    assert json.loads(validated.output)["valid"] is True

    started = runner.invoke(
        app,
        [
            "run",
            "start",
            str(EXAMPLE),
            "--seed",
            "73",
            "--database",
            str(db_path),
            "--json",
        ],
    )
    assert started.exit_code == 0, started.output
    run_payload = json.loads(started.output)

    advanced = runner.invoke(
        app,
        [
            "run",
            "advance",
            run_payload["run_id"],
            "--database",
            str(db_path),
            "--json",
        ],
    )
    assert advanced.exit_code == 0, advanced.output
    round_payload = json.loads(advanced.output)

    shown = runner.invoke(
        app,
        [
            "round",
            "show",
            round_payload["round_id"],
            "--database",
            str(db_path),
            "--json",
        ],
    )
    assert shown.exit_code == 0, shown.output
    assert json.loads(shown.output)["round_id"] == round_payload["round_id"]

    replayed = runner.invoke(
        app,
        [
            "run",
            "replay",
            round_payload["round_id"],
            "--database",
            str(db_path),
            "--json",
        ],
    )
    assert replayed.exit_code == 0, replayed.output
    replay_payload = json.loads(replayed.output)
    assert replay_payload["matched"] is True


@pytest.mark.integration
def test_cli_unknown_ids_and_invalid_paths_fail_without_traceback(tmp_path: Path) -> None:
    db_path = tmp_path / "errors.sqlite3"
    Database(db_path).setup(package_version="test")

    invalid_path = runner.invoke(
        app,
        [
            "scene",
            "validate",
            str(tmp_path / "missing.yaml"),
            "--database",
            str(db_path),
            "--json",
        ],
    )
    assert invalid_path.exit_code == 2
    assert "error:" in invalid_path.output.lower()
    assert "traceback" not in invalid_path.output.lower()

    unknown = runner.invoke(
        app,
        [
            "run",
            "show",
            "not-a-real-id",
            "--database",
            str(db_path),
            "--json",
        ],
    )
    assert unknown.exit_code == 2
    assert "unknown simulation run or branch" in unknown.output.lower()
    assert "traceback" not in unknown.output.lower()
