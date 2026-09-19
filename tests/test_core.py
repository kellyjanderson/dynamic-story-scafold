from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from dynamic_story_scaffold import Simulation, load_scene
from dynamic_story_scaffold.core import (
    ActionIntent,
    ActionResolution,
    ActorUpdate,
    ComponentRef,
    DisturbanceSet,
    Effect,
    EffectStacking,
    EntityKind,
    EntityRef,
    Outcome,
    KnowledgeLevel,
    Position,
    RandomStreams,
    ScoreBreakdown,
    ScoredOption,
    ScoreTerm,
    WorldEvent,
    TimeSpan,
    WorldForcing,
)
from dynamic_story_scaffold.schema import SimulationRules
from dynamic_story_scaffold.state import ContinuousComponentState

EXAMPLE = Path(__file__).parents[1] / "examples" / "hollow_bank.yaml"


def test_component_reference_round_trips() -> None:
    reference = ComponentRef.parse("weather.wind_speed")
    assert reference.element == "weather"
    assert reference.component == "wind_speed"
    assert reference.path == "weather.wind_speed"

    with pytest.raises(ValueError):
        ComponentRef.parse("weather")


def test_random_streams_are_semantically_independent() -> None:
    streams = RandomStreams(8128)
    expected = streams.stream("environment", 1, "weather.wind_speed").random()

    # Consuming unrelated streams must not perturb this stream.
    streams.stream("decision", 1, "reedshadow_merrit").random()
    streams.stream("perception", 1, "blackjaw").random()

    actual = streams.stream("environment", 1, "weather.wind_speed").random()
    assert actual == expected


def test_score_breakdown_is_inspectable() -> None:
    score = ScoreBreakdown(
        terms=(
            ScoreTerm("objective", 0.8, 2.0),
            ScoreTerm("risk", -0.4, 0.5),
        ),
        jitter=0.03,
    )

    assert score.contribution("objective") == 1.6
    assert score.deterministic_total == pytest.approx(1.4)
    assert score.total == pytest.approx(1.43)


def test_position_supports_semantic_and_coordinate_modes() -> None:
    assert Position(zone="west_log").distance_to(Position(zone="east_bank")) is None
    assert Position(x=0, y=0).distance_to(Position(x=3, y=4)) == 5.0


def test_disturbances_merge_and_aggregate_forcing() -> None:
    component = ComponentRef.parse("terrain.dam_integrity")
    shellbreaker = EntityRef(EntityKind.ACTOR, "shellbreaker_orr")
    blackjaw = EntityRef(EntityKind.ACTOR, "blackjaw")

    first = DisturbanceSet(
        forcing=(WorldForcing(component, -0.2, shellbreaker, "hammer impact"),),
        events=(WorldEvent("dam_stressed", source=blackjaw),),
    )
    second = DisturbanceSet(
        forcing=(WorldForcing(component, -0.15, blackjaw, "body impact"),),
    )

    merged = first.merged(second)
    assert merged.forcing_by_component()[component] == pytest.approx(-0.35)
    assert merged.event_names == frozenset({"dam_stressed"})


def test_effect_and_action_records_share_common_targeting() -> None:
    actor = EntityRef(EntityKind.ACTOR, "currentcaller_nix")
    target = EntityRef(EntityKind.ACTOR, "blackjaw")
    effect = Effect(
        id="crosscurrent-1",
        kind="stability",
        source=actor,
        target=target,
        magnitude=-0.15,
        duration_seconds=2.0,
        stacking=EffectStacking.STRONGEST,
    )
    intent = ActionIntent(
        actor=actor,
        action="crosscurrent",
        target=target,
        ability="Crosscurrent",
    )
    resolution = ActionResolution(
        intent=intent,
        outcome=Outcome.SUCCESS,
        disturbances=DisturbanceSet(effects=(effect,)),
        span=TimeSpan(0.3, 1.2),
    )

    assert resolution.disturbances.effects[0].target == target


