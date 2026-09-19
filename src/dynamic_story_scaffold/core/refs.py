from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TypeAlias


class EntityKind(StrEnum):
    ACTOR = "actor"
    ENVIRONMENT = "environment"
    TERRAIN = "terrain"
    REGION = "region"
    OBJECT = "object"
    GROUP = "group"


@dataclass(frozen=True, slots=True)
class EntityRef:
    kind: EntityKind
    id: str

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("entity reference id must not be empty")

    def __str__(self) -> str:
        return f"{self.kind.value}:{self.id}"


@dataclass(frozen=True, slots=True)
class ComponentRef:
    element: str
    component: str

    def __post_init__(self) -> None:
        if not self.element or not self.component:
            raise ValueError("component reference parts must not be empty")
        if "." in self.element or "." in self.component:
            raise ValueError("component reference parts must not contain '.'")

    @classmethod
    def parse(cls, value: str) -> "ComponentRef":
        element, separator, component = value.partition(".")
        if not separator or not element or not component or "." in component:
            raise ValueError(
                f"component reference must be '<element>.<component>', got {value!r}"
            )
        return cls(element=element, component=component)

    @property
    def path(self) -> str:
        return f"{self.element}.{self.component}"

    def __str__(self) -> str:
        return self.path


TargetRef: TypeAlias = EntityRef | ComponentRef
