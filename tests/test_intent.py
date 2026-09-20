from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from dynamic_story_scaffold import Simulation, load_scene
from dynamic_story_scaffold.actions import generate_action_candidates
from dynamic_story_scaffold.coordinator import RoundCoordinator
from dynamic_story_scaffold.core import EntityKind, EntityRef, RandomStreams
from dynamic_story_scaffold.intent import UtilityIntentProvider
from dynamic_story_scaffold.perception import BaselinePerceptionProvider
from dynamic_story_scaffold.schema import (
    AbilityDefinition,
    CharacterDefinition,
    RoleDefinition,
    SceneDefinition,
    SceneSetting,
)

EXAMPLE = Path(__file__).parents[1] / "examples" / "hollow_bank.yaml"


def _decision_scene() -> SceneDefinition:
    role = RoleDefinition(name="Scout")
    cautious = CharacterDefinition(
        id="cautious",
        name="Cautious",
        species="test",
        role="Scout",
        motivations={"self_preservation": 1.0},
        initial_state={"position": "west"},
    )
    curious = CharacterDefinition(
        id="curious",
        name="Curious",
        species="test",
        role="Scout",
        motivations={"understand_unknown_threats": 1.0},
        initial_state={"position": "east"},
    )
    return SceneDefinition(
        version=1,
        setting=SceneSetting(name="Intent test"),
        environment={},
        characters=(cautious, curious),
        roles={"Scout": role},
    )


@pytest.mark.unit
def test_same_role_different_motivations_can_choose_differently() -> None:
    scene = _decision_scene()
    sim = Simulation(scene, seed=11)
    provider = UtilityIntentProvider(scene, decision_jitter=0.0)

    cautious = provider.choose_intent(
        actor=EntityRef(EntityKind.ACTOR, "cautious"),
        world=sim.state.to_snapshot(),
        observations=(),
        rng=RandomStreams(11).stream("intent", "same-role", "cautious"),
    )
    curious = provider.choose_intent(
        actor=EntityRef(EntityKind.ACTOR, "curious"),
        world=sim.state.to_snapshot(),
        observations=(),
        rng=RandomStreams(11).stream("intent", "same-role", "curious"),
    )

    assert cautious.action == "defend"
    assert curious.action == "observe"


@pytest.mark.unit
def test_same_entropy_replays_candidate_scoring_and_selection() -> None:
    scene = _decision_scene()
    sim = Simulation(scene, seed=17)
    provider = UtilityIntentProvider(scene)
    actor = EntityRef(EntityKind.ACTOR, "cautious")

    first = provider.choose_intent(
        actor=actor,
        world=sim.state.to_snapshot(),
        observations=(),
        rng=RandomStreams(97).stream("intent", "round-1", "cautious"),
    )
    second = provider.choose_intent(
        actor=actor,
        world=sim.state.to_snapshot(),
        observations=(),
        rng=RandomStreams(97).stream("intent", "round-1", "cautious"),
    )

    assert first == second
    assert first.data["selection_policy"] == "max_utility"
    assert first.data["candidate_scores"]


@pytest.mark.unit
def test_score_contributions_are_inspectable() -> None:
    scene = _decision_scene()
    sim = Simulation(scene, seed=23)
    intent = UtilityIntentProvider(scene, decision_jitter=0.0).choose_intent(
        actor=EntityRef(EntityKind.ACTOR, "cautious"),
        world=sim.state.to_snapshot(),
        observations=(),
        rng=RandomStreams(23).stream("intent", "inspect", "cautious"),
    )

    assert intent.score is not None
    names = {term.name for term in intent.score.terms}
    assert names == {
        "objective_relevance",
        "motivation_relevance",
        "priority_relevance",
        "role_affinity",
        "positional_suitability",
        "expected_effect",
        "resource_cost",
        "risk",
        "recent_action_repetition",
        "quirk_modifiers",
    }
    audit = intent.data["candidate_scores"]
    assert all(option["terms"] for option in audit)
    assert all("contribution" in term for option in audit for term in option["terms"])


@pytest.mark.unit
def test_impossible_abilities_are_excluded_before_scoring() -> None:
    scene = _decision_scene()
    unavailable = AbilityDefinition(
        name="Expensive Scan",
        kind="spell",
        tags=("information",),
        mechanics={
            "targeting": "none",
            "resource_cost": {"mana": 1.0},
        },
    )
    scene = replace(
        scene,
        roles={"Scout": replace(scene.roles["Scout"], abilities=(unavailable,))},
    )
    sim = Simulation(scene, seed=29)
    candidates = generate_action_candidates(
        scene=scene,
        actor=EntityRef(EntityKind.ACTOR, "cautious"),
        world=sim.state.to_snapshot(),
        observations=(),
    )

    assert all(candidate.ability != "Expensive Scan" for candidate in candidates)


@pytest.mark.unit
def test_intent_generation_cannot_mutate_snapshot_or_canonical_state() -> None:
    scene = _decision_scene()
    sim = Simulation(scene, seed=31)
    snapshot = sim.state.to_snapshot()
    digest = snapshot.digest()
    actor = EntityRef(EntityKind.ACTOR, "cautious")

    UtilityIntentProvider(scene).choose_intent(
        actor=actor,
        world=snapshot,
        observations=(),
        rng=RandomStreams(31).stream("intent", "pure", actor.id),
    )

    assert snapshot.digest() == digest
    assert sim.state.to_snapshot().digest() == digest


@pytest.mark.unit
def test_no_legal_candidate_yields_explicit_no_action() -> None:
    scene = _decision_scene()
    sim = Simulation(scene, seed=37)
    sim.state.actor("cautious").health = 0.0
    actor = EntityRef(EntityKind.ACTOR, "cautious")

    intent = UtilityIntentProvider(scene, decision_jitter=0.0).choose_intent(
        actor=actor,
        world=sim.state.to_snapshot(),
        observations=(),
        rng=RandomStreams(37).stream("intent", "no-action", actor.id),
    )

    assert intent.action == "no_action"
    assert intent.ability is None


@pytest.mark.integration
def test_hollow_bank_actors_all_produce_valid_data_driven_intents() -> None:
    scene = load_scene(EXAMPLE)
    sim = Simulation(scene, seed=41)
    record = RoundCoordinator(
        sim,
        perception_provider=BaselinePerceptionProvider(),
        intent_provider=UtilityIntentProvider(scene),
    ).advance_round()

    assert len(record.intents) == len(scene.actors)
    assert {intent.actor.id for intent in record.intents} == {
        actor.id for actor in scene.actors
    }
    for intent in record.intents:
        assert intent.action
        assert intent.score is not None
        assert intent.data["selection_policy"] == "max_utility"
        assert intent.data["candidate_scores"]
