"""Shared domain primitives used across simulation layers."""

from .effects import Effect, EffectStacking
from .identity import BranchId, CheckpointId, RoundId, RunContext, RunId
from .interfaces import ActionResolver, IntentProvider, PerceptionProvider
from .randomness import RandomStreams
from .records import (
    ActionIntent,
    ActionResolution,
    ActorUpdate,
    ComponentChange,
    DisturbanceSet,
    KnowledgeLevel,
    Observation,
    Outcome,
    RoundRecord,
    TickRecord,
    WorldEvent,
    WorldForcing,
    WorldSnapshot,
)
from .refs import ComponentRef, EntityKind, EntityRef, TargetRef
from .scoring import ScoreBreakdown, ScoredOption, ScoreTerm
from .spatial import Position
from .time import TimeSpan
from .values import NumericRange, UNIT_INTERVAL

__all__ = [
    "ActionIntent",
    "ActionResolution",
    "ActorUpdate",
    "ActionResolver",
    "BranchId",
    "CheckpointId",
    "ComponentChange",
    "ComponentRef",
    "DisturbanceSet",
    "Effect",
    "EffectStacking",
    "EntityKind",
    "EntityRef",
    "Observation",
    "NumericRange",
    "IntentProvider",
    "KnowledgeLevel",
    "Outcome",
    "PerceptionProvider",
    "Position",
    "RandomStreams",
    "RoundId",
    "RoundRecord",
    "RunContext",
    "RunId",
    "ScoreBreakdown",
    "ScoredOption",
    "ScoreTerm",
    "TargetRef",
    "TimeSpan",
    "UNIT_INTERVAL",
    "TickRecord",
    "WorldEvent",
    "WorldForcing",
    "WorldSnapshot",
]
