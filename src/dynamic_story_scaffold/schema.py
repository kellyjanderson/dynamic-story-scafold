from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Sequence

Scalar = int | float | str | bool
ComponentKind = Literal["continuous", "discrete"]


class SceneDefinitionError(ValueError):
    """Raised when a scene definition is structurally invalid."""


@dataclass(frozen=True)
class Bounds:
    minimum: float
    maximum: float

    def __post_init__(self) -> None:
        if self.minimum > self.maximum:
            raise SceneDefinitionError(
                f"bounds minimum {self.minimum} exceeds maximum {self.maximum}"
            )

    def clamp(self, value: float) -> float:
        return min(self.maximum, max(self.minimum, value))


@dataclass(frozen=True)
class DynamicsDefinition:
    method: str
    max_delta: float | None = None
    jitter: float = 0.0
    inertia: float = 0.0
    drift: float = 0.0
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.method:
            raise SceneDefinitionError("dynamics.method must not be empty")
        if self.max_delta is not None and self.max_delta < 0:
            raise SceneDefinitionError("dynamics.max_delta must be >= 0")
        if self.jitter < 0:
            raise SceneDefinitionError("dynamics.jitter must be >= 0")
        if not 0.0 <= self.inertia <= 1.0:
            raise SceneDefinitionError("dynamics.inertia must be between 0 and 1")


@dataclass(frozen=True)
class ContinuousComponentDefinition:
    name: str
    initial: float
    bounds: Bounds
    dynamics: DynamicsDefinition
    units: str | None = None
    description: str | None = None
    kind: ComponentKind = "continuous"

    def __post_init__(self) -> None:
        if not self.bounds.minimum <= self.initial <= self.bounds.maximum:
            raise SceneDefinitionError(
                f"{self.name}.initial={self.initial} is outside "
                f"[{self.bounds.minimum}, {self.bounds.maximum}]"
            )


@dataclass(frozen=True)
class DiscreteTransition:
    to: str
    event: str | None = None
    probability: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.probability <= 1.0:
            raise SceneDefinitionError("transition probability must be between 0 and 1")


@dataclass(frozen=True)
class DiscreteComponentDefinition:
    name: str
    initial: str
    states: tuple[str, ...]
    transitions: Mapping[str, tuple[DiscreteTransition, ...]] = field(default_factory=dict)
    description: str | None = None
    kind: ComponentKind = "discrete"

    def __post_init__(self) -> None:
        if not self.states:
            raise SceneDefinitionError(f"{self.name}.states must not be empty")
        if self.initial not in self.states:
            raise SceneDefinitionError(
                f"{self.name}.initial={self.initial!r} is not in states"
            )
        known = set(self.states)
        for source, transitions in self.transitions.items():
            if source not in known:
                raise SceneDefinitionError(
                    f"{self.name}.transitions references unknown state {source!r}"
                )
            for transition in transitions:
                if transition.to not in known:
                    raise SceneDefinitionError(
                        f"{self.name}.transition target {transition.to!r} is unknown"
                    )


DynamicComponentDefinition = ContinuousComponentDefinition | DiscreteComponentDefinition


@dataclass(frozen=True)
class EnvironmentElementDefinition:
    name: str
    components: Mapping[str, DynamicComponentDefinition]
    description: str | None = None


@dataclass(frozen=True)
class SceneSetting:
    name: str
    biome: str | None = None
    time_of_day: str | None = None
    season: str | None = None
    location_type: str | None = None
    scale: str | None = None
    objectives: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class CharacterDefinition:
    id: str
    name: str
    species: str
    role: str
    physical: Mapping[str, float] = field(default_factory=dict)
    priorities: tuple[str, ...] = ()
    motivations: Mapping[str, float] = field(default_factory=dict)
    quirks: tuple[str, ...] = ()
    initial_state: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AbilityDefinition:
    name: str
    kind: str
    description: str | None = None
    mechanics: Mapping[str, Any] = field(default_factory=dict)
    modifiers: Mapping[str, float] = field(default_factory=dict)
    visual_semantics: tuple[str, ...] = ()


@dataclass(frozen=True)
class RoleDefinition:
    name: str
    abilities: tuple[AbilityDefinition, ...] = ()
    modifiers: Mapping[str, float] = field(default_factory=dict)
    preferred_range: str | None = None
    combat_role: str | None = None


@dataclass(frozen=True)
class CreatureDefinition:
    id: str
    name: str
    species: str
    physical: Mapping[str, float] = field(default_factory=dict)
    motivations: Mapping[str, float] = field(default_factory=dict)
    behaviors: tuple[str, ...] = ()
    initial_state: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SimulationRules:
    tick_seconds: float = 1.0
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.tick_seconds <= 0:
            raise SceneDefinitionError("simulation.tick_seconds must be > 0")


@dataclass(frozen=True)
class SceneDefinition:
    version: int
    setting: SceneSetting
    environment: Mapping[str, EnvironmentElementDefinition]
    characters: tuple[CharacterDefinition, ...] = ()
    roles: Mapping[str, RoleDefinition] = field(default_factory=dict)
    creatures: tuple[CreatureDefinition, ...] = ()
    simulation: SimulationRules = field(default_factory=SimulationRules)

    def __post_init__(self) -> None:
        if self.version != 1:
            raise SceneDefinitionError(
                f"unsupported scene definition version {self.version}; expected 1"
            )

        role_names = set(self.roles)
        for character in self.characters:
            if character.role not in role_names:
                raise SceneDefinitionError(
                    f"character {character.id!r} references unknown role "
                    f"{character.role!r}"
                )

        ids = [c.id for c in self.characters] + [c.id for c in self.creatures]
        duplicates = {item for item in ids if ids.count(item) > 1}
        if duplicates:
            raise SceneDefinitionError(
                f"actor ids must be unique; duplicates: {sorted(duplicates)}"
            )


def tuple_of_strings(value: Sequence[Any] | None) -> tuple[str, ...]:
    if value is None:
        return ()
    return tuple(str(item) for item in value)
