from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

from .schema import (
    AbilityDefinition,
    Bounds,
    CharacterDefinition,
    ContinuousComponentDefinition,
    CreatureDefinition,
    DiscreteComponentDefinition,
    DiscreteTransition,
    DynamicsDefinition,
    EnvironmentElementDefinition,
    RoleDefinition,
    SceneDefinition,
    SceneDefinitionError,
    SceneSetting,
    SimulationRules,
    tuple_of_strings,
)


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SceneDefinitionError(f"{path} must be a mapping")
    return value


def _float_mapping(value: Any, path: str) -> dict[str, float]:
    raw = _mapping(value or {}, path)
    result: dict[str, float] = {}
    for key, item in raw.items():
        try:
            result[str(key)] = float(item)
        except (TypeError, ValueError) as exc:
            raise SceneDefinitionError(f"{path}.{key} must be numeric") from exc
    return result


def _parse_dynamics(raw: Any, path: str) -> DynamicsDefinition:
    data = _mapping(raw, path)
    known = {"method", "max_delta", "jitter", "inertia", "drift"}
    parameters = {str(k): v for k, v in data.items() if k not in known}
    return DynamicsDefinition(
        method=str(data["method"]),
        max_delta=(
            None if data.get("max_delta") is None else float(data["max_delta"])
        ),
        jitter=float(data.get("jitter", 0.0)),
        inertia=float(data.get("inertia", 0.0)),
        drift=float(data.get("drift", 0.0)),
        parameters=parameters,
    )


def _parse_component(name: str, raw: Any, path: str):
    data = _mapping(raw, path)
    kind = str(data.get("kind", "continuous"))

    if kind == "continuous":
        bounds_raw = data.get("bounds")
        if (
            not isinstance(bounds_raw, (list, tuple))
            or len(bounds_raw) != 2
        ):
            raise SceneDefinitionError(
                f"{path}.bounds must be a two-item [min, max] sequence"
            )
        return ContinuousComponentDefinition(
            name=name,
            initial=float(data["initial"]),
            bounds=Bounds(float(bounds_raw[0]), float(bounds_raw[1])),
            dynamics=_parse_dynamics(data["dynamics"], f"{path}.dynamics"),
            units=(None if data.get("units") is None else str(data["units"])),
            description=(
                None if data.get("description") is None else str(data["description"])
            ),
        )

    if kind == "discrete":
        states = tuple_of_strings(data.get("states"))
        transitions_raw = _mapping(data.get("transitions", {}), f"{path}.transitions")
        transitions: dict[str, tuple[DiscreteTransition, ...]] = {}
        for source, items in transitions_raw.items():
            if not isinstance(items, list):
                raise SceneDefinitionError(
                    f"{path}.transitions.{source} must be a list"
                )
            parsed: list[DiscreteTransition] = []
            for index, item in enumerate(items):
                transition = _mapping(
                    item, f"{path}.transitions.{source}[{index}]"
                )
                parsed.append(
                    DiscreteTransition(
                        to=str(transition["to"]),
                        event=(
                            None
                            if transition.get("event") is None
                            else str(transition["event"])
                        ),
                        probability=float(transition.get("probability", 1.0)),
                    )
                )
            transitions[str(source)] = tuple(parsed)

        return DiscreteComponentDefinition(
            name=name,
            initial=str(data["initial"]),
            states=states,
            transitions=transitions,
            description=(
                None if data.get("description") is None else str(data["description"])
            ),
        )

    raise SceneDefinitionError(
        f"{path}.kind must be 'continuous' or 'discrete', got {kind!r}"
    )


def _parse_environment(raw: Any) -> dict[str, EnvironmentElementDefinition]:
    data = _mapping(raw or {}, "environment")
    result: dict[str, EnvironmentElementDefinition] = {}
    for element_name, element_raw in data.items():
        path = f"environment.{element_name}"
        element = _mapping(element_raw, path)
        components_raw = _mapping(element.get("components", {}), f"{path}.components")
        components = {
            str(component_name): _parse_component(
                str(component_name),
                component_raw,
                f"{path}.components.{component_name}",
            )
            for component_name, component_raw in components_raw.items()
        }
        result[str(element_name)] = EnvironmentElementDefinition(
            name=str(element_name),
            components=components,
            description=(
                None
                if element.get("description") is None
                else str(element["description"])
            ),
        )
    return result


