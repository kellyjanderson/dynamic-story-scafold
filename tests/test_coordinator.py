from __future__ import annotations

from pathlib import Path

import pytest

from dynamic_story_scaffold import Simulation, load_scene
from dynamic_story_scaffold.coordinator import RoundCoordinator, RoundInProgressError
from dynamic_story_scaffold.core import (
    ActionIntent,
    ActionResolution,
    CoordinatorPhase,
    EntityKind,
    EntityRef,
    Outcome,
    ProposalTerminalStatus,
    WorldSnapshot,
)

EXAMPLE = Path(__file__).parents[1] / "examples" / "hollow_bank.yaml"


@pytest.mark.unit
def test_noop_round_records_canonical_phase_order_and_advances_one_tick() -> None:
    sim = Simulation(load_scene(EXAMPLE), seed=17)
    coordinator = RoundCoordinator(sim)
    before = sim.state.to_snapshot()

    record = coordinator.advance_round()

    assert record.execution is not None
    assert record.execution.phases == RoundCoordinator.PHASE_ORDER
    assert record.execution.committed is True
    assert record.execution.proposals == ()
    assert record.state_before == before.to_data()
    assert sim.state.tick == 1
    assert sim.state.elapsed_seconds == pytest.approx(sim.scene.simulation.tick_seconds)


@pytest.mark.unit
def test_recursive_advance_is_rejected_immediately() -> None:
    sim = Simulation(load_scene(EXAMPLE), seed=19)
    coordinator: RoundCoordinator

    class RecursiveProvider:
        def perceive(self, *, actor, world, rng):
            coordinator.advance_round()
            return ()

    coordinator = RoundCoordinator(sim, perception_provider=RecursiveProvider())

    with pytest.raises(RoundInProgressError, match="already active"):
        coordinator.advance_round()

    assert coordinator.active is False
    assert sim.state.tick == 0


@pytest.mark.unit
def test_provider_exception_before_commit_leaves_canonical_state_unchanged() -> None:
    sim = Simulation(load_scene(EXAMPLE), seed=23)
    before = sim.state.to_snapshot()

    class ExplodingProvider:
        def perceive(self, *, actor, world, rng):
            raise RuntimeError("provider failed")

    coordinator = RoundCoordinator(sim, perception_provider=ExplodingProvider())

    with pytest.raises(RuntimeError, match="provider failed"):
        coordinator.advance_round()

    assert sim.state.to_snapshot().digest() == before.digest()


@pytest.mark.unit
def test_providers_receive_world_snapshot_not_mutable_world_state() -> None:
    sim = Simulation(load_scene(EXAMPLE), seed=29)
    seen = []

    class SnapshotProvider:
        def perceive(self, *, actor, world, rng):
            seen.append(world)
            assert isinstance(world, WorldSnapshot)
            world.data["tick"] = 999
            return ()

    coordinator = RoundCoordinator(sim, perception_provider=SnapshotProvider())
    coordinator.advance_round()

    assert seen
    assert sim.state.tick == 1


@pytest.mark.unit
def test_every_submitted_placeholder_proposal_is_terminal() -> None:
    sim = Simulation(load_scene(EXAMPLE), seed=31)

    class EmptyPerception:
        def perceive(self, *, actor, world, rng):
            return ()

    class Intent:
        def choose_intent(self, *, actor, world, observations, rng):
            return ActionIntent(actor=actor, action="wait")

    class Resolver:
        def resolve(self, *, intent, world, rng):
            return ActionResolution(intent=intent, outcome=Outcome.SUCCESS)

    coordinator = RoundCoordinator(
        sim,
        perception_provider=EmptyPerception(),
        intent_provider=Intent(),
        resolver=Resolver(),
    )
    record = coordinator.advance_round()

    assert record.execution is not None
    assert record.execution.proposals
    assert {
        item.status for item in record.execution.proposals
    } == {ProposalTerminalStatus.ACCEPTED}


@pytest.mark.integration
def test_coordinator_commits_resolved_actor_update_only_after_resolution() -> None:
    sim = Simulation(load_scene(EXAMPLE), seed=37)
    target = sim.state.actor("reedshadow_merrit")
    before_health = target.health

    class EmptyPerception:
        def perceive(self, *, actor, world, rng):
            return ()

    class OneIntent:
        def choose_intent(self, *, actor, world, observations, rng):
            return ActionIntent(actor=actor, action="wait")

    class Resolver:
        def resolve(self, *, intent, world, rng):
            from dynamic_story_scaffold.core import ActorUpdate
            updates = ()
            if intent.actor.id == "reedshadow_merrit":
                updates = (ActorUpdate(actor=intent.actor, health_delta=-0.1),)
            return ActionResolution(
                intent=intent,
                outcome=Outcome.SUCCESS,
                actor_updates=updates,
            )

    record = RoundCoordinator(
        sim,
        perception_provider=EmptyPerception(),
        intent_provider=OneIntent(),
        resolver=Resolver(),
    ).advance_round()

    assert record.execution is not None and record.execution.committed
    assert sim.state.actor("reedshadow_merrit").health == pytest.approx(
        before_health - 0.1
    )


@pytest.mark.unit
def test_resolver_exception_before_commit_leaves_state_unchanged() -> None:
    sim = Simulation(load_scene(EXAMPLE), seed=41)
    before = sim.state.to_snapshot()

    class Intent:
        def choose_intent(self, *, actor, world, observations, rng):
            return ActionIntent(actor=actor, action="wait")

    class Resolver:
        def resolve(self, *, intent, world, rng):
            raise RuntimeError("resolution failed")

    coordinator = RoundCoordinator(sim, intent_provider=Intent(), resolver=Resolver())

    with pytest.raises(RuntimeError, match="resolution failed"):
        coordinator.advance_round()

    assert sim.state.to_snapshot().digest() == before.digest()
