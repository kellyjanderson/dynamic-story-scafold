from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from dynamic_story_scaffold import Simulation, load_scene
from dynamic_story_scaffold.core import RandomStreams, RunContext, WorldSnapshot
from dynamic_story_scaffold.schema import SimulationRules
from dynamic_story_scaffold.state import WorldState


EXAMPLE = Path(__file__).parents[1] / "examples" / "hollow_bank.yaml"


def test_explicit_run_seed_overrides_scene_default() -> None:
    scene = load_scene(EXAMPLE)
    scene = replace(
        scene,
        simulation=SimulationRules(
            tick_seconds=scene.simulation.tick_seconds,
            seed=123,
        ),
    )

    sim = Simulation(scene, seed=987)

    assert sim.seed == 987
    assert sim.run_context.root_seed == 987
    assert scene.simulation.seed == 123


def test_scene_default_seed_becomes_run_seed() -> None:
    scene = load_scene(EXAMPLE)
    scene = replace(
        scene,
        simulation=SimulationRules(
            tick_seconds=scene.simulation.tick_seconds,
            seed=321,
        ),
    )

    sim = Simulation(scene)

    assert sim.seed == 321
    assert sim.run_context.root_seed == 321


def test_missing_seed_generates_exposed_replay_seed() -> None:
    scene = load_scene(EXAMPLE)
    scene = replace(
        scene,
        simulation=SimulationRules(
            tick_seconds=scene.simulation.tick_seconds,
            seed=None,
        ),
    )

    sim = Simulation(scene)
    replay = Simulation(scene, seed=sim.run_context.root_seed)

    first_stream = RandomStreams(sim.run_context.root_seed).stream(
        "environment", "continuous", 4, "weather.wind_speed"
    )
    replay_stream = RandomStreams(replay.run_context.root_seed).stream(
        "environment", "continuous", 4, "weather.wind_speed"
    )

    assert isinstance(sim.run_context.root_seed, int)
    assert first_stream.random() == replay_stream.random()


def test_root_lineage_ids_are_stable_for_run() -> None:
    scene = load_scene(EXAMPLE)
    sim = Simulation(scene, seed=7)
    context = sim.run_context

    sim.tick()
    sim.tick()

    assert sim.run_context is context
    assert sim.run_context.run_id == context.run_id
    assert sim.run_context.root_branch_id == context.root_branch_id
    assert sim.run_context.initial_checkpoint_id == context.initial_checkpoint_id
    assert sim.run_context.scene_id == scene.setting.name
    assert sim.run_context.scene_revision == scene.version


def test_snapshot_nested_mutation_cannot_mutate_canonical_state() -> None:
    scene = load_scene(EXAMPLE)
    sim = Simulation(scene, seed=5)
    actor = sim.state.actor("reedshadow_merrit")
    actor.values["nested"] = {"choices": ["hold", "move"]}

    snapshot = sim.state.to_snapshot()
    snapshot.data["actors"]["reedshadow_merrit"]["values"]["nested"]["choices"].append(
        "retreat"
    )

    assert actor.values["nested"]["choices"] == ["hold", "move"]


def test_snapshot_serialization_round_trip_preserves_normalized_state() -> None:
    scene = load_scene(EXAMPLE)
    sim = Simulation(scene, seed=12)
    sim.state.actor("reedshadow_merrit").values["nested"] = {
        "flags": ["alert", "ready"]
    }
    sim.tick()

    snapshot = sim.state.to_snapshot()
    encoded = json.dumps(snapshot.to_data(), sort_keys=True)
    decoded = WorldSnapshot.from_data(json.loads(encoded))
    restored = WorldState.from_snapshot(decoded)

    assert restored.snapshot() == sim.state.snapshot()
    assert decoded.digest() == snapshot.digest()

    restored.actor("reedshadow_merrit").values["nested"]["flags"].append("changed")
    assert sim.state.actor("reedshadow_merrit").values["nested"]["flags"] == [
        "alert",
        "ready",
    ]


def test_run_context_create_exposes_root_identity() -> None:
    context = RunContext.create(
        scene_id="test-scene",
        scene_revision=1,
        scene_seed=44,
    )

    assert context.root_seed == 44
    assert str(context.run_id)
    assert str(context.root_branch_id)
    assert str(context.initial_checkpoint_id)
