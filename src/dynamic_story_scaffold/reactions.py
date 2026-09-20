from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Mapping, Protocol

from .arbitration import ArbitrationAudit, arbitrate_proposals
from .core import (
    ActionProposal,
    OperationId,
    ProposalTerminalStatus,
    RandomStreams,
    TargetRef,
    WorkBudget,
    WorldSnapshot,
)


class ReactionDirective(StrEnum):
    CANCEL = "cancel"
    REDIRECT = "redirect"
    MODIFY = "modify"


@dataclass(frozen=True, slots=True)
class ReactionProposal:
    proposal: ActionProposal
    target_operation_id: OperationId
    directive: ReactionDirective
    redirect_target: TargetRef | None = None
    modifications: Mapping[str, object] | None = None


class ReactionProvider(Protocol):
    def propose_reactions(
        self,
        *,
        trigger: ActionProposal,
        world: WorldSnapshot,
        reaction_depth: int,
        rng,
    ) -> tuple[ReactionProposal, ...]:
        ...


@dataclass(frozen=True, slots=True)
class ReactionAudit:
    operation_id: OperationId
    target_operation_id: OperationId
    status: ProposalTerminalStatus
    reaction_depth: int
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class ReactionWindowAudit:
    trigger_operation_id: OperationId
    reaction_depth: int
    status: ProposalTerminalStatus
    detail: str


@dataclass(frozen=True, slots=True)
class ReactionResult:
    proposals: tuple[ActionProposal, ...]
    reactions: tuple[ActionProposal, ...]
    statuses: Mapping[OperationId, ProposalTerminalStatus]
    audits: tuple[ReactionAudit | ReactionWindowAudit, ...]
    arbitrations: tuple[ArbitrationAudit, ...]


def process_reaction_windows(
    primaries: tuple[ActionProposal, ...],
    *,
    provider: ReactionProvider | None,
    snapshot: WorldSnapshot,
    random_streams: RandomStreams,
    round_id: str,
    budget: WorkBudget,
) -> ReactionResult:
    """Process finite reaction generations without recursive coordinator entry."""

    proposals = {proposal.operation_id: proposal for proposal in primaries}
    statuses: dict[OperationId, ProposalTerminalStatus] = {
        proposal.operation_id: ProposalTerminalStatus.ACCEPTED for proposal in primaries
    }
    seen = set(proposals)
    reactions: list[ActionProposal] = []
    audits: list[ReactionAudit | ReactionWindowAudit] = []
    arbitrations: list[ArbitrationAudit] = []
    queue = deque((proposal, 0) for proposal in primaries)
    reaction_count = 0

    while queue:
        trigger, depth = queue.popleft()
        if provider is None:
            continue
        if depth >= budget.max_reaction_depth:
            audits.append(
                ReactionWindowAudit(
                    trigger_operation_id=trigger.operation_id,
                    reaction_depth=depth,
                    status=ProposalTerminalStatus.OVERFLOWED,
                    detail="reaction depth budget exhausted",
                )
            )
            continue

        offered = tuple(
            provider.propose_reactions(
                trigger=trigger,
                world=snapshot,
                reaction_depth=depth + 1,
                rng=random_streams.stream(
                    "reaction",
                    str(round_id),
                    str(trigger.operation_id),
                    depth + 1,
                ),
            )
        )
        candidates: list[ReactionProposal] = []
        for reaction in offered:
            operation_id = reaction.proposal.operation_id
            if operation_id in seen:
                audits.append(
                    ReactionAudit(
                        operation_id=operation_id,
                        target_operation_id=reaction.target_operation_id,
                        status=ProposalTerminalStatus.CANCELED,
                        reaction_depth=depth + 1,
                        detail="duplicate operation id",
                    )
                )
                continue
            seen.add(operation_id)

            if reaction_count >= budget.max_proposals:
                audits.append(
                    ReactionAudit(
                        operation_id=operation_id,
                        target_operation_id=reaction.target_operation_id,
                        status=ProposalTerminalStatus.OVERFLOWED,
                        reaction_depth=depth + 1,
                        detail="reaction proposal budget exceeded",
                    )
                )
                continue
            reaction_count += 1

            if reaction.proposal.causal_depth > budget.max_causal_depth:
                audits.append(
                    ReactionAudit(
                        operation_id=operation_id,
                        target_operation_id=reaction.target_operation_id,
                        status=ProposalTerminalStatus.OVERFLOWED,
                        reaction_depth=depth + 1,
                        detail="causal depth budget exceeded",
                    )
                )
                continue
            candidates.append(reaction)

        if not candidates:
            continue

        arbitration = arbitrate_proposals(
            tuple(item.proposal for item in candidates),
            snapshot=snapshot,
            random_streams=random_streams,
            round_id=f"{round_id}:reaction:{trigger.operation_id}:{depth + 1}",
        )
        arbitrations.extend(arbitration.audits)
        by_id = {item.proposal.operation_id: item for item in candidates}
        for outcome in arbitration.outcomes:
            reaction = by_id[outcome.operation_id]
            statuses[outcome.operation_id] = outcome.status
            audits.append(
                ReactionAudit(
                    operation_id=outcome.operation_id,
                    target_operation_id=reaction.target_operation_id,
                    status=outcome.status,
                    reaction_depth=depth + 1,
                    detail=outcome.detail,
                )
            )
            if outcome.status is not ProposalTerminalStatus.ACCEPTED:
                continue

            reactions.append(reaction.proposal)
            proposals[reaction.proposal.operation_id] = reaction.proposal
            _apply_directive(reaction, proposals, statuses)
            queue.append((reaction.proposal, depth + 1))

    return ReactionResult(
        proposals=tuple(proposals[key] for key in sorted(proposals)),
        reactions=tuple(reactions),
        statuses=dict(statuses),
        audits=tuple(audits),
        arbitrations=tuple(arbitrations),
    )


def _apply_directive(
    reaction: ReactionProposal,
    proposals: dict[OperationId, ActionProposal],
    statuses: dict[OperationId, ProposalTerminalStatus],
) -> None:
    target = proposals.get(reaction.target_operation_id)
    if target is None:
        statuses[reaction.proposal.operation_id] = ProposalTerminalStatus.FAILED
        return

    if reaction.directive is ReactionDirective.CANCEL:
        statuses[reaction.target_operation_id] = ProposalTerminalStatus.CANCELED
        return

    if reaction.directive is ReactionDirective.REDIRECT:
        if reaction.redirect_target is None:
            statuses[reaction.proposal.operation_id] = ProposalTerminalStatus.FAILED
            return
        proposals[reaction.target_operation_id] = replace(
            target,
            intent=replace(target.intent, target=reaction.redirect_target),
        )
        return

    if reaction.directive is ReactionDirective.MODIFY:
        data = dict(target.intent.data)
        data.update(reaction.modifications or {})
        proposals[reaction.target_operation_id] = replace(
            target,
            intent=replace(target.intent, data=data),
        )
        return

    raise ValueError(f"unsupported reaction directive {reaction.directive!r}")
