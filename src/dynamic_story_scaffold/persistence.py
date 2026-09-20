from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Mapping

from sqlalchemy import ForeignKey, JSON, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .core.identity import RunContext
from .core.records import WorldSnapshot
from .database import Base, Database, utc_now


class SimulationRunModel(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    root_seed: Mapped[str] = mapped_column(String(20))
    scene_id: Mapped[str] = mapped_column(String(255))
    scene_revision: Mapped[int]
    scene_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime]


class TimelineBranchModel(Base):
    __tablename__ = "timeline_branches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        index=True,
    )
    parent_branch_id: Mapped[str | None] = mapped_column(
        ForeignKey("timeline_branches.id"),
        nullable=True,
    )
    parent_checkpoint_id: Mapped[str | None] = mapped_column(
        ForeignKey("checkpoints.id"),
        nullable=True,
    )
    active_head_checkpoint_id: Mapped[str | None] = mapped_column(
        ForeignKey("checkpoints.id"),
        nullable=True,
    )
    entropy_salt: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime]


class CheckpointModel(Base):
    __tablename__ = "checkpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    branch_id: Mapped[str] = mapped_column(
        ForeignKey("timeline_branches.id", ondelete="CASCADE"),
        index=True,
    )
    previous_checkpoint_id: Mapped[str | None] = mapped_column(
        ForeignKey("checkpoints.id"),
        nullable=True,
    )
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    snapshot_digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime]


