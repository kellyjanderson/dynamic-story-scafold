from __future__ import annotations

from dataclasses import dataclass
from secrets import randbits
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class RunId:
    value: UUID

    @classmethod
    def new(cls) -> "RunId":
        return cls(uuid4())

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class BranchId:
    value: UUID

    @classmethod
    def new(cls) -> "BranchId":
        return cls(uuid4())

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class CheckpointId:
    value: UUID

    @classmethod
    def new(cls) -> "CheckpointId":
        return cls(uuid4())

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class RoundId:
    value: UUID

    @classmethod
    def new(cls) -> "RoundId":
        return cls(uuid4())

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True, order=True)
class OperationId:
    """Stable proposal/event operation identity.

    Callers may use semantic IDs for replay fixtures or generate opaque durable
    UUID identities where no authored semantic identity exists.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("operation id must not be empty")

    @classmethod
    def new(cls) -> "OperationId":
        return cls(str(uuid4()))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class RunContext:
    run_id: RunId
    root_branch_id: BranchId
    root_seed: int
    scene_id: str
    scene_revision: int
    initial_checkpoint_id: CheckpointId

    @classmethod
    def create(
        cls,
        *,
        scene_id: str,
        scene_revision: int,
        scene_seed: int | None = None,
        seed: int | None = None,
    ) -> "RunContext":
        effective_seed = scene_seed if seed is None else seed
        root_seed = randbits(64) if effective_seed is None else int(effective_seed)
        return cls(
            run_id=RunId.new(),
            root_branch_id=BranchId.new(),
            root_seed=root_seed,
            scene_id=str(scene_id),
            scene_revision=int(scene_revision),
            initial_checkpoint_id=CheckpointId.new(),
        )
