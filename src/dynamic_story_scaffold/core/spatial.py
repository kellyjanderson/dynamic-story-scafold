from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Position:
    """Spatial value that supports semantic zones now and coordinates later."""

    zone: str | None = None
    x: float | None = None
    y: float | None = None
    z: float | None = None

    def __post_init__(self) -> None:
        coordinate_values = (self.x, self.y, self.z)
        has_any = any(value is not None for value in coordinate_values)
        if has_any and (self.x is None or self.y is None):
            raise ValueError("coordinate positions require at least x and y")
        if self.zone is None and not has_any:
            raise ValueError("position requires a zone or coordinates")

    @property
    def has_coordinates(self) -> bool:
        return self.x is not None and self.y is not None

    def distance_to(self, other: "Position") -> float | None:
        if not self.has_coordinates or not other.has_coordinates:
            return None
        z1 = self.z or 0.0
        z2 = other.z or 0.0
        return math.dist((self.x, self.y, z1), (other.x, other.y, z2))
