from __future__ import annotations

from pathlib import Path

import pytest

from dynamic_story_scaffold import Simulation, load_scene
from dynamic_story_scaffold.coordinator import RoundCoordinator
from dynamic_story_scaffold.core import (
    EntityKind,
    EntityRef,
    KnowledgeLevel,
    RandomStreams,
    WorldSnapshot,
)
from dynamic_story_scaffold.perception import BaselinePerceptionProvider

EXAMPLE = Path(__file__).parents[1] / "examples" / "hollow_bank.yaml"


def _snapshot() -> WorldSnapshot:
    return WorldSnapshot.from_data(
        {
            "tick": 4,
            "elapsed_seconds": 8.0,
            "environment": {
                "weather": {
                    "wind_speed": {"value": 2.5, "velocity": 0.75},
                },
                "terrain": {
                    "dam_state": {"value": "intact"},
                },
            },
            "actors": {
                "alpha": {
                    "id": "alpha",
                    "position": {"zone": "west", "x": None, "y": None, "z": None},
                    "posture": "ready",
                    "health": 1.0,
                    "fatigue": 0.1,
                    "resources": {"secret_charge": 9.0},
                    "inventory": ["private_key"],
                    "active_effects": [],
                    "relationships": {"beta": -1.0},
                    "values": {"secret_plan": "ambush"},
                },
                "beta": {
                    "id": "beta",
                    "position": {"zone": "center", "x": None, "y": None, "z": None},
                    "posture": "crouched",
                    "health": 0.62,
                    "fatigue": 0.4,
                    "resources": {"mana": 0.8},
                    "inventory": ["hidden_map"],
                    "active_effects": [],
                    "relationships": {"alpha": 0.2},
                    "values": {"secret_plan": "retreat"},
                },
                "gamma": {
                    "id": "gamma",
                    "position": {"zone": "east", "x": None, "y": None, "z": None},
                    "posture": "prone",
                    "health": 0.2,
                    "fatigue": 0.7,
                    "resources": {},
                    "inventory": [],
                    "active_effects": [],
                    "relationships": {},
                    "values": {"secret_plan": "hide"},
                },
            },
            "recent_events": [
                {"name": "branch_snap", "audible": True},
                {"name": "private_trigger", "audible": False, "explicit": False},
            ],
        }
    )


def _perceive(
    provider: BaselinePerceptionProvider,
    observer_id: str,
    *,
    seed: int = 17,
):
    streams = RandomStreams(seed)
    observer = EntityRef(EntityKind.ACTOR, observer_id)
    return provider.perceive(
        actor=observer,
        world=_snapshot(),
        rng=streams.stream("perception", "round-4", observer_id),
    )


@pytest.mark.unit
def test_two_actors_receive_different_observations_from_same_snapshot() -> None:
    provider = BaselinePerceptionProvider(
        zone_adjacency={"west": {"center"}, "center": {"east"}}
    )

    alpha = _perceive(provider, "alpha")
    gamma = _perceive(provider, "gamma")

    alpha_subjects = {str(item.subject) for item in alpha if item.fact == "actor.presence"}
    gamma_subjects = {str(item.subject) for item in gamma if item.fact == "actor.presence"}

    assert alpha_subjects == {"actor:beta"}
    assert gamma_subjects == {"actor:beta"}
    assert alpha != gamma
    assert any(item.fact == "self.posture" and item.value == "ready" for item in alpha)
    assert any(item.fact == "self.posture" and item.value == "prone" for item in gamma)


@pytest.mark.unit
def test_hidden_or_unavailable_actor_truth_does_not_leak() -> None:
    provider = BaselinePerceptionProvider(zone_adjacency={"west": {"center"}})
    observations = _perceive(provider, "alpha")

    beta = [item for item in observations if str(item.subject) == "actor:beta"]
    facts = {item.fact for item in beta}

    assert facts == {"actor.presence", "actor.posture", "actor.injury"}
    assert not any(item.value == 0.62 for item in beta)
    serialized = repr(tuple(item.value for item in beta))
    assert "mana" not in serialized
    assert "hidden_map" not in serialized
    assert "secret_plan" not in serialized
    assert "relationships" not in serialized

    assert not any(str(item.subject) == "actor:gamma" for item in observations)

    environment = [item for item in observations if item.fact == "environment.value"]
    assert environment
    assert all("velocity" not in item.value for item in environment)


@pytest.mark.unit
def test_same_entropy_replays_perception_uncertainty() -> None:
    provider = BaselinePerceptionProvider(zone_adjacency={"west": {"center"}})

    first = _perceive(provider, "alpha", seed=101)
    second = _perceive(provider, "alpha", seed=101)

    assert first == second
    uncertain = [
        item
        for item in first
        if str(item.subject) == "actor:beta" and item.fact == "actor.presence"
    ]
    assert len(uncertain) == 1
    assert uncertain[0].certainty in {
        KnowledgeLevel.SUSPECTED,
        KnowledgeLevel.INFERRED,
        KnowledgeLevel.KNOWN,
    }


@pytest.mark.unit
def test_unrelated_rng_stream_consumption_does_not_change_perception() -> None:
    provider = BaselinePerceptionProvider(zone_adjacency={"west": {"center"}})
    streams = RandomStreams(31337)
    actor = EntityRef(EntityKind.ACTOR, "alpha")

    before = provider.perceive(
        actor=actor,
        world=_snapshot(),
        rng=streams.stream("perception", "round-4", "alpha"),
    )

    unrelated = streams.stream("intent", "round-4", "alpha")
    for _ in range(100):
        unrelated.random()

    after = provider.perceive(
        actor=actor,
        world=_snapshot(),
        rng=streams.stream("perception", "round-4", "alpha"),
    )

    assert before == after


@pytest.mark.unit
def test_provider_is_pure_with_respect_to_snapshot_and_canonical_state() -> None:
    scene = load_scene(EXAMPLE)
    sim = Simulation(scene, seed=29)
    before = sim.state.to_snapshot()
    before_digest = before.digest()
    actor_id = scene.actors[0].id

    BaselinePerceptionProvider().perceive(
        actor=EntityRef(EntityKind.ACTOR, actor_id),
        world=before,
        rng=sim.random.stream("perception", "round-pure", actor_id),
    )

    assert before.digest() == before_digest
    assert sim.state.to_snapshot().digest() == before_digest


@pytest.mark.unit
def test_recent_events_include_only_audible_or_explicit_events() -> None:
    observations = _perceive(BaselinePerceptionProvider(), "alpha")
    events = [item.value for item in observations if item.fact == "event.recent"]

    assert events == [
        {"name": "branch_snap", "audible": True, "explicit": False},
    ]


@pytest.mark.integration
def test_every_hollow_bank_actor_receives_valid_observation_tuple() -> None:
    sim = Simulation(load_scene(EXAMPLE), seed=41)
    provider = BaselinePerceptionProvider()
    record = RoundCoordinator(sim, perception_provider=provider).advance_round()

    expected_ids = {actor.id for actor in sim.scene.actors}
    assert set(record.perceptions) == expected_ids

    for actor_id, observations in record.perceptions.items():
        assert isinstance(observations, tuple)
        assert observations
        observer = EntityRef(EntityKind.ACTOR, actor_id)
        assert all(item.observer == observer for item in observations)
        assert any(
            item.subject == observer and item.fact == "self.position"
            for item in observations
        )
