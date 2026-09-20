"""Shared domain primitives used across simulation layers."""

from .effects import Effect, EffectStacking
from .identity import (
    BranchId,
    CheckpointId,
    OperationId,
    RoundId,
    RunContext,
    RunId,
)
from .interfaces import ActionResolver, IntentProvider, PerceptionProvider
from .proposals import ActionProposal, WriteClaim, WriteClass
from .randomness import RandomStreams
from .records import (
    ActionIntent,
    ActionResolution,
    ActorUpdate,
    ComponentChange,
    CoordinatorPhase,
    DisturbanceSet,
    KnowledgeLevel,
    Observation,
    Outcome,
    ProposalAudit,
    ProposalTerminalStatus,
    RoundExecutionMetadata,
    RoundRecord,
    TickRecord,
    WorkBudget,
    WorldEvent,
    WorldForcing,
    WorldSnapshot,
)
from .refs import (
    ComponentRef,
    EntityKind,
    EntityRef,
    StateRef,
    SubresourceKey,
    TargetRef,
)
from .scoring import ScoreBreakdown, ScoredOption, ScoreTerm
from .spatial import Position
from .time import TimeSpan
from .values import NumericRange, UNIT_INTERVAL

__all__ = [
    "ActionIntent",
    "ActionProposal",
    "ActionResolution",
    "ActorUpdate",
    "ActionResolver",
    "BranchId",
    "CheckpointId",
    "ComponentChange",
    "ComponentRef",
    "CoordinatorPhase",
    "DisturbanceSet",
    "Effect",
    "EffectStacking",
    "EntityKind",
    "EntityRef",
    "Observation",
    "NumericRange",
    "IntentProvider",
    "KnowledgeLevel",
    "OperationId",
    "Outcome",
    "PerceptionProvider",
    "Position",
    "ProposalAudit",
    "ProposalTerminalStatus",
    "RandomStreams",
    "RoundExecutionMetadata",
    "RoundId",
    "RoundRecord",
    "RunContext",
    "RunId",
    "ScoreBreakdown",
    "ScoredOption",
    "ScoreTerm",
    "StateRef",
    "SubresourceKey",
    "TargetRef",
    "TimeSpan",
    "UNIT_INTERVAL",
    "TickRecord",
    "WorkBudget",
    "WorldEvent",
    "WorldForcing",
    "WorldSnapshot",
    "WriteClaim",
    "WriteClass",
]
