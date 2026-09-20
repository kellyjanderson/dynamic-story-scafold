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
from .effect_runtime import apply_effects
from .events import (
    CausalGenerationQueue,
    GenerationHandler,
    generation_items_for_disturbances,
)
from .reactions import ReactionProvider, process_reaction_windows
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
        reaction_provider: ReactionProvider | None = None,
        event_handler: GenerationHandler | None = None,
        effect_handler: GenerationHandler | None = None,
        work_budget: WorkBudget | None = None,
    ) -> None:
        self.simulation = simulation
        self.perception_provider = perception_provider
        self.intent_provider = intent_provider
        self.resolver = resolver
        self.reaction_provider = reaction_provider
        self.event_handler = event_handler
        self.effect_handler = effect_handler
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
        reaction_audits = ()
        generation_audits = ()
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

            accepted_primaries = tuple(
                proposal.proposal
                for proposal in proposals
                if proposal.status is ProposalTerminalStatus.ACCEPTED
            )
            reaction_result = process_reaction_windows(
                accepted_primaries,
                provider=self.reaction_provider,
                snapshot=before,
                random_streams=self.simulation.random,
                round_id=str(round_id),
                budget=self.work_budget,
            )
            reaction_audits = reaction_result.audits
            arbitration_audits = (*arbitration_audits, *reaction_result.arbitrations)
            states_by_id = {
                proposal.proposal.operation_id: proposal for proposal in proposals
            }
            for normalized in reaction_result.proposals:
                state = states_by_id.get(normalized.operation_id)
                status = reaction_result.statuses.get(normalized.operation_id)
                if state is None:
                    state = _ProposalState(
                        normalized,
                        status=status,
                        detail="reaction proposal",
                    )
                    proposals.append(state)
                    states_by_id[normalized.operation_id] = state
                else:
                    state.proposal = normalized
                    if status is not None:
                        state.status = status
            resolution_order = tuple(
                operation
                for operation in resolution_order
                if states_by_id[operation].status is ProposalTerminalStatus.ACCEPTED
            ) + tuple(
                proposal.operation_id
                for proposal in reaction_result.reactions
                if reaction_result.statuses.get(proposal.operation_id)
                is ProposalTerminalStatus.ACCEPTED
            )

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

            resolved_pairs: list[tuple[_ProposalState, ActionResolution]] = []
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
                    resolved_pairs.append((proposal, resolution))

            self._phase(phases, CoordinatorPhase.COLLECT_CONSEQUENCES)
            forcing = []
            actor_updates = []
            generation_items = []
            for proposal, resolution in resolved_pairs:
                forcing.extend(resolution.disturbances.forcing)
                actor_updates.extend(resolution.actor_updates)
                generation_items.extend(
                    generation_items_for_disturbances(
                        resolution.disturbances,
                        parent_operation_id=proposal.proposal.operation_id,
                        causal_depth=proposal.proposal.causal_depth + 1,
                    )
                )

            generation_result = CausalGenerationQueue(self.work_budget).process(
                generation_items,
                snapshot=before,
                event_handler=self.event_handler,
                effect_handler=self.effect_handler,
            )
            generation_audits = generation_result.audits
            disturbances = DisturbanceSet(
                forcing=tuple(forcing) + generation_result.disturbances.forcing,
                events=generation_result.disturbances.events,
                effects=generation_result.disturbances.effects,
            )

            for update in actor_updates:
                candidate.apply_actor_update(update)

            effects_by_actor: dict[str, list] = {}
            for effect in disturbances.effects:
                if (
                    isinstance(effect.target, EntityRef)
                    and effect.target.kind is EntityKind.ACTOR
                    and effect.target.id in candidate.actors
                ):
                    effects_by_actor.setdefault(effect.target.id, []).append(effect)
            now_seconds = float(before.to_data().get("elapsed_seconds", 0.0))
            for actor_id, incoming_effects in effects_by_actor.items():
                actor = candidate.actor(actor_id)
                actor.active_effects = list(
                    apply_effects(
                        actor.active_effects,
                        incoming_effects,
                        now_seconds=now_seconds,
                    )
                )

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
                reactions=tuple(
                    self._reaction_data(audit) for audit in reaction_audits
                ),
                generations=tuple(
                    self._generation_data(audit) for audit in generation_audits
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
    def _reaction_data(audit) -> Mapping[str, object]:
        data = {
            "status": audit.status.value,
            "reaction_depth": audit.reaction_depth,
            "detail": audit.detail,
        }
        if hasattr(audit, "operation_id"):
            data["operation_id"] = str(audit.operation_id)
            data["target_operation_id"] = str(audit.target_operation_id)
        else:
            data["trigger_operation_id"] = str(audit.trigger_operation_id)
        return data

    @staticmethod
    def _generation_data(audit) -> Mapping[str, object]:
        return {
            "operation_id": str(audit.operation_id),
            "kind": audit.kind.value,
            "status": audit.status.value,
            "causal_parent": (
                None if audit.causal_parent is None else str(audit.causal_parent)
            ),
            "causal_depth": audit.causal_depth,
            "generation": audit.generation,
            "detail": audit.detail,
        }

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