class SimulationRoundModel(Base):
    __tablename__ = "simulation_rounds"
    __table_args__ = (
        UniqueConstraint(
            "branch_id",
            "round_number",
            name="uq_simulation_round_branch_number",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    branch_id: Mapped[str] = mapped_column(
        ForeignKey("timeline_branches.id", ondelete="CASCADE"),
        index=True,
    )
    round_number: Mapped[int]
    input_checkpoint_id: Mapped[str] = mapped_column(
        ForeignKey("checkpoints.id")
    )
    output_checkpoint_id: Mapped[str] = mapped_column(
        ForeignKey("checkpoints.id"),
        unique=True,
    )
    audit: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime]


@dataclass(frozen=True, slots=True)
class StoredRun:
    run_id: str
    branch_id: str
    checkpoint_id: str


@dataclass(frozen=True, slots=True)
class StoredRunContext:
    run_id: str
    branch_id: str
    checkpoint_id: str
    root_seed: int
    scene_id: str
    scene_revision: int
    scene_data: Mapping[str, Any]
    entropy_salt: str | None


@dataclass(frozen=True, slots=True)
class StoredRound:
    round_id: str
    branch_id: str
    round_number: int
    input_checkpoint_id: str
    output_checkpoint_id: str
    audit: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ReplayInput:
    round: StoredRound
    input_snapshot: WorldSnapshot
    context: StoredRunContext


class PersistenceConflict(RuntimeError):
    pass


class SimulationPersistence:
    """Durable simulation history repository.

    Simulation/provider work is intentionally absent from this service. Callers
    compute a completed round first, then persist the resulting checkpoint and
    audit in one short transaction.
    """

    def __init__(self, database: Database) -> None:
        self.database = database

    def create_run(
        self,
        context: RunContext,
        initial_snapshot: WorldSnapshot,
        *,
        scene_data: Mapping[str, Any] | None = None,
    ) -> StoredRun:
        run_id = str(context.run_id)
        branch_id = str(context.root_branch_id)
        checkpoint_id = str(context.initial_checkpoint_id)

        with self.database.session() as session:
            existing = session.get(SimulationRunModel, run_id)
            if existing is not None:
                branch = session.get(TimelineBranchModel, branch_id)
                checkpoint = session.get(CheckpointModel, checkpoint_id)
                if branch is None or checkpoint is None:
                    raise PersistenceConflict(
                        "run identity exists without its declared root lineage"
                    )
                return StoredRun(run_id, branch_id, checkpoint_id)

            session.add(
                SimulationRunModel(
                    id=run_id,
                    root_seed=str(context.root_seed),
                    scene_id=context.scene_id,
                    scene_revision=context.scene_revision,
                    scene_data=None if scene_data is None else dict(scene_data),
                    created_at=utc_now(),
                )
            )
            branch = TimelineBranchModel(
                id=branch_id,
                run_id=run_id,
                parent_branch_id=None,
                parent_checkpoint_id=None,
                active_head_checkpoint_id=None,
                entropy_salt=None,
                created_at=utc_now(),
            )
            session.add(branch)
            session.flush()

            checkpoint = CheckpointModel(
                id=checkpoint_id,
                branch_id=branch_id,
                previous_checkpoint_id=None,
                snapshot=initial_snapshot.to_data(),
                snapshot_digest=initial_snapshot.digest(),
                created_at=utc_now(),
            )
            session.add(checkpoint)
            session.flush()
            branch.active_head_checkpoint_id = checkpoint_id

        return StoredRun(run_id, branch_id, checkpoint_id)

    def commit_round(
        self,
        *,
        branch_id: str,
        round_id: str,
        round_number: int,
        input_checkpoint_id: str,
        output_checkpoint_id: str,
        output_snapshot: WorldSnapshot,
        audit: Mapping[str, Any],
        before_head_update: Callable[[Session], None] | None = None,
    ) -> StoredRound:
        with self.database.session() as session:
            existing = session.get(SimulationRoundModel, round_id)
            if existing is not None:
                if (
                    existing.branch_id != branch_id
                    or existing.round_number != round_number
                    or existing.input_checkpoint_id != input_checkpoint_id
                    or existing.output_checkpoint_id != output_checkpoint_id
                ):
                    raise PersistenceConflict(
                        f"round id {round_id} is already committed with different lineage"
                    )
                return self._stored_round(existing)

            branch = session.get(TimelineBranchModel, branch_id)
            if branch is None:
                raise KeyError(f"unknown timeline branch {branch_id}")
            if branch.active_head_checkpoint_id != input_checkpoint_id:
                raise PersistenceConflict(
                    "round input checkpoint is not the branch active head"
                )

            input_checkpoint = session.get(CheckpointModel, input_checkpoint_id)
            if input_checkpoint is None or input_checkpoint.branch_id != branch_id:
                raise PersistenceConflict(
                    "round input checkpoint does not belong to the branch"
                )

            output = CheckpointModel(
                id=output_checkpoint_id,
                branch_id=branch_id,
                previous_checkpoint_id=input_checkpoint_id,
                snapshot=output_snapshot.to_data(),
                snapshot_digest=output_snapshot.digest(),
                created_at=utc_now(),
            )
            persisted_round = SimulationRoundModel(
                id=round_id,
                branch_id=branch_id,
                round_number=round_number,
                input_checkpoint_id=input_checkpoint_id,
                output_checkpoint_id=output_checkpoint_id,
                audit=dict(audit),
                created_at=utc_now(),
            )
            session.add_all((output, persisted_round))
            session.flush()

            if before_head_update is not None:
                before_head_update(session)

            branch.active_head_checkpoint_id = output_checkpoint_id
            stored = self._stored_round(persisted_round)

        return stored

    def load_run_context(self, run_or_branch_id: str) -> StoredRunContext:
        with Session(self.database.engine()) as session:
            branch = session.get(TimelineBranchModel, run_or_branch_id)
            if branch is None:
                run = session.get(SimulationRunModel, run_or_branch_id)
                if run is None:
                    raise KeyError(f"unknown simulation run or branch {run_or_branch_id}")
                branch = session.scalar(
                    select(TimelineBranchModel).where(
                        TimelineBranchModel.run_id == run.id,
                        TimelineBranchModel.parent_branch_id.is_(None),
                    )
                )
                if branch is None:
                    raise PersistenceConflict(
                        f"run {run.id} has no root timeline branch"
                    )
            else:
                run = session.get(SimulationRunModel, branch.run_id)
                if run is None:
                    raise PersistenceConflict(
                        f"branch {branch.id} references missing run {branch.run_id}"
                    )

            if branch.active_head_checkpoint_id is None:
                raise PersistenceConflict(f"branch {branch.id} has no active checkpoint")
            if run.scene_data is None:
                raise PersistenceConflict(
                    f"run {run.id} predates persisted scene replay data"
                )
            return StoredRunContext(
                run_id=run.id,
                branch_id=branch.id,
                checkpoint_id=branch.active_head_checkpoint_id,
                root_seed=int(run.root_seed),
                scene_id=run.scene_id,
                scene_revision=run.scene_revision,
                scene_data=dict(run.scene_data or {}),
                entropy_salt=branch.entropy_salt,
            )

    def load_round(self, round_id: str) -> StoredRound:
        with Session(self.database.engine()) as session:
            persisted_round = session.get(SimulationRoundModel, round_id)
            if persisted_round is None:
                raise KeyError(f"unknown simulation round {round_id}")
            return self._stored_round(persisted_round)

    def branch_head(self, branch_id: str) -> str:
        with Session(self.database.engine()) as session:
            branch = session.get(TimelineBranchModel, branch_id)
            if branch is None or branch.active_head_checkpoint_id is None:
                raise KeyError(f"unknown or uninitialized timeline branch {branch_id}")
            return branch.active_head_checkpoint_id

    def load_checkpoint(self, checkpoint_id: str) -> WorldSnapshot:
        with Session(self.database.engine()) as session:
            checkpoint = session.get(CheckpointModel, checkpoint_id)
            if checkpoint is None:
                raise KeyError(f"unknown checkpoint {checkpoint_id}")
            return WorldSnapshot.from_data(checkpoint.snapshot)

    def load_replay_input(self, round_id: str) -> ReplayInput:
        with Session(self.database.engine()) as session:
            persisted_round = session.get(SimulationRoundModel, round_id)
            if persisted_round is None:
                raise KeyError(f"unknown simulation round {round_id}")
            checkpoint = session.get(
                CheckpointModel,
                persisted_round.input_checkpoint_id,
            )
            if checkpoint is None:
                raise PersistenceConflict(
                    f"round {round_id} references a missing input checkpoint"
                )
            branch = session.get(TimelineBranchModel, persisted_round.branch_id)
            if branch is None:
                raise PersistenceConflict(
                    f"round {round_id} references a missing branch"
                )
            run = session.get(SimulationRunModel, branch.run_id)
            if run is None:
                raise PersistenceConflict(
                    f"round {round_id} references a missing run"
                )
            context = StoredRunContext(
                run_id=run.id,
                branch_id=branch.id,
                checkpoint_id=branch.active_head_checkpoint_id or persisted_round.input_checkpoint_id,
                root_seed=int(run.root_seed),
                scene_id=run.scene_id,
                scene_revision=run.scene_revision,
                scene_data=dict(run.scene_data),
                entropy_salt=branch.entropy_salt,
            )
            return ReplayInput(
                round=self._stored_round(persisted_round),
                input_snapshot=WorldSnapshot.from_data(checkpoint.snapshot),
                context=context,
            )

    def round_count(self, branch_id: str) -> int:
        with Session(self.database.engine()) as session:
            return len(
                session.scalars(
                    select(SimulationRoundModel).where(
                        SimulationRoundModel.branch_id == branch_id
                    )
                ).all()
            )

    @staticmethod
    def _stored_round(model: SimulationRoundModel) -> StoredRound:
        return StoredRound(
            round_id=model.id,
            branch_id=model.branch_id,
            round_number=model.round_number,
            input_checkpoint_id=model.input_checkpoint_id,
            output_checkpoint_id=model.output_checkpoint_id,
            audit=dict(model.audit),
        )
