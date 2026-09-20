from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable, Mapping

from .core.identity import OperationId
from .core.proposals import ActionProposal
from .core.randomness import RandomStreams
from .core.records import ProposalTerminalStatus, WorldSnapshot
from .core.refs import StateRef
from .dependencies import DependencyPlan, dependency_plan


class ArbitrationRule(StrEnum):
    EXCLUSIVE_WEIGHTED_CHOICE = "exclusive_weighted_choice"
    CYCLE_WEIGHTED_CHOICE = "cycle_weighted_choice"


@dataclass(frozen=True, slots=True)
class ArbitrationOutcome:
    operation_id: OperationId
    status: ProposalTerminalStatus
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class ArbitrationAudit:
    conflict_id: str
    rule: ArbitrationRule
    candidate_ids: tuple[OperationId, ...]
    selected_ids: tuple[OperationId, ...]
    outcomes: tuple[ArbitrationOutcome, ...]
    stochastic_rule: str | None = None
    weights: tuple[tuple[OperationId, float], ...] = ()
    modifiers: tuple[tuple[OperationId, float], ...] = ()
    semantic_stream_key: tuple[str, ...] | None = None
    sampled_value: float | None = None
    chosen_result: OperationId | None = None


@dataclass(frozen=True, slots=True)
class ArbitrationResult:
    outcomes: tuple[ArbitrationOutcome, ...]
    audits: tuple[ArbitrationAudit, ...]
    resolution_order: tuple[OperationId, ...]

    def status_for(self, operation_id: OperationId) -> ProposalTerminalStatus:
        for outcome in self.outcomes:
            if outcome.operation_id == operation_id:
                return outcome.status
        raise KeyError(operation_id)


def _state_ref_key(ref: StateRef) -> str:
    return str(ref)


def _weighted_choice(
    *,
    conflict_id: str,
    rule: ArbitrationRule,
    candidates: tuple[ActionProposal, ...],
    snapshot: WorldSnapshot,
    random_streams: RandomStreams,
    round_id: str,
    weights: Mapping[OperationId, float] | None = None,
    modifiers: Mapping[OperationId, float] | None = None,
) -> tuple[OperationId, ArbitrationAudit]:
    """Select one candidate from a stable ordering and record full stochastic audit."""

    del snapshot  # Reserved policy input; the immutable snapshot is part of the interface.
    ordered = tuple(sorted(candidates, key=lambda item: item.operation_id))
    if not ordered:
        raise ValueError("arbitration requires at least one candidate")

    weights = weights or {}
    modifiers = modifiers or {}
    effective: list[tuple[OperationId, float]] = []
    modifier_values: list[tuple[OperationId, float]] = []
    for proposal in ordered:
        base = float(weights.get(proposal.operation_id, 1.0))
        modifier = float(modifiers.get(proposal.operation_id, 1.0))
        if base < 0 or modifier < 0:
            raise ValueError("arbitration weights and modifiers must be non-negative")
        effective.append((proposal.operation_id, base * modifier))
        modifier_values.append((proposal.operation_id, modifier))

    total = sum(weight for _, weight in effective)
    if total <= 0:
        raise ValueError("arbitration requires positive total weight")

    stream_key = ("arbitration", str(round_id), conflict_id)
    sampled = random_streams.stream(*stream_key).random()
    threshold = sampled * total
    cumulative = 0.0
    chosen = effective[-1][0]
    for operation_id, weight in effective:
        cumulative += weight
        if threshold < cumulative:
            chosen = operation_id
            break

    outcomes = tuple(
        ArbitrationOutcome(
            operation_id=proposal.operation_id,
            status=(
                ProposalTerminalStatus.ACCEPTED
                if proposal.operation_id == chosen
                else ProposalTerminalStatus.REJECTED
            ),
            detail=(
                f"selected by {rule.value}"
                if proposal.operation_id == chosen
                else f"not selected by {rule.value}"
            ),
        )
        for proposal in ordered
    )
    return chosen, ArbitrationAudit(
        conflict_id=conflict_id,
        rule=rule,
        candidate_ids=tuple(item.operation_id for item in ordered),
        selected_ids=(chosen,),
        outcomes=outcomes,
        stochastic_rule="weighted_choice",
        weights=tuple(effective),
        modifiers=tuple(modifier_values),
        semantic_stream_key=stream_key,
        sampled_value=sampled,
        chosen_result=chosen,
    )


