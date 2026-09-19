from pathlib import Path

import pytest
import yaml

from dynamic_story_scaffold import load_scene, parse_scene
from dynamic_story_scaffold.schema import SceneDefinitionError


EXAMPLE = Path(__file__).parents[1] / "examples" / "hollow_bank.yaml"


def test_example_scene_loads() -> None:
    scene = load_scene(EXAMPLE)

    assert scene.setting.name == "Hollow Bank First Contact"
    assert set(scene.environment) == {"weather", "water", "terrain", "ecology"}
    assert len(scene.characters) == 6
    assert len(scene.creatures) == 1
    assert scene.characters[0].role == "Reedshadow"
    assert scene.roles["Currentcaller"].abilities[0].kind == "spell"


def test_character_role_must_exist() -> None:
    raw = yaml.safe_load(EXAMPLE.read_text())
    raw["characters"][0]["role"] = "NotARealRole"

    with pytest.raises(SceneDefinitionError, match="unknown role"):
        parse_scene(raw)


def test_continuous_initial_value_must_be_in_bounds() -> None:
    raw = yaml.safe_load(EXAMPLE.read_text())
    raw["environment"]["weather"]["components"]["cloud_cover"]["initial"] = 2.0

    with pytest.raises(SceneDefinitionError, match="outside"):
        parse_scene(raw)


def test_discrete_transition_targets_must_exist() -> None:
    raw = yaml.safe_load(EXAMPLE.read_text())
    transitions = raw["environment"]["terrain"]["components"]["dam_state"]["transitions"]
    transitions["intact"][0]["to"] = "vaporized"

    with pytest.raises(SceneDefinitionError, match="unknown"):
        parse_scene(raw)
