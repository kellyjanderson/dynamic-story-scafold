from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TimeSpan:
    start: float
    end: float

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("time span end must not precede start")

    @property
    def duration(self) -> float:
        return self.end - self.start

    @classmethod
    def instant(cls, at: float) -> "TimeSpan":
        return cls(start=at, end=at)
