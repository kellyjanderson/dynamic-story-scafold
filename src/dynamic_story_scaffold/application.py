from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID

import yaml

from .coordinator import RoundCoordinator
from .core.identity import CheckpointId, RoundId
from .core.records import RoundRecord, WorldSnapshot
from .database import Database
from .intent import UtilityIntentProvider
from .loader import load_scene, parse_scene
from .perception import BaselinePerceptionProvider
from .persistence import (
    PersistenceConflict,
    SimulationPersistence,
    StoredRound,
    StoredRunContext,
)
from .resolution import RulesActionResolver
from .simulation import Simulation
from .state import WorldState


class ReplayMismatch(RuntimeError):
    """Raised when a stored round no longer reproduces its persisted output."""


class SimulationApplication:
    """Application service boundary for persisted simulation and replay."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self.database.require_current_schema()
        self.persistence = SimulationPersistence(database)

    def validate_scene(self, path: str | Path) -> dict[str, Any]:
        scene_path = Path(path)
        scene = load_scene(scene_path)
        return {
            "valid": True,
            "path": str(scene_path),
            "scene_id": scene.setting.name,
            "scene_revision": scene.version,
            "actors": len(scene.actors),
            "environment_elements": len(scene.environment),
        }

    def start_run(self, path: str | Path, *, seed: int | None = None) -> dict[str, Any]:
        scene_path = Path(path)
        raw = yaml.safe_load(scene_path.read_text(encoding="utf-8"))
        if not isinstance(raw, Mapping):
            raise ValueError("scene YAML root must be a mapping")
        scene = parse_scene(raw)
        simulation = Simulation(scene, seed=seed)
        stored = self.persistence.create_run(
            simulation.run_context,
            simulation.initial_snapshot,
            scene_data=raw,
        )
        return {
            "run_id": stored.run_id,
            "branch_id": stored.branch_id,
            "checkpoint_id": stored.checkpoint_id,
            "root_seed": simulation.run_context.root_seed,
            "branch_entropy_salt": None,
            "scene_id": simulation.run_context.scene_id,
            "scene_revision": simulation.run_context.scene_revision,
        }

    def show_run(self, run_or_branch_id: str) -> dict[str, Any]:
        context = self.persistence.load_run_context(run_or_branch_id)
        return self._context_payload(context)

    def advance_run(self, run_or_branch_id: str) -> dict[str, Any]:
        context = self.persistence.load_run_context(run_or_branch_id)
        scene = parse_scene(context.scene_data)
        before = self.persistence.load_checkpoint(context.checkpoint_id)
        simulation = Simulation(
            scene,
            state=WorldState.from_snapshot(before),
            seed=context.root_seed,
        )
        coordinator = self._coordinator(simulation, scene)
        record = coordinator.advance_round()
        if record.execution is None:
            raise RuntimeError("round completed without execution metadata")

        output_checkpoint_id = str(CheckpointId.new())
        round_id = str(record.execution.round_id)
        payload = self._round_payload(
            record,
            context=context,
            input_checkpoint_id=context.checkpoint_id,
            output_checkpoint_id=output_checkpoint_id,
        )
        stored = self.persistence.commit_round(
            branch_id=context.branch_id,
            round_id=round_id,
            round_number=record.round_number,
            input_checkpoint_id=context.checkpoint_id,
            output_checkpoint_id=output_checkpoint_id,
            output_snapshot=WorldSnapshot.from_data(record.state_after),
            audit={"round": payload},
        )
        return self._stored_round_payload(stored)

    def show_round(self, round_id: str) -> dict[str, Any]:
        stored = self.persistence.load_round(round_id)
        payload = stored.audit.get("round")
        if not isinstance(payload, Mapping):
            return self._stored_round_payload(stored)
        return dict(payload)

    def replay_round(self, round_id: str) -> dict[str, Any]:
        replay = self.persistence.load_replay_input(round_id)
        try:
            replay_id = RoundId(UUID(round_id))
        except ValueError as exc:
            raise ValueError(f"malformed round id {round_id!r}") from exc

        scene = parse_scene(replay.context.scene_data)
        simulation = Simulation(
            scene,
            state=WorldState.from_snapshot(replay.input_snapshot),
            seed=replay.context.root_seed,
        )
        record = self._coordinator(simulation, scene).advance_round(round_id=replay_id)
        replay_payload = self._round_payload(
            record,
            context=replay.context,
            input_checkpoint_id=replay.round.input_checkpoint_id,
            output_checkpoint_id=replay.round.output_checkpoint_id,
        )
        stored_output = self.persistence.load_checkpoint(
            replay.round.output_checkpoint_id
        )
        replay_output = WorldSnapshot.from_data(record.state_after)
        output_match = replay_output.digest() == stored_output.digest()
        stored_payload = replay.round.audit.get("round")
        audit_match = isinstance(stored_payload, Mapping) and dict(stored_payload) == replay_payload
        result = {
            "round_id": round_id,
            "run_id": replay.context.run_id,
            "branch_id": replay.context.branch_id,
            "root_seed": replay.context.root_seed,
            "branch_entropy_salt": replay.context.entropy_salt,
            "input_checkpoint_id": replay.round.input_checkpoint_id,
            "output_checkpoint_id": replay.round.output_checkpoint_id,
            "stored_output_digest": stored_output.digest(),
            "replayed_output_digest": replay_output.digest(),
            "output_match": output_match,
            "audit_match": audit_match,
            "matched": output_match and audit_match,
        }
        if not result["matched"]:
            raise ReplayMismatch(
                "replayed round does not match stored output/audit: "
                f"output_match={output_match}, audit_match={audit_match}"
            )
        return result

    @staticmethod
    def _coordinator(simulation: Simulation, scene) -> RoundCoordinator:
        return RoundCoordinator(
            simulation,
            perception_provider=BaselinePerceptionProvider(),
            intent_provider=UtilityIntentProvider(scene),
            resolver=RulesActionResolver(scene),
        )

    @staticmethod
    def _context_payload(context: StoredRunContext) -> dict[str, Any]:
        return {
            "run_id": context.run_id,
            "branch_id": context.branch_id,
            "checkpoint_id": context.checkpoint_id,
            "root_seed": context.root_seed,
            "branch_entropy_salt": context.entropy_salt,
            "scene_id": context.scene_id,
            "scene_revision": context.scene_revision,
        }

    @staticmethod
    def _stored_round_payload(stored: StoredRound) -> dict[str, Any]:
        payload = stored.audit.get("round")
        if isinstance(payload, Mapping):
            return dict(payload)
        return {
            "round_id": stored.round_id,
            "branch_id": stored.branch_id,
            "round_number": stored.round_number,
            "input_checkpoint_id": stored.input_checkpoint_id,
            "output_checkpoint_id": stored.output_checkpoint_id,
            "audit": dict(stored.audit),
        }

    def _round_payload(
        self,
        record: RoundRecord,
        *,
        context: StoredRunContext,
        input_checkpoint_id: str,
        output_checkpoint_id: str,
    ) -> dict[str, Any]:
        if record.execution is None:
            raise RuntimeError("round has no execution metadata")
        return {
            "round_id": str(record.execution.round_id),
            "round_number": record.round_number,
            "run_id": context.run_id,
            "branch_id": context.branch_id,
            "input_checkpoint_id": input_checkpoint_id,
            "output_checkpoint_id": output_checkpoint_id,
            "entropy": {
                "root_seed": context.root_seed,
                "branch_salt": context.entropy_salt,
            },
            "scene": {
                "id": context.scene_id,
                "revision": context.scene_revision,
            },
            "perceptions": _jsonable(record.perceptions),
            "intents": _jsonable(record.intents),
            "resolutions": _jsonable(record.resolutions),
            "execution": _jsonable(record.execution),
            "state_diff": _state_diff(record.state_before, record.state_after),
            "state_before_digest": WorldSnapshot.from_data(record.state_before).digest(),
            "state_after_digest": WorldSnapshot.from_data(record.state_after).digest(),
        }


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {
            field.name: _jsonable(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_jsonable(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    return value


def _state_diff(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[dict[str, Any]]:
    before_flat = _flatten(before)
    after_flat = _flatten(after)
    changes: list[dict[str, Any]] = []
    for path in sorted(set(before_flat) | set(after_flat)):
        old = before_flat.get(path)
        new = after_flat.get(path)
        if old != new:
            changes.append({"path": path, "before": old, "after": new})
    return changes


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key in sorted(value, key=str):
            child = f"{prefix}.{key}" if prefix else str(key)
            result.update(_flatten(value[key], child))
        return result
    if isinstance(value, (list, tuple)):
        result: dict[str, Any] = {}
        for index, item in enumerate(value):
            child = f"{prefix}[{index}]"
            result.update(_flatten(item, child))
        return result
    return {prefix: _jsonable(value)}