def _parse_abilities(raw: Any, path: str) -> tuple[AbilityDefinition, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise SceneDefinitionError(f"{path} must be a list")

    abilities: list[AbilityDefinition] = []
    for index, item in enumerate(raw):
        data = _mapping(item, f"{path}[{index}]")
        abilities.append(
            AbilityDefinition(
                name=str(data["name"]),
                kind=str(data.get("kind", "ability")),
                description=(
                    None if data.get("description") is None else str(data["description"])
                ),
                mechanics=dict(_mapping(data.get("mechanics", {}), f"{path}[{index}].mechanics")),
                modifiers=_float_mapping(
                    data.get("modifiers", {}),
                    f"{path}[{index}].modifiers",
                ),
                visual_semantics=tuple_of_strings(data.get("visual_semantics")),
            )
        )
    return tuple(abilities)


def _parse_roles(raw: Any) -> dict[str, RoleDefinition]:
    data = _mapping(raw or {}, "roles")
    roles: dict[str, RoleDefinition] = {}
    for role_name, role_raw in data.items():
        path = f"roles.{role_name}"
        role = _mapping(role_raw, path)
        roles[str(role_name)] = RoleDefinition(
            name=str(role_name),
            abilities=_parse_abilities(role.get("abilities"), f"{path}.abilities"),
            modifiers=_float_mapping(role.get("modifiers", {}), f"{path}.modifiers"),
            preferred_range=(
                None
                if role.get("preferred_range") is None
                else str(role["preferred_range"])
            ),
            combat_role=(
                None if role.get("combat_role") is None else str(role["combat_role"])
            ),
        )
    return roles


def _parse_characters(raw: Any) -> tuple[CharacterDefinition, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise SceneDefinitionError("characters must be a list")

    characters: list[CharacterDefinition] = []
    for index, item in enumerate(raw):
        path = f"characters[{index}]"
        data = _mapping(item, path)
        characters.append(
            CharacterDefinition(
                id=str(data["id"]),
                name=str(data.get("name", data["id"])),
                species=str(data["species"]),
                role=str(data["role"]),
                physical=_float_mapping(data.get("physical", {}), f"{path}.physical"),
                priorities=tuple_of_strings(data.get("priorities")),
                motivations=_float_mapping(
                    data.get("motivations", {}), f"{path}.motivations"
                ),
                quirks=tuple_of_strings(data.get("quirks")),
                initial_state=dict(
                    _mapping(data.get("initial_state", {}), f"{path}.initial_state")
                ),
            )
        )
    return tuple(characters)


def _parse_creatures(raw: Any) -> tuple[CreatureDefinition, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise SceneDefinitionError("creatures must be a list")

    creatures: list[CreatureDefinition] = []
    for index, item in enumerate(raw):
        path = f"creatures[{index}]"
        data = _mapping(item, path)
        creatures.append(
            CreatureDefinition(
                id=str(data["id"]),
                name=str(data.get("name", data["id"])),
                species=str(data["species"]),
                physical=_float_mapping(data.get("physical", {}), f"{path}.physical"),
                motivations=_float_mapping(
                    data.get("motivations", {}), f"{path}.motivations"
                ),
                behaviors=tuple_of_strings(data.get("behaviors")),
                initial_state=dict(
                    _mapping(data.get("initial_state", {}), f"{path}.initial_state")
                ),
            )
        )
    return tuple(creatures)


def parse_scene(raw: Mapping[str, Any]) -> SceneDefinition:
    data = _mapping(raw, "scene definition")
    setting_raw = _mapping(data["setting"], "setting")
    simulation_raw = _mapping(data.get("simulation", {}), "simulation")

    return SceneDefinition(
        version=int(data.get("version", 1)),
        setting=SceneSetting(
            name=str(setting_raw["name"]),
            biome=(
                None if setting_raw.get("biome") is None else str(setting_raw["biome"])
            ),
            time_of_day=(
                None
                if setting_raw.get("time_of_day") is None
                else str(setting_raw["time_of_day"])
            ),
            season=(
                None
                if setting_raw.get("season") is None
                else str(setting_raw["season"])
            ),
            location_type=(
                None
                if setting_raw.get("location_type") is None
                else str(setting_raw["location_type"])
            ),
            scale=(
                None if setting_raw.get("scale") is None else str(setting_raw["scale"])
            ),
            objectives=tuple_of_strings(setting_raw.get("objectives")),
            tags=tuple_of_strings(setting_raw.get("tags")),
        ),
        environment=_parse_environment(data.get("environment", {})),
        characters=_parse_characters(data.get("characters")),
        roles=_parse_roles(data.get("roles", {})),
        creatures=_parse_creatures(data.get("creatures")),
        simulation=SimulationRules(
            tick_seconds=float(simulation_raw.get("tick_seconds", 1.0)),
            seed=(
                None
                if simulation_raw.get("seed") is None
                else int(simulation_raw["seed"])
            ),
        ),
    )


def load_scene(path: str | Path) -> SceneDefinition:
    scene_path = Path(path)
    with scene_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, Mapping):
        raise SceneDefinitionError("scene YAML root must be a mapping")
    return parse_scene(raw)