def arbitrate_proposals(
    proposals: Iterable[ActionProposal],
    *,
    snapshot: WorldSnapshot,
    random_streams: RandomStreams,
    round_id: str,
    weights: Mapping[OperationId, float] | None = None,
    modifiers: Mapping[OperationId, float] | None = None,
) -> ArbitrationResult:
    """Reduce a finite proposal graph to finite terminal outcomes.

    Exclusive-resource conflicts are arbitrated before dependency traversal.
    SCCs are treated as bounded simultaneous conflicts rather than execution waits.
    """

    items = tuple(proposals)
    by_id = {proposal.operation_id: proposal for proposal in items}
    if len(by_id) != len(items):
        raise ValueError("proposal operation ids must be unique")

    plan: DependencyPlan = dependency_plan(items)
    statuses: dict[OperationId, ArbitrationOutcome] = {}
    audits: list[ArbitrationAudit] = []

    exclusive_groups: dict[StateRef, list[ActionProposal]] = {}
    for proposal in items:
        for target in proposal.exclusive_targets:
            exclusive_groups.setdefault(target, []).append(proposal)

    for target in sorted(exclusive_groups, key=lambda ref: ref.sort_key()):
        active = tuple(
            proposal
            for proposal in sorted(
                exclusive_groups[target], key=lambda item: item.operation_id
            )
            if proposal.operation_id not in statuses
        )
        if len(active) < 2:
            continue
        conflict_id = f"exclusive:{_state_ref_key(target)}"
        chosen, audit = _weighted_choice(
            conflict_id=conflict_id,
            rule=ArbitrationRule.EXCLUSIVE_WEIGHTED_CHOICE,
            candidates=active,
            snapshot=snapshot,
            random_streams=random_streams,
            round_id=round_id,
            weights=weights,
            modifiers=modifiers,
        )
        audits.append(audit)
        for outcome in audit.outcomes:
            if outcome.operation_id != chosen:
                statuses[outcome.operation_id] = outcome

    resolution_order: list[OperationId] = []
    for component in plan.components:
        component_items = tuple(by_id[operation] for operation in component.operations)
        eligible = tuple(
            proposal
            for proposal in component_items
            if proposal.operation_id not in statuses
        )
        if not eligible:
            continue

        external_dependencies = {
            proposal.operation_id: tuple(
                dependency
                for dependency in sorted(proposal.dependencies)
                if dependency not in component.operations
            )
            for proposal in eligible
        }
        blocked = {
            operation
            for operation, dependencies in external_dependencies.items()
            if any(
                dependency in statuses
                and statuses[dependency].status is not ProposalTerminalStatus.ACCEPTED
                for dependency in dependencies
            )
        }
        for operation in sorted(blocked):
            statuses[operation] = ArbitrationOutcome(
                operation,
                ProposalTerminalStatus.DEFERRED,
                "dependency did not reach accepted status",
            )

        eligible = tuple(
            proposal
            for proposal in eligible
            if proposal.operation_id not in blocked
        )
        if not eligible:
            continue

        if component.cyclic and len(eligible) > 1:
            conflict_id = "cycle:" + ",".join(
                str(proposal.operation_id)
                for proposal in sorted(eligible, key=lambda item: item.operation_id)
            )
            chosen, audit = _weighted_choice(
                conflict_id=conflict_id,
                rule=ArbitrationRule.CYCLE_WEIGHTED_CHOICE,
                candidates=eligible,
                snapshot=snapshot,
                random_streams=random_streams,
                round_id=round_id,
                weights=weights,
                modifiers=modifiers,
            )
            audits.append(audit)
            for outcome in audit.outcomes:
                statuses[outcome.operation_id] = outcome
            resolution_order.append(chosen)
            continue

        for proposal in sorted(eligible, key=lambda item: item.operation_id):
            statuses[proposal.operation_id] = ArbitrationOutcome(
                proposal.operation_id,
                ProposalTerminalStatus.ACCEPTED,
                "dependency region resolved",
            )
            resolution_order.append(proposal.operation_id)

    for operation_id in sorted(by_id):
        statuses.setdefault(
            operation_id,
            ArbitrationOutcome(
                operation_id,
                ProposalTerminalStatus.REJECTED,
                "proposal was not eligible for resolution",
            ),
        )

    return ArbitrationResult(
        outcomes=tuple(statuses[operation_id] for operation_id in sorted(statuses)),
        audits=tuple(audits),
        resolution_order=tuple(resolution_order),
    )
