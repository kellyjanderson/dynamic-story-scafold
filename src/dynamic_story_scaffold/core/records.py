from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from .effects import Effect
from .refs import ComponentRef, EntityRef, TargetRef
from .scoring import ScoreBreakdown
from .spatial import Position
from .time import TimeSpan
from .values import UNIT_INTERVAL


class KnowledgeLevel(StrEnum):
    KNOWN = "known"
    INFERRED = "inferred"
    SUSPECTED = "suspected"
    UNKNOWN = "unknown"


class Outcome(StrEnum):
    CRITICAL_FAILURE = "critical_failure"
    FAILURE = "failure"
    PARTIAL = "partial"
    SUCCESS = "success"
    STRONG_SUCCESS = "strong_success"
    CRITICAL_SUCCESS = "critical_success"


@dataclass(frozen=True, slots=True)
class WorldForcing:
    component: ComponentRef
    amount: float
    source: EntityRef | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class WorldEvent:
    name: str
    source: EntityRef | None = None
    target: TargetRef | None = None
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("event name must not be empty")


@dataclass(frozen=True, slots=True)
class DisturbanceSet:
    """Canonical output from actor/world actions into bounded world dynamics."""

    forcing: tuple[WorldForcing, ...] = ()
    events: tuple[WorldEvent, ...] = ()
    effects: tuple[Effect, ...] = ()

    @classmethod
    def from_legacy(
        cls,
        forcing: Mapping[str, float] | None = None,
        events: tuple[str, ...] | list[str] = (),
    ) -> "DisturbanceSet":
        return cls(
            forcing=tuple(
                WorldForcing(ComponentRef.parse(path), float(amount))
                for path, amount in (forcing or {}).items()
            ),
            events=tuple(WorldEvent(str(name)) for name in events),
        )

    def forcing_by_component(self) -> dict[ComponentRef, float]:
        totals: dict[ComponentRef, float] = {}
        for item in self.forcing:
            totals[item.component] = totals.get(item.component, 0.0) + item.amount
        return totals

    @property
    def event_names(self) -> frozenset[str]:
        return frozenset(event.name for event in self.events)

    def merged(self, *others: "DisturbanceSet") -> "DisturbanceSet":
        all_sets = (self, *others)
        return DisturbanceSet(
            forcing=tuple(item for group in all_sets for item in group.forcing),
            events=tuple(item for group in all_sets for item in group.events),
            effects=tuple(item for group in all_sets for item in group.effects),
        )


@dataclass(frozen=True, slots=True)
class ComponentChange:
    component: ComponentRef
    before: float | str
    after: float | str

    @property
    def path(self) -> str:
        return self.component.path


@dataclass(frozen=True, slots=True)
class Observation:
    observer: EntityRef
    subject: TargetRef
    fact: str
    confidence: float
    value: Any = True
    certainty: KnowledgeLevel = KnowledgeLevel.KNOWN
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        UNIT_INTERVAL.require(self.confidence, name="observation confidence")


@dataclass(frozen=True, slots=True)
class ActionIntent:
    actor: EntityRef
    action: str
    target: TargetRef | None = None
    ability: str | None = None
    desired_outcome: str | None = None
    destination: Position | None = None
    resource_commitment: Mapping[str, float] = field(default_factory=dict)
    risk_tolerance: float = 0.5
    score: ScoreBreakdown | None = None
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.action:
            raise ValueError("intent action must not be empty")
        UNIT_INTERVAL.require(self.risk_tolerance, name="risk tolerance")


@dataclass(frozen=True, slots=True)
class ActorUpdate:
    actor: EntityRef
    health_delta: float = 0.0
    fatigue_delta: float = 0.0
    destination: Position | None = None
    posture: str | None = None
    resource_delta: Mapping[str, float] = field(default_factory=dict)
    inventory_add: tuple[str, ...] = ()
    inventory_remove: tuple[str, ...] = ()
    data: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ActionResolution:
    intent: ActionIntent
    outcome: Outcome
    roll: float | None = None
    total: float | None = None
    difficulty: float | None = None
    disturbances: DisturbanceSet = field(default_factory=DisturbanceSet)
    actor_updates: tuple[ActorUpdate, ...] = ()
    explanation: str | None = None
    span: TimeSpan = field(default_factory=lambda: TimeSpan.instant(0.0))

    @property
    def started_at(self) -> float:
        return self.span.start

    @property
    def ended_at(self) -> float:
        return self.span.end


@dataclass(frozen=True, slots=True)
class TickRecord:
    tick: int
    span: TimeSpan
    changes: tuple[ComponentChange, ...] = ()
    disturbances: DisturbanceSet = field(default_factory=DisturbanceSet)

    @property
    def started_at(self) -> float:
        return self.span.start

    @property
    def ended_at(self) -> float:
        return self.span.end

    @property
    def elapsed_seconds(self) -> float:
        return self.span.end

    @property
    def events(self) -> tuple[str, ...]:
        return tuple(sorted(self.disturbances.event_names))


@dataclass(frozen=True, slots=True)
class RoundRecord:
    round_number: int
    span: TimeSpan
    perceptions: Mapping[str, tuple[Observation, ...]] = field(default_factory=dict)
    intents: tuple[ActionIntent, ...] = ()
    resolutions: tuple[ActionResolution, ...] = ()
    ticks: tuple[TickRecord, ...] = ()
    state_before: Mapping[str, Any] = field(default_factory=dict)
    state_after: Mapping[str, Any] = field(default_factory=dict)

    @property
    def started_at(self) -> float:
        return self.span.start

    @property
    def ended_at(self) -> float:
        return self.span.end
