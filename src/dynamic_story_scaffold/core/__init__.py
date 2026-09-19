"""Shared domain primitives used across simulation layers."""

from .effects import Effect, EffectStacking
from .interfaces import ActionResolver, IntentProvider, PerceptionProvider
from .randomness import RandomStreams
from .records import (
    ActionIntent,
    ActionResolution,
    ComponentChange,
    DisturbanceSet,
    Observation,
    Outcome,
    RoundRecord,
    TickRecord,
    WorldEvent,
    WorldForcing,
)
from .refs import ComponentRef, EntityKind, EntityRef, TargetRef
from .scoring import ScoreBreakdown, ScoreTerm
from .spatial import Position
from .time import TimeSpan

__all__ = [
    "ActionIntent",
    "ActionResolution",
    "ActionResolver",
    "ComponentChange",
    "ComponentRef",
    "DisturbanceSet",
    "Effect",
    "EffectStacking",
    "EntityKind",
    "EntityRef",
    "Observation",
    "IntentProvider",
    "Outcome",
    "PerceptionProvider",
    "Position",
    "RandomStreams",
    "RoundRecord",
    "ScoreBreakdown",
    "ScoreTerm",
    "TargetRef",
    "TimeSpan",
    "TickRecord",
    "WorldEvent",
    "WorldForcing",
]
