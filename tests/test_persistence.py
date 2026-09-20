from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import inspect

from dynamic_story_scaffold.core.identity import CheckpointId, RoundId, RunContext
from dynamic_story_scaffold.core.records import WorldSnapshot
from dynamic_story_scaffold.database import Database
from dynamic_story_scaffold.persistence import SimulationPersistence


def _context() -> RunContext:
    return RunContext.create(
        scene_id="test-scene",
        scene_revision=7,
        seed=2**63 + 17,
    )


def _snapshot(tick: int, value: float) -> WorldSnapshot:
    return WorldSnapshot.from_data(
        {
            "tick": tick,
            "elapsed_seconds": float(tick),
            "environment": {
                "river": {
                    "level": {
                        "value": value,
                        "velocity": 0.0,
                    }
                }
            },
            "actors": {},
        }
    )


def _store(tmp_path: Path) -> tuple[SimulationPersistence, RunContext]:
    database = Database(tmp_path / "simulation.sqlite3")
    database.migrate()
    return SimulationPersistence(database), _context()


@pytest.mark.integration
def test_create_run_persists_root_branch_and_checkpoint(tmp_path: Path) -> None:
    store, context = _store(tmp_path)
    initial = _snapshot(0, 0.25)

    created = store.create_run(context, initial)

    assert created.run_id == str(context.run_id)
    assert created.branch_id == str(context.root_branch_id)
    assert created.checkpoint_id == str(context.initial_checkpoint_id)
    assert store.branch_head(created.branch_id) == created.checkpoint_id
    assert store.load_checkpoint(created.checkpoint_id).to_data() == initial.to_data()


@pytest.mark.integration
def test_round_commit_atomically_advances_branch_head(tmp_path: Path) -> None:
    store, context = _store(tmp_path)
    root = store.create_run(context, _snapshot(0, 0.25))
    round_id = str(RoundId.new())
    output_id = str(CheckpointId.new())
    output = _snapshot(1, 0.5)

    persisted = store.commit_round(
        branch_id=root.branch_id,
        round_id=round_id,
        round_number=1,
        input_checkpoint_id=root.checkpoint_id,
        output_checkpoint_id=output_id,
        output_snapshot=output,
        audit={"decision": {"sample": 0.75}},
    )

    assert persisted.round_id == round_id
    assert persisted.input_checkpoint_id == root.checkpoint_id
    assert persisted.output_checkpoint_id == output_id
    assert store.branch_head(root.branch_id) == output_id
    assert store.load_checkpoint(output_id).to_data() == output.to_data()


@pytest.mark.integration
def test_duplicate_round_commit_is_idempotent(tmp_path: Path) -> None:
    store, context = _store(tmp_path)
    root = store.create_run(context, _snapshot(0, 0.25))
    round_id = str(RoundId.new())
    output_id = str(CheckpointId.new())
    output = _snapshot(1, 0.5)

    first = store.commit_round(
        branch_id=root.branch_id,
        round_id=round_id,
        round_number=1,
        input_checkpoint_id=root.checkpoint_id,
        output_checkpoint_id=output_id,
        output_snapshot=output,
        audit={"result": "success"},
    )
    second = store.commit_round(
        branch_id=root.branch_id,
        round_id=round_id,
        round_number=1,
        input_checkpoint_id=root.checkpoint_id,
        output_checkpoint_id=output_id,
        output_snapshot=output,
        audit={"result": "success"},
    )

    assert second == first
    assert store.round_count(root.branch_id) == 1
    assert store.branch_head(root.branch_id) == output_id


@pytest.mark.integration
def test_transaction_failure_does_not_partially_advance_branch(tmp_path: Path) -> None:
    store, context = _store(tmp_path)
    root = store.create_run(context, _snapshot(0, 0.25))
    output_id = str(CheckpointId.new())

    def fail(_session) -> None:
        raise RuntimeError("simulated persistence failure")

    with pytest.raises(RuntimeError, match="simulated persistence failure"):
        store.commit_round(
            branch_id=root.branch_id,
            round_id=str(RoundId.new()),
            round_number=1,
            input_checkpoint_id=root.checkpoint_id,
            output_checkpoint_id=output_id,
            output_snapshot=_snapshot(1, 0.5),
            audit={"result": "would-have-succeeded"},
            before_head_update=fail,
        )

    assert store.branch_head(root.branch_id) == root.checkpoint_id
    assert store.round_count(root.branch_id) == 0
    with pytest.raises(KeyError):
        store.load_checkpoint(output_id)


@pytest.mark.integration
def test_replay_loads_input_checkpoint_and_round_audit(tmp_path: Path) -> None:
    store, context = _store(tmp_path)
    initial = _snapshot(0, 0.25)
    root = store.create_run(context, initial)
    round_id = str(RoundId.new())
    audit = {
        "intent": {"actor": "actor:otter", "action": "defend"},
        "resolution": {"roll": 0.42, "outcome": "success"},
    }

    store.commit_round(
        branch_id=root.branch_id,
        round_id=round_id,
        round_number=1,
        input_checkpoint_id=root.checkpoint_id,
        output_checkpoint_id=str(CheckpointId.new()),
        output_snapshot=_snapshot(1, 0.5),
        audit=audit,
    )

    replay = store.load_replay_input(round_id)

    assert replay.input_snapshot.to_data() == initial.to_data()
    assert replay.round.audit == audit


@pytest.mark.integration
def test_migration_upgrades_fresh_database(tmp_path: Path) -> None:
    database = Database(tmp_path / f"{uuid4()}.sqlite3")
    database.migrate()

    tables = set(inspect(database.engine()).get_table_names())

    assert {
        "simulation_runs",
        "timeline_branches",
        "checkpoints",
        "simulation_rounds",
    } <= tables
    assert database.status().revision == "0003"
