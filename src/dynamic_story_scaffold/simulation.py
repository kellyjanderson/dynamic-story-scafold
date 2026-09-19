from __future__ import annotations

from typing import Iterable, Mapping

from .core.randomness import RandomStreams
from .core.records import ComponentChange, DisturbanceSet, TickRecord
from .core.refs import ComponentRef
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

TickResult = TickRecord


class Simulation:
    """Stateful, seeded simulator for a loaded scene definition.

    Inputs enter the environment as a DisturbanceSet: bounded continuous forcing,
    explicit events, and effects. Legacy forcing/events arguments remain
    supported and compile into the same shared representation.
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
        self.seed = 0 if effective_seed is None else int(effective_seed)
        self.random = RandomStreams(self.seed)

    def tick(
        self,
        *,
        disturbances: DisturbanceSet | None = None,
        forcing: Mapping[str, float] | None = None,
        events: Iterable[str] = (),
    ) -> TickRecord:
        legacy = DisturbanceSet.from_legacy(
            forcing=forcing,
            events=tuple(str(event) for event in events),
        )
        applied = (disturbances or DisturbanceSet()).merged(legacy)
        forcing_by_component = applied.forcing_by_component()
        event_names = applied.event_names
        changes: list[ComponentChange] = []

        started_at = self.state.elapsed_seconds
        tick_number = self.state.tick + 1

        for element_name, element_definition in self.scene.environment.items():
            element_state = self.state.environment[element_name]
            for component_name, definition in element_definition.components.items():
                reference = ComponentRef(element_name, component_name)
                state = element_state.components[component_name]

                if isinstance(definition, ContinuousComponentDefinition):
                    if not isinstance(state, ContinuousComponentState):
                        raise TypeError(f"{reference.path} has mismatched runtime state")
                    rng = self.random.stream(
                        "environment",
                        "continuous",
                        tick_number,
                        reference.path,
                    )
                    next_state = evolve_continuous(
                        definition,
                        state,
                        rng,
                        forcing=forcing_by_component.get(reference, 0.0),
                    )
                    if next_state.value != state.value:
                        changes.append(
                            ComponentChange(
                                component=reference,
                                before=state.value,
                                after=next_state.value,
                            )
                        )
                    element_state.components[component_name] = next_state
                    continue

                if isinstance(definition, DiscreteComponentDefinition):
                    if not isinstance(state, DiscreteComponentState):
                        raise TypeError(f"{reference.path} has mismatched runtime state")
                    rng = self.random.stream(
                        "environment",
                        "discrete",
                        tick_number,
                        reference.path,
                    )
                    next_value = self._evolve_discrete(
                        definition,
                        state.value,
                        event_names,
                        rng,
                    )
                    if next_value != state.value:
                        changes.append(
                            ComponentChange(
                                component=reference,
                                before=state.value,
                                after=next_value,
                            )
                        )
                        state.value = next_value
                    continue

                raise TypeError(
                    f"unsupported component definition at {reference.path}"
                )

        self.state.tick = tick_number
        self.state.elapsed_seconds += self.scene.simulation.tick_seconds

        return TickRecord(
            tick=tick_number,
            started_at=started_at,
            ended_at=self.state.elapsed_seconds,
            changes=tuple(changes),
            disturbances=applied,
        )

    def _evolve_discrete(
        self,
        definition: DiscreteComponentDefinition,
        current: str,
        events: frozenset[str],
        rng,
    ) -> str:
        candidates = definition.transitions.get(current, ())
        for transition in candidates:
            if not self._transition_is_eligible(transition, events):
                continue
            if rng.random() <= transition.probability:
                return transition.to
        return current

    @staticmethod
    def _transition_is_eligible(
        transition: DiscreteTransition,
        events: frozenset[str],
    ) -> bool:
        return transition.event is None or transition.event in events
