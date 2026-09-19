from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ScoreTerm:
    name: str
    value: float
    weight: float = 1.0

    @property
    def contribution(self) -> float:
        return self.value * self.weight


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    """Inspectable weighted scoring shared by decisions and cinematic ranking."""

    terms: tuple[ScoreTerm, ...] = ()
    jitter: float = 0.0
    metadata: Mapping[str, str] = field(default_factory=dict)

    @property
    def deterministic_total(self) -> float:
        return sum(term.contribution for term in self.terms)

    @property
    def total(self) -> float:
        return self.deterministic_total + self.jitter

    def contribution(self, name: str) -> float:
        return sum(
            term.contribution
            for term in self.terms
            if term.name == name
        )
