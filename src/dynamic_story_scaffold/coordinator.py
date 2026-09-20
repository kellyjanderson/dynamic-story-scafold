from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .arbitration import ArbitrationAudit, arbitrate_proposals
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
from .core.identity import OperationId
from .core.proposals import ActionProposal
from .simulation import Simulation
from .state import WorldState


class CoordinatorError(RuntimeError):
    """Base error for round coordination failures."""


class RoundInProgressError(CoordinatorError):
    """Raised when a coordinator is asked to recursively advance a round."""


@dataclass(slots=True)
class _ProposalState:
    proposal: ActionProposal
    status: ProposalTerminalStatus | None = None
    detail: str | None = None

    @property
    def proposal_id(self) -> str:
        return str(self.proposal.operation_id)

    @property
    def intent(self) -> ActionIntent:
        return self.proposal.intent

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
    """Single-writer round coordinator with explicit phase barriers."""

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
        proposed_inputs: list[ActionIntent | ActionProposal] = []
        round_id = RoundId.new()
        before = self.simulation.state.to_snapshot()
        candidate = WorldState.from_snapshot(before)
        perceptions: dict[str, tuple] = {}
        intents: list[ActionIntent] = []
        resolutions: list[ActionResolution] = []
        arbitration_audits: tuple[ArbitrationAudit, ...] = ()
        resolution_order: tuple[OperationId, ...] = ()
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
                    selected = self.intent_provider.choose_intent(
                        actor=actor,
                        world=before,
                        observations=perceptions.get(actor_id, ()),
                        rng=self.simulation.random.stream(
                            "intent", str(round_id), actor_id
                        ),
                    )
                    if isinstance(selected, ActionProposal):
                        proposed_inputs.append(selected)
                        intents.append(selected.intent)
                    else:
                        proposed_inputs.append(selected)
                        intents.append(selected)

            self._phase(phases, CoordinatorPhase.NORMALIZE_PROPOSALS)
            for index, selected in enumerate(proposed_inputs):
                if isinstance(selected, ActionProposal):
                    normalized = selected
                else:
                    normalized = ActionProposal(
                        operation_id=OperationId(
                            f"{round_id}:{selected.actor.kind.value}:{selected.actor.id}"
                        ),
                        intent=selected,
                    )
                proposal = _ProposalState(normalized)
                if index >= self.work_budget.max_proposals:
                    proposal.status = ProposalTerminalStatus.OVERFLOWED
                    proposal.detail = "proposal budget exceeded"
                elif normalized.causal_depth > self.work_budget.max_causal_depth:
                    proposal.status = ProposalTerminalStatus.OVERFLOWED
                    proposal.detail = "causal depth budget exceeded"
                proposals.append(proposal)

            self._phase(phases, CoordinatorPhase.REACTION_ARBITRATION)
            schedulable = tuple(
                proposal.proposal for proposal in proposals if proposal.status is None
            )
            if schedulable:
                arbitration = arbitrate_proposals(
                    schedulable,
                    snapshot=before,
                    random_streams=self.simulation.random,
                    round_id=str(round_id),
                )
                arbitration_audits = arbitration.audits
                resolution_order = arbitration.resolution_order
                states_by_id = {
                    proposal.proposal.operation_id: proposal for proposal in proposals
                }
                for outcome in arbitration.outcomes:
                    state = states_by_id[outcome.operation_id]
                    state.status = outcome.status
                    state.detail = outcome.detail

            self._phase(phases, CoordinatorPhase.RESOLVE)
            by_operation = {
                proposal.proposal.operation_id: proposal for proposal in proposals
            }
            accepted = [
                by_operation[operation]
                for operation in resolution_order
                if by_operation[operation].status is ProposalTerminalStatus.ACCEPTED
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
                arbitrations=tuple(
                    self._arbitration_data(audit) for audit in arbitration_audits
                ),
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
            if not committed:
                assert self.simulation.state.to_snapshot().digest() == before.digest()
            raise
        finally:
            self._active = False

    @staticmethod
    def _phase(phases: list[CoordinatorPhase], phase: CoordinatorPhase) -> None:
        phases.append(phase)

    @staticmethod
    def _arbitration_data(audit: ArbitrationAudit) -> Mapping[str, object]:
        return {
            "conflict_id": audit.conflict_id,
            "rule": audit.rule.value,
            "candidate_ids": tuple(str(item) for item in audit.candidate_ids),
            "selected_ids": tuple(str(item) for item in audit.selected_ids),
            "outcomes": tuple(
                {
                    "operation_id": str(outcome.operation_id),
                    "status": outcome.status.value,
                    "detail": outcome.detail,
                }
                for outcome in audit.outcomes
            ),
            "stochastic_rule": audit.stochastic_rule,
            "weights": tuple((str(item), weight) for item, weight in audit.weights),
            "modifiers": tuple(
                (str(item), modifier) for item, modifier in audit.modifiers
            ),
            "semantic_stream_key": audit.semantic_stream_key,
            "sampled_value": audit.sampled_value,
            "chosen_result": (
                None if audit.chosen_result is None else str(audit.chosen_result)
            ),
        }
