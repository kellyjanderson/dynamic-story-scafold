from __future__ import annotations

from pathlib import Path

import pytest

from dynamic_story_scaffold import Simulation, load_scene
from dynamic_story_scaffold.atomic_commit import (
    AtomicRoundCommitError,
    build_atomic_round_candidate,
)
from dynamic_story_scaffold.coordinator import RoundCoordinator
from dynamic_story_scaffold.core import (
    ActorUpdate,
    ComponentRef,
    DisturbanceSet,
    EntityKind,
    EntityRef,
    Position,
    WorldForcing,
)
from dynamic_story_scaffold.intent import UtilityIntentProvider
from dynamic_story_scaffold.perception import BaselinePerceptionProvider
from dynamic_story_scaffold.resolution import RulesActionResolver

EXAMPLE = Path(__file__).parents[1] / "examples" / "hollow_bank.yaml"


def _simulation(seed: int = 211) -> Simulation:
    return Simulation(load_scene(EXAMPLE), seed=seed)


@pytest.mark.unit
def test_same_component_forcing_is_aggregated_before_single_tick() -> None:
    sim = _simulation()
    before = sim.state.to_snapshot()
    component = ComponentRef("terrain", "dam_integrity")

    candidate, tick, plan = build_atomic_round_candidate(
        sim,
        before,
        actor_updates=(),
        disturbances=DisturbanceSet(
            forcing=(
                WorldForcing(component, -0.2),
                WorldForcing(component, -0.15),
            )
        ),
    )

    assert sim.state.to_snapshot().digest() == before.digest()
    assert len(plan.disturbances.forcing) == 1
    assert plan.disturbances.forcing[0].component == component
    assert plan.disturbances.forcing[0].amount == pytest.approx(-0.35)
    assert tick.tick == 1
    assert candidate.tick == 1


@pytest.mark.unit
def test_actor_deltas_aggregate_once_and_health_fatigue_remain_bounded() -> None:
    sim = _simulation()
    before = sim.state.to_snapshot()
    actor = EntityRef(EntityKind.ACTOR, "reedshadow_merrit")

    candidate, _tick, plan = build_atomic_round_candidate(
        sim,
        before,
        actor_updates=(
            ActorUpdate(actor=actor, health_delta=-0.8, fatigue_delta=0.7),
            ActorUpdate(actor=actor, health_delta=-0.8, fatigue_delta=0.7),
        ),
        disturbances=DisturbanceSet(),
    )

    assert len(plan.actor_updates) == 1
    assert plan.actor_updates[0].health_delta == pytest.approx(-1.6)
    assert plan.actor_updates[0].fatigue_delta == pytest.approx(1.4)
    assert candidate.actor(actor).health == 0.0
    assert candidate.actor(actor).fatigue == 1.0


@pytest.mark.unit
def test_incompatible_exclusive_actor_writes_fail_without_canonical_mutation() -> None:
    sim = _simulation()
    before = sim.state.to_snapshot()
    actor = EntityRef(EntityKind.ACTOR, "reedshadow_merrit")

    with pytest.raises(AtomicRoundCommitError, match="destination"):
        build_atomic_round_candidate(
            sim,
            before,
            actor_updates=(
                ActorUpdate(actor=actor, destination=Position(zone="west_log")),
                ActorUpdate(actor=actor, destination=Position(zone="center_pool")),
            ),
            disturbances=DisturbanceSet(),
        )

    assert sim.state.to_snapshot().digest() == before.digest()


@pytest.mark.unit
def test_validation_failure_discards_candidate_and_preserves_old_state() -> None:
    sim = _simulation()
    before = sim.state.to_snapshot()

    with pytest.raises(AtomicRoundCommitError, match="unknown forcing component"):
        build_atomic_round_candidate(
            sim,
            before,
            actor_updates=(),
            disturbances=DisturbanceSet(
                forcing=(
                    WorldForcing(ComponentRef("terrain", "not_a_component"), 1.0),
                )
            ),
        )

    assert sim.state.to_snapshot().digest() == before.digest()


@pytest.mark.unit
def test_shuffled_consequence_order_yields_same_normalized_next_state() -> None:
    first = _simulation(seed=223)
    second = _simulation(seed=223)
    actor = EntityRef(EntityKind.ACTOR, "reedshadow_merrit")
    component = ComponentRef("terrain", "dam_integrity")

    updates = (
        ActorUpdate(actor=actor, health_delta=-0.1, resource_delta={"focus": 1.0}),
        ActorUpdate(actor=actor, fatigue_delta=0.2, resource_delta={"focus": -0.25}),
    )
    forcing = (
        WorldForcing(component, -0.2),
        WorldForcing(component, -0.1),
    )

    candidate_a, _tick_a, _plan_a = build_atomic_round_candidate(
        first,
        first.state.to_snapshot(),
        actor_updates=updates,
        disturbances=DisturbanceSet(forcing=forcing),
    )
    candidate_b, _tick_b, _plan_b = build_atomic_round_candidate(
        second,
        second.state.to_snapshot(),
        actor_updates=tuple(reversed(updates)),
        disturbances=DisturbanceSet(forcing=tuple(reversed(forcing))),
    )

    assert candidate_a.to_snapshot().digest() == candidate_b.to_snapshot().digest()


@pytest.mark.unit
def test_same_input_and_entropy_reproduce_equivalent_normalized_snapshot() -> None:
    first = _simulation(seed=227)
    second = _simulation(seed=227)
    actor = EntityRef(EntityKind.ACTOR, "blackjaw")
    component = ComponentRef("terrain", "dam_integrity")
    updates = (ActorUpdate(actor=actor, fatigue_delta=0.125),)
    disturbances = DisturbanceSet(forcing=(WorldForcing(component, -0.3),))

    candidate_a, _tick_a, _plan_a = build_atomic_round_candidate(
        first,
        first.state.to_snapshot(),
        actor_updates=updates,
        disturbances=disturbances,
    )
    candidate_b, _tick_b, _plan_b = build_atomic_round_candidate(
        second,
        second.state.to_snapshot(),
        actor_updates=updates,
        disturbances=disturbances,
    )

    assert candidate_a.to_snapshot().to_data() == candidate_b.to_snapshot().to_data()


@pytest.mark.integration
def test_full_hollow_bank_round_commits_one_coherent_next_state() -> None:
    sim = _simulation(seed=229)
    before = sim.state.to_snapshot()
    record = RoundCoordinator(
        sim,
        perception_provider=BaselinePerceptionProvider(),
        intent_provider=UtilityIntentProvider(sim.scene),
        resolver=RulesActionResolver(sim.scene),
    ).advance_round()

    assert record.execution is not None
    assert record.execution.committed is True
    assert record.execution.state_before_digest == before.digest()
    assert record.execution.state_after_digest == sim.state.to_snapshot().digest()
    assert record.execution.state_after_digest != record.execution.state_before_digest
    assert len(record.ticks) == 1
    assert sim.state.tick == 1
