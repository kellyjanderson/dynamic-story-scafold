from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from .refs import EntityRef, TargetRef


class EffectStacking(StrEnum):
    REPLACE = "replace"
    STACK = "stack"
    STRONGEST = "strongest"
    REFRESH = "refresh"


@dataclass(frozen=True, slots=True)
class Effect:
    id: str
    kind: str
    source: EntityRef
    target: TargetRef
    magnitude: float = 1.0
    duration_seconds: float | None = None
    stacking: EffectStacking = EffectStacking.REPLACE
    tags: tuple[str, ...] = ()
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("effect id must not be empty")
        if not self.kind:
            raise ValueError("effect kind must not be empty")
        if self.duration_seconds is not None and self.duration_seconds < 0:
            raise ValueError("effect duration must be >= 0")
