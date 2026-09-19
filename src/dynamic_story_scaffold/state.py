from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .core.refs import ComponentRef
from .schema import (
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
    values: dict[str, Any] = field(default_factory=dict)


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

        actors: dict[str, ActorState] = {}
        for character in scene.characters:
            actors[character.id] = ActorState(
                id=character.id,
                values=dict(character.initial_state),
            )
        for creature in scene.creatures:
            actors[creature.id] = ActorState(
                id=creature.id,
                values=dict(creature.initial_state),
            )

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
                actor_id: dict(actor.values)
                for actor_id, actor in self.actors.items()
            },
        }
