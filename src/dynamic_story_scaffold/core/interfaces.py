from __future__ import annotations

from random import Random
from typing import Protocol, Sequence

from .records import ActionIntent, ActionResolution, Observation
from .refs import EntityRef


class PerceptionProvider(Protocol):
    def perceive(
        self,
        *,
        actor: EntityRef,
        world: object,
        rng: Random,
    ) -> tuple[Observation, ...]: ...


class IntentProvider(Protocol):
    def choose_intent(
        self,
        *,
        actor: EntityRef,
        world: object,
        observations: Sequence[Observation],
        rng: Random,
    ) -> ActionIntent: ...


class ActionResolver(Protocol):
    def resolve(
        self,
        *,
        intent: ActionIntent,
        world: object,
        rng: Random,
    ) -> ActionResolution: ...
