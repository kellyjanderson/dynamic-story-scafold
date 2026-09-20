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


@dataclass(frozen=True, slots=True, order=True)
class SubresourceKey:
    """Structured subresource path used at subsystem boundaries."""

    parts: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.parts:
            raise ValueError("subresource key must contain at least one part")
        for part in self.parts:
            if not part or "." in part:
                raise ValueError(
                    "subresource key parts must be non-empty and must not contain '.'"
                )

    @classmethod
    def of(cls, *parts: str) -> "SubresourceKey":
        return cls(tuple(parts))

    def __str__(self) -> str:
        return "/".join(self.parts)


@dataclass(frozen=True, slots=True)
class StateRef:
    """Typed reference to an entity/component or one of its subresources."""

    target: TargetRef
    subresource: SubresourceKey | None = None

    def sort_key(self) -> tuple[str, str]:
        return (str(self.target), "" if self.subresource is None else str(self.subresource))

    def __str__(self) -> str:
        if self.subresource is None:
            return str(self.target)
        return f"{self.target}/{self.subresource}"
