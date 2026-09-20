from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .identity import OperationId
from .records import ActionIntent
from .refs import StateRef


class WriteClass(StrEnum):
    AGGREGATABLE = "aggregatable"
    EXCLUSIVE = "exclusive"
    RULE_GOVERNED = "rule_governed"


@dataclass(frozen=True, slots=True)
class WriteClaim:
    target: StateRef
    write_class: WriteClass
    rule: str | None = None

    def __post_init__(self) -> None:
        if self.write_class is WriteClass.RULE_GOVERNED and not self.rule:
            raise ValueError("rule-governed writes require a rule")


@dataclass(frozen=True, slots=True)
class ActionProposal:
    """Normalized coordinator proposal with explicit dependency/claim metadata."""

    operation_id: OperationId
    intent: ActionIntent
    read_set: frozenset[StateRef] = field(default_factory=frozenset)
    write_set: tuple[WriteClaim, ...] = ()
    exclusive_claims: frozenset[StateRef] = field(default_factory=frozenset)
    dependencies: frozenset[OperationId] = field(default_factory=frozenset)
    causal_parent: OperationId | None = None
    causal_depth: int = 0

    def __post_init__(self) -> None:
        if self.causal_depth < 0:
            raise ValueError("causal depth must be non-negative")

    @property
    def exclusive_targets(self) -> frozenset[StateRef]:
        from_writes = {
            claim.target
            for claim in self.write_set
            if claim.write_class is WriteClass.EXCLUSIVE
        }
        return frozenset((*self.exclusive_claims, *from_writes))
