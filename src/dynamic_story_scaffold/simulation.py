from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Iterable, Mapping

from .dynamics import evolve_continuous
from .schema import (
    ContinuousComponentDefinition,
    DiscreteComponentDefinition,
    DiscreteTransition,
    SceneDefinition,
)
from .state import (
    ContinuousComponentState,
    DiscreteComponentState,
    WorldState,
)


@dataclass(frozen=True)
class ComponentChange:
    path: str
    before: float | str
    after: float | str


@dataclass(frozen=True)
class TickResult:
    tick: int
    elapsed_seconds: float
    changes: tuple[ComponentChange, ...] = ()
    events: tuple[str, ...] = ()


class Simulation:
    """Stateful, seeded simulator for a loaded scene definition.

    Continuous dynamics are evolved once per tick. External forcing is supplied
    by component path, such as weather.wind_speed. Discrete components change
    only through explicitly declared transitions.
    """

    def __init__(
        self,
        scene: SceneDefinition,
        *,
        state: WorldState | None = None,
        seed: int | None = None,
    ) -> None:
        self.scene = scene
        self.state = state if state is not None else WorldState.from_scene(scene)
        effective_seed = scene.simulation.seed if seed is None else seed
        self.rng = Random(effective_seed)

    def tick(
        self,
        *,
        forcing: Mapping[str, float] | None = None,
        events: Iterable[str] = (),
    ) -> TickResult:
        forcing = forcing or {}
        event_set = frozenset(str(event) for event in events)
        changes: list[ComponentChange] = []

        for element_name, element_definition in self.scene.environment.items():
            element_state = self.state.environment[element_name]
            for component_name, definition in element_definition.components.items():
                path = f"{element_name}.{component_name}"
                state = element_state.components[component_name]

                if isinstance(definition, ContinuousComponentDefinition):
                    if not isinstance(state, ContinuousComponentState):
                        raise TypeError(f"{path} has mismatched runtime state")
                    next_state = evolve_continuous(
                        definition,
                        state,
                        self.rng,
                        forcing=float(forcing.get(path, 0.0)),
                    )
                    if next_state.value != state.value:
                        changes.append(
                            ComponentChange(
                                path=path,
                                before=state.value,
                                after=next_state.value,
                            )
                        )
                    element_state.components[component_name] = next_state
                    continue

                if isinstance(definition, DiscreteComponentDefinition):
                    if not isinstance(state, DiscreteComponentState):
                        raise TypeError(f"{path} has mismatched runtime state")
                    next_value = self._evolve_discrete(
                        definition,
                        state.value,
                        event_set,
                    )
                    if next_value != state.value:
                        changes.append(
                            ComponentChange(
                                path=path,
                                before=state.value,
                                after=next_value,
                            )
                        )
                        state.value = next_value
                    continue

                raise TypeError(f"unsupported component definition at {path}")

        self.state.tick += 1
        self.state.elapsed_seconds += self.scene.simulation.tick_seconds

        return TickResult(
            tick=self.state.tick,
            elapsed_seconds=self.state.elapsed_seconds,
            changes=tuple(changes),
            events=tuple(sorted(event_set)),
        )

    def _evolve_discrete(
        self,
        definition: DiscreteComponentDefinition,
        current: str,
        events: frozenset[str],
    ) -> str:
        candidates = definition.transitions.get(current, ())
        for transition in candidates:
            if not self._transition_is_eligible(transition, events):
                continue
            if self.rng.random() <= transition.probability:
                return transition.to
        return current

    @staticmethod
    def _transition_is_eligible(
        transition: DiscreteTransition,
        events: frozenset[str],
    ) -> bool:
        return transition.event is None or transition.event in events
