from __future__ import annotations

from random import Random
from typing import TYPE_CHECKING, Protocol, Sequence

from .records import ActionIntent, ActionResolution, Observation
from .refs import EntityRef

if TYPE_CHECKING:
    from dynamic_story_scaffold.state import WorldState


class PerceptionProvider(Protocol):
    def perceive(
        self,
        *,
        actor: EntityRef,
        world: "WorldState",
        rng: Random,
    ) -> tuple[Observation, ...]: ...


class IntentProvider(Protocol):
    def choose_intent(
        self,
        *,
        actor: EntityRef,
        world: "WorldState",
        observations: Sequence[Observation],
        rng: Random,
    ) -> ActionIntent: ...


class ActionResolver(Protocol):
    def resolve(
        self,
        *,
        intent: ActionIntent,
        world: "WorldState",
        rng: Random,
    ) -> ActionResolution: ...
