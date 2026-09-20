from __future__ import annotations

from pathlib import Path

import pytest

from dynamic_story_scaffold import Simulation, load_scene
from dynamic_story_scaffold.coordinator import RoundCoordinator
from dynamic_story_scaffold.core import (
    ActionIntent,
    ActorUpdate,
    ComponentRef,
    EntityKind,
    EntityRef,
    Outcome,
    RandomStreams,
)
from dynamic_story_scaffold.intent import UtilityIntentProvider
from dynamic_story_scaffold.perception import BaselinePerceptionProvider
from dynamic_story_scaffold.resolution import RulesActionResolver

EXAMPLE = Path(__file__).parents[1] / "examples" / "hollow_bank.yaml"


def _setup():
    scene = load_scene(EXAMPLE)
    sim = Simulation(scene, seed=101)
    resolver = RulesActionResolver(scene)
    return scene, sim, resolver


@pytest.mark.unit
def test_successful_physical_attack_yields_typed_actor_consequence() -> None:
    _scene, sim, resolver = _setup()
    attacker = EntityRef(EntityKind.ACTOR, "shellbreaker_orr")
    target = EntityRef(EntityKind.ACTOR, "blackjaw")
    intent = ActionIntent(
        actor=attacker,
        action="attack",
        ability="Hammerfall",
        target=target,
        data={"difficulty": 0.0},
    )

    resolution = resolver.resolve(
        intent=intent,
        world=sim.state.to_snapshot(),
        rng=RandomStreams(7).stream("resolution", "round-1", attacker.id, "hammerfall"),
    )

    assert resolution.outcome not in {Outcome.FAILURE, Outcome.CRITICAL_FAILURE}
    assert resolution.actor_updates
    assert all(isinstance(update, ActorUpdate) for update in resolution.actor_updates)
    damage = [update for update in resolution.actor_updates if update.actor == target]
    assert damage and damage[0].health_delta < 0.0


@pytest.mark.unit
def test_terrain_impact_yields_forcing_and_event_not_direct_terrain_mutation() -> None:
    _scene, sim, resolver = _setup()
    actor = EntityRef(EntityKind.ACTOR, "shellbreaker_orr")
    terrain = EntityRef(EntityKind.TERRAIN, "spillway")
    before = sim.state.to_snapshot()
    intent = ActionIntent(
        actor=actor,
        action="attack",
        target=terrain,
        data={"difficulty": 0.0},
    )

    resolution = resolver.resolve(
        intent=intent,
        world=before,
        rng=RandomStreams(11).stream("resolution", "round-2", actor.id, "terrain-hit"),
    )

    assert before.digest() == sim.state.to_snapshot().digest()
    assert resolution.disturbances.forcing
    assert resolution.disturbances.forcing[0].component == ComponentRef(
        "terrain", "dam_integrity"
    )
    assert resolution.disturbances.forcing[0].amount < 0.0
    assert {event.name for event in resolution.disturbances.events} == {"terrain_impacted"}
    assert all("terrain" not in update.data for update in resolution.actor_updates)


@pytest.mark.unit
def test_same_entropy_replays_sampled_resolution() -> None:
    _scene, sim, resolver = _setup()
    actor = EntityRef(EntityKind.ACTOR, "shellbreaker_orr")
    target = EntityRef(EntityKind.ACTOR, "blackjaw")
    intent = ActionIntent(actor=actor, action="attack", ability="Hammerfall", target=target)
    snapshot = sim.state.to_snapshot()

    first = resolver.resolve(
        intent=intent,
        world=snapshot,
        rng=RandomStreams(19).stream("resolution", "round-3", actor.id, "intent-1"),
    )
    second = resolver.resolve(
        intent=intent,
        world=snapshot,
        rng=RandomStreams(19).stream("resolution", "round-3", actor.id, "intent-1"),
    )

    assert first == second
    assert first.audit["sample"] == second.audit["sample"]


@pytest.mark.unit
def test_different_seeds_can_change_stochastic_degree_legitimately() -> None:
    _scene, sim, resolver = _setup()
    actor = EntityRef(EntityKind.ACTOR, "shellbreaker_orr")
    target = EntityRef(EntityKind.ACTOR, "blackjaw")
    intent = ActionIntent(
        actor=actor,
        action="attack",
        ability="Hammerfall",
        target=target,
        data={"difficulty": 1.45},
    )
    snapshot = sim.state.to_snapshot()

    results = {
        resolver.resolve(
            intent=intent,
            world=snapshot,
            rng=RandomStreams(seed).stream(
                "resolution", "round-4", actor.id, "intent-variable"
            ),
        ).outcome
        for seed in range(1, 41)
    }

    assert len(results) > 1


@pytest.mark.unit
def test_failed_resolution_has_no_hidden_state_mutation() -> None:
    _scene, sim, resolver = _setup()
    actor = EntityRef(EntityKind.ACTOR, "shellbreaker_orr")
    target = EntityRef(EntityKind.ACTOR, "blackjaw")
    snapshot = sim.state.to_snapshot()
    digest = snapshot.digest()
    intent = ActionIntent(
        actor=actor,
        action="attack",
        ability="Hammerfall",
        target=target,
        data={"difficulty": 5.0},
    )

    resolution = resolver.resolve(
        intent=intent,
        world=snapshot,
        rng=RandomStreams(23).stream("resolution", "round-5", actor.id, "failure"),
    )

    assert resolution.outcome in {Outcome.FAILURE, Outcome.CRITICAL_FAILURE}
    assert resolution.actor_updates == ()
    assert resolution.disturbances.forcing == ()
    assert resolution.disturbances.events == ()
    assert resolution.disturbances.effects == ()
    assert snapshot.digest() == digest
    assert sim.state.to_snapshot().digest() == digest


@pytest.mark.unit
def test_resolution_audit_reconstructs_check_result() -> None:
    _scene, sim, resolver = _setup()
    actor = EntityRef(EntityKind.ACTOR, "currentcaller_nix")
    target = EntityRef(EntityKind.ENVIRONMENT, "world")
    intent = ActionIntent(
        actor=actor,
        action="spell",
        ability="Crosscurrent",
        target=target,
        data={"situational_modifiers": {"stable_footing": 0.1}},
    )

    resolution = resolver.resolve(
        intent=intent,
        world=sim.state.to_snapshot(),
        rng=RandomStreams(29).stream("resolution", "round-6", actor.id, "crosscurrent"),
    )

    audit = resolution.audit
    modifier_total = sum(item["value"] for item in audit["modifiers"])
    reconstructed = (
        audit["sample"] + audit["base_capability"]["value"] + modifier_total
    )
    assert reconstructed == pytest.approx(audit["total"])
    assert audit["total"] - audit["difficulty"] == pytest.approx(audit["margin"])
    assert audit["outcome"] == resolution.outcome.value
    assert resolution.explanation
    assert resolution.roll == audit["sample"]


@pytest.mark.integration
def test_hollow_bank_intents_resolve_to_typed_proposals() -> None:
    scene, sim, resolver = _setup()
    record = RoundCoordinator(
        sim,
        perception_provider=BaselinePerceptionProvider(),
        intent_provider=UtilityIntentProvider(scene),
        resolver=resolver,
    ).advance_round()

    assert len(record.resolutions) == len(scene.actors)
    for resolution in record.resolutions:
        assert resolution.audit["sample"] == resolution.roll
        assert resolution.audit["outcome"] == resolution.outcome.value
        assert all(isinstance(update, ActorUpdate) for update in resolution.actor_updates)
        assert all(
            isinstance(item.component, ComponentRef)
            for item in resolution.disturbances.forcing
        )
