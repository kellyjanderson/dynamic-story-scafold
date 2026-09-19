from pathlib import Path

from dynamic_story_scaffold import Simulation, load_scene
from dynamic_story_scaffold.state import (
    ContinuousComponentState,
    DiscreteComponentState,
)


EXAMPLE = Path(__file__).parents[1] / "examples" / "hollow_bank.yaml"


def test_seeded_simulations_are_replayable() -> None:
    scene = load_scene(EXAMPLE)
    first = Simulation(scene, seed=42)
    second = Simulation(scene, seed=42)

    first_values = []
    second_values = []
    for _ in range(8):
        first.tick()
        second.tick()
        first_values.append(first.state.snapshot()["environment"])
        second_values.append(second.state.snapshot()["environment"])

    assert first_values == second_values


def test_max_delta_is_never_exceeded_even_with_large_forcing() -> None:
    scene = load_scene(EXAMPLE)
    sim = Simulation(scene, seed=1)

    before = sim.state.component("weather.wind_speed")
    assert isinstance(before, ContinuousComponentState)
    start = before.value

    sim.tick(forcing={"weather.wind_speed": 1000.0})

    after = sim.state.component("weather.wind_speed")
    assert isinstance(after, ContinuousComponentState)
    assert abs(after.value - start) <= 1.25


def test_bounds_are_never_exceeded() -> None:
    scene = load_scene(EXAMPLE)
    sim = Simulation(scene, seed=11)

    for _ in range(200):
        sim.tick(
            forcing={
                "weather.cloud_cover": 100.0,
                "weather.wind_speed": 100.0,
                "water.level": -100.0,
            }
        )

    cloud = sim.state.component("weather.cloud_cover")
    wind = sim.state.component("weather.wind_speed")
    water = sim.state.component("water.level")

    assert isinstance(cloud, ContinuousComponentState)
    assert isinstance(wind, ContinuousComponentState)
    assert isinstance(water, ContinuousComponentState)
    assert 0.0 <= cloud.value <= 1.0
    assert 0.0 <= wind.value <= 35.0
    assert 0.0 <= water.value <= 1.0


def test_discrete_world_change_requires_declared_event() -> None:
    scene = load_scene(EXAMPLE)
    sim = Simulation(scene, seed=7)

    dam = sim.state.component("terrain.dam_state")
    assert isinstance(dam, DiscreteComponentState)
    assert dam.value == "intact"

    sim.tick()
    assert dam.value == "intact"

    sim.tick(events=["dam_stressed"])
    assert dam.value == "strained"

    sim.tick(events=["dam_damaged"])
    assert dam.value == "leaking"


def test_external_forcing_can_represent_actor_or_world_disturbance() -> None:
    scene = load_scene(EXAMPLE)
    sim = Simulation(scene, seed=4)

    before = sim.state.component("terrain.dam_integrity")
    assert isinstance(before, ContinuousComponentState)
    start = before.value

    result = sim.tick(
        forcing={"terrain.dam_integrity": -0.5},
        events=["dam_stressed"],
    )

    after = sim.state.component("terrain.dam_integrity")
    assert isinstance(after, ContinuousComponentState)
    assert after.value < start
    assert start - after.value <= 0.03 + 1e-12
    assert any(change.path == "terrain.dam_state" for change in result.changes)
