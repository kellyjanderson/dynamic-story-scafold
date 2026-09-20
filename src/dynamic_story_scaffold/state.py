from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .core.effects import Effect, EffectStacking
from .core.records import ActorUpdate, WorldSnapshot
from .core.refs import ComponentRef, EntityKind, EntityRef, TargetRef
from .core.spatial import Position
from .core.values import UNIT_INTERVAL
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
        UNIT_INTERVAL.require(self.health, name="actor health")
        UNIT_INTERVAL.require(self.fatigue, name="actor fatigue")

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

    @classmethod
    def from_snapshot_data(cls, data: Mapping[str, Any]) -> "ActorState":
        return cls(
            id=str(data["id"]),
            position=_parse_position(data.get("position")),
            posture=_optional_string(data.get("posture")),
            health=float(data.get("health", 1.0)),
            fatigue=float(data.get("fatigue", 0.0)),
            resources=_float_mapping(data.get("resources", {})),
            inventory=_string_list(data.get("inventory", ())),
            active_effects=[
                _effect_from_snapshot(item)
                for item in _mapping_list(data.get("active_effects", ()))
            ],
            relationships=_float_mapping(data.get("relationships", {})),
            values=dict(_mapping(data.get("values", {}))),
        )

    def apply(self, update: ActorUpdate) -> None:
        if update.actor != self.ref:
            raise ValueError(
                f"actor update for {update.actor} cannot be applied to {self.ref}"
            )

        self.health = UNIT_INTERVAL.clamp(self.health + update.health_delta)
        self.fatigue = UNIT_INTERVAL.clamp(self.fatigue + update.fatigue_delta)

        if update.destination is not None:
            self.position = update.destination
        if update.posture is not None:
            self.posture = update.posture

        for resource, delta in update.resource_delta.items():
            self.resources[resource] = self.resources.get(resource, 0.0) + float(delta)

        for item in update.inventory_remove:
            try:
                self.inventory.remove(item)
            except ValueError:
                pass
        self.inventory.extend(update.inventory_add)
        self.values.update(update.data)

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

    @classmethod
    def from_snapshot(cls, snapshot: WorldSnapshot | Mapping[str, Any]) -> "WorldState":
        data = snapshot.to_data() if isinstance(snapshot, WorldSnapshot) else WorldSnapshot(snapshot).to_data()

        environment: dict[str, EnvironmentElementState] = {}
        for element_name, raw_components in _mapping(data.get("environment", {})).items():
            components: dict[str, ComponentState] = {}
            for component_name, raw_component in _mapping(raw_components).items():
                component_data = _mapping(raw_component)
                if "velocity" in component_data:
                    components[str(component_name)] = ContinuousComponentState(
                        value=float(component_data["value"]),
                        velocity=float(component_data.get("velocity", 0.0)),
                    )
                else:
                    components[str(component_name)] = DiscreteComponentState(
                        value=str(component_data["value"])
                    )
            environment[str(element_name)] = EnvironmentElementState(components)

        actors = {
            str(actor_id): ActorState.from_snapshot_data(_mapping(actor_data))
            for actor_id, actor_data in _mapping(data.get("actors", {})).items()
        }

        return cls(
            tick=int(data.get("tick", 0)),
            elapsed_seconds=float(data.get("elapsed_seconds", 0.0)),
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
        if isinstance(reference, EntityRef):
            if reference.kind is not EntityKind.ACTOR:
                raise KeyError(str(reference))
            actor_id = reference.id
        else:
            actor_id = reference
        return self.actors[actor_id]

    def apply_actor_update(self, update: ActorUpdate) -> None:
        self.actor(update.actor).apply(update)

    def to_snapshot(self) -> WorldSnapshot:
        return WorldSnapshot.from_data(self.snapshot())

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


def _effect_from_snapshot(data: Mapping[str, Any]) -> Effect:
    source = _parse_entity_ref(str(data["source"]))
    target = _parse_target_ref(str(data["target"]))
    return Effect(
        id=str(data["id"]),
        kind=str(data["kind"]),
        source=source,
        target=target,
        magnitude=float(data.get("magnitude", 1.0)),
        duration_seconds=(
            None
            if data.get("duration_seconds") is None
            else float(data["duration_seconds"])
        ),
        stacking=EffectStacking(str(data.get("stacking", EffectStacking.REPLACE.value))),
        tags=tuple(str(item) for item in data.get("tags", ())),
        data=dict(_mapping(data.get("data", {}))),
    )


def _parse_entity_ref(value: str) -> EntityRef:
    kind, separator, item_id = value.partition(":")
    if not separator or not kind or not item_id:
        raise ValueError(f"invalid entity reference {value!r}")
    return EntityRef(EntityKind(kind), item_id)


def _parse_target_ref(value: str) -> TargetRef:
    if ":" in value:
        return _parse_entity_ref(value)
    return ComponentRef.parse(value)


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


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("expected mapping")
    return value


def _mapping_list(value: Any) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    return [_mapping(item) for item in value]


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
