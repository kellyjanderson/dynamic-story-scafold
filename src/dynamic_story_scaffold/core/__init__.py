"""Shared domain primitives used across simulation layers."""

from .effects import Effect, EffectStacking
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

__all__ = [
    "ActionIntent",
    "ActionResolution",
    "ComponentChange",
    "ComponentRef",
    "DisturbanceSet",
    "Effect",
    "EffectStacking",
    "EntityKind",
    "EntityRef",
    "Observation",
    "Outcome",
    "Position",
    "RandomStreams",
    "RoundRecord",
    "ScoreBreakdown",
    "ScoreTerm",
    "TargetRef",
    "TickRecord",
    "WorldEvent",
    "WorldForcing",
]
