from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .core.effects import Effect
from .core.refs import ComponentRef, EntityKind, EntityRef
from .core.spatial import Position
from .schema import (
    ActorDefinition,
    ContinuousComponentDefinition,
    DiscreteComponentDefinition,
    SceneDefinition,
)


@dataclass
class ContinuousComponentState:
    value: float
    velocity: float = 0.0


@dataclass
class DiscreteComponentState:
    value: str


ComponentState = ContinuousComponentState | DiscreteComponentState


@dataclass
class EnvironmentElementState:
    components: dict[str, ComponentState] = field(default_factory=dict)


@dataclass
class ActorState:
    id: str
    position: Position | None = None
    posture: str | None = None
    health: float = 1.0
    fatigue: float = 0.0
    resources: dict[str, float] = field(default_factory=dict)
    inventory: list[str] = field(default_factory=list)
    active_effects: list[Effect] = field(default_factory=list)
    relationships: dict[str, float] = field(default_factory=dict)
    values: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.health <= 1.0:
            raise ValueError("actor health must be between 0 and 1")
        if not 0.0 <= self.fatigue <= 1.0:
            raise ValueError("actor fatigue must be between 0 and 1")

    @property
    def ref(self) -> EntityRef:
        return EntityRef(EntityKind.ACTOR, self.id)

    @classmethod
    def from_definition(cls, definition: ActorDefinition) -> "ActorState":
        initial = dict(definition.initial_state)
        return cls(
            id=definition.id,
            position=_parse_position(initial.pop("position", None)),
            posture=_optional_string(initial.pop("posture", None)),
            health=float(initial.pop("health", 1.0)),
            fatigue=float(initial.pop("fatigue", 0.0)),
            resources=_float_mapping(initial.pop("resources", {})),
            inventory=_string_list(initial.pop("inventory", ())),
            relationships=_float_mapping(initial.pop("relationships", {})),
            values=initial,
        )

    def snapshot(self) -> Mapping[str, Any]:
        position: Mapping[str, Any] | None = None
        if self.position is not None:
            position = {
                "zone": self.position.zone,
                "x": self.position.x,
                "y": self.position.y,
                "z": self.position.z,
            }

        return {
            "id": self.id,
            "position": position,
            "posture": self.posture,
            "health": self.health,
            "fatigue": self.fatigue,
            "resources": dict(self.resources),
            "inventory": list(self.inventory),
            "active_effects": [
                {
                    "id": effect.id,
                    "kind": effect.kind,
                    "source": str(effect.source),
                    "target": str(effect.target),
                    "magnitude": effect.magnitude,
                    "duration_seconds": effect.duration_seconds,
                    "stacking": effect.stacking.value,
                    "tags": list(effect.tags),
                    "data": dict(effect.data),
                }
                for effect in self.active_effects
            ],
            "relationships": dict(self.relationships),
            "values": dict(self.values),
        }


@dataclass
class WorldState:
    tick: int
    elapsed_seconds: float
    environment: dict[str, EnvironmentElementState]
    actors: dict[str, ActorState]

    @classmethod
    def from_scene(cls, scene: SceneDefinition) -> "WorldState":
        environment: dict[str, EnvironmentElementState] = {}
        for element_name, element in scene.environment.items():
            components: dict[str, ComponentState] = {}
            for component_name, definition in element.components.items():
                if isinstance(definition, ContinuousComponentDefinition):
                    components[component_name] = ContinuousComponentState(
                        value=definition.initial
                    )
                elif isinstance(definition, DiscreteComponentDefinition):
                    components[component_name] = DiscreteComponentState(
                        value=definition.initial
                    )
                else:
                    raise TypeError(
                        f"unsupported component definition: {type(definition)!r}"
                    )
            environment[element_name] = EnvironmentElementState(components)

        actors = {
            definition.id: ActorState.from_definition(definition)
            for definition in scene.actors
        }

        return cls(
            tick=0,
            elapsed_seconds=0.0,
            environment=environment,
            actors=actors,
        )

    def component(self, reference: str | ComponentRef) -> ComponentState:
        try:
            component = (
                reference
                if isinstance(reference, ComponentRef)
                else ComponentRef.parse(reference)
            )
        except ValueError as exc:
            raise KeyError(str(exc)) from exc
        return self.environment[component.element].components[component.component]

    def actor(self, reference: str | EntityRef) -> ActorState:
        actor_id = reference.id if isinstance(reference, EntityRef) else reference
        return self.actors[actor_id]

    def snapshot(self) -> Mapping[str, Any]:
        environment: dict[str, dict[str, Any]] = {}
        for element_name, element in self.environment.items():
            values: dict[str, Any] = {}
            for component_name, component in element.components.items():
                if isinstance(component, ContinuousComponentState):
                    values[component_name] = {
                        "value": component.value,
                        "velocity": component.velocity,
                    }
                else:
                    values[component_name] = {"value": component.value}
            environment[element_name] = values

        return {
            "tick": self.tick,
            "elapsed_seconds": self.elapsed_seconds,
            "environment": environment,
            "actors": {
                actor_id: actor.snapshot()
                for actor_id, actor in self.actors.items()
            },
        }


def _parse_position(value: Any) -> Position | None:
    if value is None:
        return None
    if isinstance(value, str):
        return Position(zone=value)
    if isinstance(value, Mapping):
        return Position(
            zone=_optional_string(value.get("zone")),
            x=_optional_float(value.get("x")),
            y=_optional_float(value.get("y")),
            z=_optional_float(value.get("z")),
        )
    raise ValueError(f"unsupported actor position {value!r}")


def _optional_string(value: Any) -> str | None:
    return None if value is None else str(value)


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _float_mapping(value: Any) -> dict[str, float]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("expected mapping")
    return {str(key): float(item) for key, item in value.items()}


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]