def test_simulation_accepts_shared_disturbances() -> None:
    scene = load_scene(EXAMPLE)
    sim = Simulation(scene, seed=4)
    reference = ComponentRef.parse("terrain.dam_integrity")
    start_state = sim.state.component(reference)
    assert isinstance(start_state, ContinuousComponentState)
    start = start_state.value

    result = sim.tick(
        disturbances=DisturbanceSet(
            forcing=(
                WorldForcing(reference, -0.25),
                WorldForcing(reference, -0.25),
            ),
            events=(WorldEvent("dam_stressed"),),
        )
    )

    after = sim.state.component(reference)
    assert isinstance(after, ContinuousComponentState)
    assert after.value < start
    assert start - after.value <= 0.03 + 1e-12
    assert result.events == ("dam_stressed",)
    assert any(change.component == reference for change in result.changes)


def test_unrelated_random_consumption_does_not_change_environment() -> None:
    scene = load_scene(EXAMPLE)
    baseline = Simulation(scene, seed=91)
    noisy = Simulation(scene, seed=91)

    for tick in range(5):
        noisy.random.stream("decision", tick, "reedshadow_merrit").random()
        noisy.random.stream("perception", tick, "blackjaw").gauss(0, 1)
        baseline.tick()
        noisy.tick()

    assert baseline.state.snapshot()["environment"] == noisy.state.snapshot()["environment"]



def test_actor_update_applies_shared_state_changes() -> None:
    scene = load_scene(EXAMPLE)
    sim = Simulation(scene, seed=5)
    actor = sim.state.actor("reedshadow_merrit")

    actor.health = 0.9
    actor.fatigue = 0.2
    actor.resources["focus"] = 2.0
    actor.inventory.append("bone_knife")

    sim.state.apply_actor_update(
        ActorUpdate(
            actor=actor.ref,
            health_delta=-0.25,
            fatigue_delta=0.95,
            destination=Position(zone="center_pool"),
            posture="swimming",
            resource_delta={"focus": -1.0},
            inventory_remove=("bone_knife",),
            inventory_add=("brass_key",),
            data={"awareness": "engaged"},
        )
    )

    assert actor.health == pytest.approx(0.65)
    assert actor.fatigue == 1.0
    assert actor.position == Position(zone="center_pool")
    assert actor.posture == "swimming"
    assert actor.resources["focus"] == pytest.approx(1.0)
    assert actor.inventory == ["brass_key"]
    assert actor.values["awareness"] == "engaged"


def test_actor_runtime_state_normalizes_common_initial_fields() -> None:
    scene = load_scene(EXAMPLE)
    state = Simulation(scene).state
    merrit = state.actor("reedshadow_merrit")

    assert merrit.position == Position(zone="west_log")
    assert merrit.posture == "crouched"
    assert merrit.values["awareness"] == "alert"



def test_scored_options_share_selection_contract() -> None:
    low = ScoredOption(
        value="hide",
        score=ScoreBreakdown(terms=(ScoreTerm("utility", 0.2),)),
    )
    high = ScoredOption(
        value="intercept",
        score=ScoreBreakdown(terms=(ScoreTerm("utility", 0.9),)),
    )
    assert max((low, high), key=lambda option: option.total).value == "intercept"


def test_observation_uses_shared_knowledge_level() -> None:
    observer = EntityRef(EntityKind.ACTOR, "bubble_augur_pell")
    subject = EntityRef(EntityKind.ACTOR, "blackjaw")
    from dynamic_story_scaffold.core import Observation

    observation = Observation(
        observer=observer,
        subject=subject,
        fact="turning toward the spillway",
        confidence=0.7,
        certainty=KnowledgeLevel.INFERRED,
    )

    assert observation.certainty is KnowledgeLevel.INFERRED


def test_generated_run_seed_can_be_replayed() -> None:
    scene = load_scene(EXAMPLE)
    unseeded_scene = replace(
        scene,
        simulation=SimulationRules(
            tick_seconds=scene.simulation.tick_seconds,
            seed=None,
        ),
    )

    first = Simulation(unseeded_scene)
    replay = Simulation(unseeded_scene, seed=first.seed)

    for _ in range(4):
        first.tick()
        replay.tick()

    assert first.state.snapshot()["environment"] == replay.state.snapshot()["environment"]



def test_unknown_world_forcing_is_rejected() -> None:
    scene = load_scene(EXAMPLE)
    sim = Simulation(scene, seed=3)

    with pytest.raises(KeyError, match="weather.not_a_component"):
        sim.tick(
            disturbances=DisturbanceSet(
                forcing=(
                    WorldForcing(
                        ComponentRef("weather", "not_a_component"),
                        1.0,
                    ),
                ),
            )
        )
