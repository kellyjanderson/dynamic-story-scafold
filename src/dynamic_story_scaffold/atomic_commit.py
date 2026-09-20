from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .core import (
    ActorUpdate,
    ComponentRef,
    DisturbanceSet,
    Effect,
    EntityKind,
    EntityRef,
    WorldEvent,
    WorldForcing,
    WorldSnapshot,
)
from .effect_runtime import apply_effects
from .simulation import Simulation, TickRecord
from .state import WorldState


class AtomicRoundCommitError(ValueError):
    """Raised when accepted round consequences cannot form one coherent state."""


@dataclass(frozen=True, slots=True)
class AtomicRoundPlan:
    actor_updates: tuple[ActorUpdate, ...]
    disturbances: DisturbanceSet


def _finite(value: float, *, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise AtomicRoundCommitError(f"{label} must be finite")
    return result


def _single_value(values: Iterable[Any], *, label: str) -> Any | None:
    found: list[Any] = []
    for value in values:
        if value is None:
            continue
        if not any(value == existing for existing in found):
            found.append(value)
    if len(found) > 1:
        raise AtomicRoundCommitError(f"incompatible exclusive writes for {label}")
    return found[0] if found else None


def _merge_actor_updates(
    actor_id: str,
    updates: tuple[ActorUpdate, ...],
) -> ActorUpdate:
    actor = updates[0].actor
    health_delta = sum(
        _finite(item.health_delta, label=f"{actor_id} health delta") for item in updates
    )
    fatigue_delta = sum(
        _finite(item.fatigue_delta, label=f"{actor_id} fatigue delta") for item in updates
    )

    resources: dict[str, float] = {}
    for update in updates:
        for key, delta in update.resource_delta.items():
            resources[str(key)] = resources.get(str(key), 0.0) + _finite(
                delta, label=f"{actor_id} resource {key!r} delta"
            )

    destination = _single_value(
        (item.destination for item in updates),
        label=f"{actor_id} destination",
    )
    posture = _single_value(
        (item.posture for item in updates),
        label=f"{actor_id} posture",
    )

    data: dict[str, Any] = {}
    for update in updates:
        for key, value in update.data.items():
            key = str(key)
            if key in data and data[key] != value:
                raise AtomicRoundCommitError(
                    f"incompatible exclusive writes for {actor_id} data {key!r}"
                )
            data[key] = value

    additions = sorted(item for update in updates for item in update.inventory_add)
    removals = sorted(item for update in updates for item in update.inventory_remove)
    overlap = set(additions).intersection(removals)
    if overlap:
        raise AtomicRoundCommitError(
            f"incompatible inventory writes for {actor_id}: {sorted(overlap)!r}"
        )

    return ActorUpdate(
        actor=actor,
        health_delta=health_delta,
        fatigue_delta=fatigue_delta,
        destination=destination,
        posture=posture,
        resource_delta={key: resources[key] for key in sorted(resources)},
        inventory_add=tuple(additions),
        inventory_remove=tuple(removals),
        data={key: data[key] for key in sorted(data)},
    )


def _event_key(event: WorldEvent) -> tuple[str, str, str, str]:
    return (
        event.name,
        "" if event.source is None else str(event.source),
        "" if event.target is None else str(event.target),
        "" if event.operation_id is None else str(event.operation_id),
    )


def _effect_key(effect: Effect) -> tuple[str, str, str, str]:
    return (str(effect.target), effect.kind, effect.id, str(effect.source))


def normalize_round_consequences(
    simulation: Simulation,
    before: WorldSnapshot,
    *,
    actor_updates: Iterable[ActorUpdate],
    disturbances: DisturbanceSet,
) -> AtomicRoundPlan:
    """Validate and normalize accepted consequences before candidate mutation."""

    before_data = before.to_data()
    actors = before_data.get("actors", {})
    if not isinstance(actors, Mapping):
        raise AtomicRoundCommitError("snapshot actors must be a mapping")

    grouped: dict[str, list[ActorUpdate]] = {}
    for update in actor_updates:
        if update.actor.kind is not EntityKind.ACTOR:
            raise AtomicRoundCommitError(f"actor update target is not an actor: {update.actor}")
        if update.actor.id not in actors:
            raise AtomicRoundCommitError(f"unknown actor update target: {update.actor}")
        grouped.setdefault(update.actor.id, []).append(update)

    merged_updates = tuple(
        _merge_actor_updates(actor_id, tuple(grouped[actor_id]))
        for actor_id in sorted(grouped)
    )

    forcing_totals: dict[ComponentRef, float] = {}
    for forcing in disturbances.forcing:
        try:
            simulation.scene.component_definition(forcing.component)
        except (KeyError, ValueError) as exc:
            raise AtomicRoundCommitError(
                f"unknown forcing component: {forcing.component}"
            ) from exc
        forcing_totals[forcing.component] = forcing_totals.get(forcing.component, 0.0) + _finite(
            forcing.amount,
            label=f"forcing for {forcing.component}",
        )

    normalized_forcing = tuple(
        WorldForcing(
            component=component,
            amount=forcing_totals[component],
            reason="aggregate round forcing",
        )
        for component in sorted(forcing_totals, key=lambda item: item.path)
    )

    effects = tuple(sorted(disturbances.effects, key=_effect_key))
    for effect in effects:
        if isinstance(effect.target, EntityRef) and effect.target.kind is EntityKind.ACTOR:
            if effect.target.id not in actors:
                raise AtomicRoundCommitError(f"unknown effect target: {effect.target}")
        elif isinstance(effect.target, ComponentRef):
            try:
                simulation.scene.component_definition(effect.target)
            except (KeyError, ValueError) as exc:
                raise AtomicRoundCommitError(f"unknown effect target: {effect.target}") from exc

    return AtomicRoundPlan(
        actor_updates=merged_updates,
        disturbances=DisturbanceSet(
            forcing=normalized_forcing,
            events=tuple(sorted(disturbances.events, key=_event_key)),
            effects=effects,
        ),
    )


def build_atomic_round_candidate(
    simulation: Simulation,
    before: WorldSnapshot,
    *,
    actor_updates: Iterable[ActorUpdate],
    disturbances: DisturbanceSet,
) -> tuple[WorldState, TickRecord, AtomicRoundPlan]:
    """Build and fully validate a detached next state without canonical mutation."""

    plan = normalize_round_consequences(
        simulation,
        before,
        actor_updates=actor_updates,
        disturbances=disturbances,
    )
    candidate = WorldState.from_snapshot(before)

    for update in plan.actor_updates:
        candidate.apply_actor_update(update)

    effects_by_actor: dict[str, list[Effect]] = {}
    for effect in plan.disturbances.effects:
        if (
            isinstance(effect.target, EntityRef)
            and effect.target.kind is EntityKind.ACTOR
        ):
            effects_by_actor.setdefault(effect.target.id, []).append(effect)

    now_seconds = float(before.to_data().get("elapsed_seconds", 0.0))
    for actor_id in sorted(effects_by_actor):
        actor = candidate.actor(actor_id)
        actor.active_effects = list(
            apply_effects(
                actor.active_effects,
                effects_by_actor[actor_id],
                now_seconds=now_seconds,
            )
        )

    candidate_simulation = Simulation(
        simulation.scene,
        state=candidate,
        seed=simulation.seed,
    )
    candidate_simulation.run_context = simulation.run_context
    candidate_simulation.random = simulation.random
    candidate_simulation.rng = simulation.rng
    tick = candidate_simulation.tick(disturbances=plan.disturbances)

    # Force final serialization/validation while the candidate is still detached.
    candidate_simulation.state.to_snapshot()
    return candidate_simulation.state, tick, plan
