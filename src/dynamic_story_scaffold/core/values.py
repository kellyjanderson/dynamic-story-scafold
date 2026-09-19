from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NumericRange:
    minimum: float
    maximum: float

    def __post_init__(self) -> None:
        if self.minimum > self.maximum:
            raise ValueError(
                f"range minimum {self.minimum} exceeds maximum {self.maximum}"
            )

    def contains(self, value: float) -> bool:
        return self.minimum <= value <= self.maximum

    def clamp(self, value: float) -> float:
        return min(self.maximum, max(self.minimum, value))

    def require(self, value: float, *, name: str = "value") -> float:
        if not self.contains(value):
            raise ValueError(
                f"{name}={value} is outside [{self.minimum}, {self.maximum}]"
            )
        return value


UNIT_INTERVAL = NumericRange(0.0, 1.0)
