from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .core import (
    ActionIntent,
    ActionResolution,
    ActionResolver,
    CoordinatorPhase,
    DisturbanceSet,
    EntityKind,
    EntityRef,
    IntentProvider,
    PerceptionProvider,
    ProposalAudit,
    ProposalTerminalStatus,
    RoundExecutionMetadata,
    RoundId,
    RoundRecord,
    TimeSpan,
    WorkBudget,
    WorldSnapshot,
)
from .simulation import Simulation
from .state import WorldState


class CoordinatorError(RuntimeError):
    """Base error for round coordination failures."""


class RoundInProgressError(CoordinatorError):
    """Raised when a coordinator is asked to recursively advance a round."""


@dataclass(slots=True)
class _ProposalState:
    proposal_id: str
    intent: ActionIntent
    status: ProposalTerminalStatus | None = None
    detail: str | None = None

    def audit(self) -> ProposalAudit:
        if self.status is None:
            raise CoordinatorError(
                f"proposal {self.proposal_id} has no terminal status"
            )
        return ProposalAudit(
            proposal_id=self.proposal_id,
            status=self.status,
            actor=self.intent.actor,
            detail=self.detail,
        )


class RoundCoordinator:
    """Single-writer round coordinator with explicit phase barriers.

    MVP-02 deliberately implements only the execution skeleton. Perception,
    action selection, arbitration, and resolution policy remain delegated to
    optional providers. Canonical world state is replaced only at commit.
    """

    PHASE_ORDER = (
        CoordinatorPhase.SNAPSHOT,
        CoordinatorPhase.PERCEIVE,
        CoordinatorPhase.INTENT,
        CoordinatorPhase.NORMALIZE_PROPOSALS,
        CoordinatorPhase.REACTION_ARBITRATION,
        CoordinatorPhase.RESOLVE,
        CoordinatorPhase.COLLECT_CONSEQUENCES,
        CoordinatorPhase.COMMIT,
        CoordinatorPhase.RECORD,
    )

    def __init__(
        self,
        simulation: Simulation,
        *,
        perception_provider: PerceptionProvider | None = None,
        intent_provider: IntentProvider | None = None,
        resolver: ActionResolver | None = None,
        work_budget: WorkBudget | None = None,
    ) -> None:
        self.simulation = simulation
        self.perception_provider = perception_provider
        self.intent_provider = intent_provider
        self.resolver = resolver
        self.work_budget = work_budget or WorkBudget()
        self._active = False
        self.records: list[RoundRecord] = []

    @property
    def active(self) -> bool:
        return self._active

    def advance_round(self) -> RoundRecord:
        if self._active:
            raise RoundInProgressError("round advancement is already active")

        self._active = True
        phases: list[CoordinatorPhase] = []
        proposals: list[_ProposalState] = []
        round_id = RoundId.new()
        before = self.simulation.state.to_snapshot()
        candidate = WorldState.from_snapshot(before)
        perceptions: dict[str, tuple] = {}
        intents: list[ActionIntent] = []
        resolutions: list[ActionResolution] = []
        committed = False

        try:
            self._phase(phases, CoordinatorPhase.SNAPSHOT)

            self._phase(phases, CoordinatorPhase.PERCEIVE)
            if self.perception_provider is not None:
                for actor_id in sorted(candidate.actors):
                    actor = EntityRef(EntityKind.ACTOR, actor_id)
                    observations = self.perception_provider.perceive(
                        actor=actor,
                        world=before,
                        rng=self.simulation.random.stream(
                            "perception", str(round_id), actor_id
                        ),
                    )
                    perceptions[actor_id] = tuple(observations)

            self._phase(phases, CoordinatorPhase.INTENT)
            if self.intent_provider is not None:
                for actor_id in sorted(candidate.actors):
                    actor = EntityRef(EntityKind.ACTOR, actor_id)
                    intent = self.intent_provider.choose_intent(
                        actor=actor,
                        world=before,
                        observations=perceptions.get(actor_id, ()),
                        rng=self.simulation.random.stream(
                            "intent", str(round_id), actor_id
                        ),
                    )
                    intents.append(intent)

            self._phase(phases, CoordinatorPhase.NORMALIZE_PROPOSALS)
            for index, intent in enumerate(intents):
                proposal = _ProposalState(
                    proposal_id=f"{round_id}:{index}",
                    intent=intent,
                )
                if index >= self.work_budget.max_proposals:
                    proposal.status = ProposalTerminalStatus.OVERFLOWED
                    proposal.detail = "proposal budget exceeded"
                proposals.append(proposal)

            self._phase(phases, CoordinatorPhase.REACTION_ARBITRATION)
            # MVP-02 has no arbitration policy yet. Every in-budget proposal is
            # accepted into the resolver stage; later slices replace this rule.
            for proposal in proposals:
                if proposal.status is None:
                    proposal.status = ProposalTerminalStatus.ACCEPTED

            self._phase(phases, CoordinatorPhase.RESOLVE)
            accepted = [
                proposal
                for proposal in proposals
                if proposal.status is ProposalTerminalStatus.ACCEPTED
            ]
            if len(accepted) > self.work_budget.max_resolutions:
                for proposal in accepted[self.work_budget.max_resolutions :]:
                    proposal.status = ProposalTerminalStatus.OVERFLOWED
                    proposal.detail = "resolution budget exceeded"
                accepted = accepted[: self.work_budget.max_resolutions]

            if self.resolver is not None:
                for proposal in accepted:
                    try:
                        resolution = self.resolver.resolve(
                            intent=proposal.intent,
                            world=before,
                            rng=self.simulation.random.stream(
                                "resolution",
                                str(round_id),
                                proposal.proposal_id,
                            ),
                        )
                    except Exception:
                        proposal.status = ProposalTerminalStatus.FAILED
                        proposal.detail = "resolver raised before commit"
                        raise
                    resolutions.append(resolution)

            self._phase(phases, CoordinatorPhase.COLLECT_CONSEQUENCES)
            disturbances = DisturbanceSet()
            actor_updates = []
            for resolution in resolutions:
                disturbances = disturbances.merged(resolution.disturbances)
                actor_updates.extend(resolution.actor_updates)

            for update in actor_updates:
                candidate.apply_actor_update(update)

            # Advance environment/time on the detached candidate. Reuse the
            # simulation's deterministic tick implementation without exposing
            # canonical mutable state to providers.
            candidate_simulation = Simulation(
                self.simulation.scene,
                state=candidate,
                seed=self.simulation.seed,
            )
            candidate_simulation.run_context = self.simulation.run_context
            candidate_simulation.random = self.simulation.random
            candidate_simulation.rng = self.simulation.rng
            tick = candidate_simulation.tick(disturbances=disturbances)

            self._phase(phases, CoordinatorPhase.COMMIT)
            self.simulation.state = candidate_simulation.state
            committed = True

            self._phase(phases, CoordinatorPhase.RECORD)
            after = self.simulation.state.to_snapshot()
            execution = RoundExecutionMetadata(
                round_id=round_id,
                phases=tuple(phases),
                proposals=tuple(proposal.audit() for proposal in proposals),
                state_before_digest=before.digest(),
                state_after_digest=after.digest(),
                committed=True,
            )
            record = RoundRecord(
                round_number=self.simulation.state.tick,
                span=TimeSpan(
                    float(before.to_data()["elapsed_seconds"]),
                    self.simulation.state.elapsed_seconds,
                ),
                perceptions=perceptions,
                intents=tuple(intents),
                resolutions=tuple(resolutions),
                ticks=(tick,),
                state_before=before.to_data(),
                state_after=after.to_data(),
                execution=execution,
            )
            self.records.append(record)
            return record
        except Exception:
            # Canonical state has not been replaced until COMMIT. If RECORD were
            # ever to fail after commit, do not lie about rollback semantics.
            if not committed:
                assert self.simulation.state.to_snapshot().digest() == before.digest()
            raise
        finally:
            self._active = False

    @staticmethod
    def _phase(phases: list[CoordinatorPhase], phase: CoordinatorPhase) -> None:
        phases.append(phase)
