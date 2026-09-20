from __future__ import annotations

import pytest
from hypothesis import given, settings, strategies as st

from dynamic_story_scaffold.core import (
    ActionIntent,
    ActionProposal,
    EntityKind,
    EntityRef,
    OperationId,
    ProposalTerminalStatus,
    RandomStreams,
    WorkBudget,
    WorldSnapshot,
)
from dynamic_story_scaffold.reactions import (
    ReactionDirective,
    ReactionProposal,
    ReactionWindowAudit,
    process_reaction_windows,
)


SNAPSHOT = WorldSnapshot.from_data({"tick": 0, "elapsed_seconds": 0.0, "actors": {}})


def actor(name: str) -> EntityRef:
    return EntityRef(EntityKind.ACTOR, name)


def proposal(
    operation_id: str,
    *,
    actor_id: str,
    target: EntityRef | None = None,
    causal_parent: str | None = None,
    causal_depth: int = 0,
) -> ActionProposal:
    return ActionProposal(
        operation_id=OperationId(operation_id),
        intent=ActionIntent(actor=actor(actor_id), action="attack", target=target),
        causal_parent=None if causal_parent is None else OperationId(causal_parent),
        causal_depth=causal_depth,
    )


@pytest.mark.integration
def test_hold_the_line_interception_cancels_primary() -> None:
    primary = proposal("attack-1", actor_id="attacker", target=actor("protected"))

    class Provider:
        def propose_reactions(self, *, trigger, world, reaction_depth, rng):
            if trigger.operation_id != primary.operation_id:
                return ()
            intercept = proposal(
                "intercept-1",
                actor_id="guardian",
                target=actor("attacker"),
                causal_parent=str(trigger.operation_id),
                causal_depth=trigger.causal_depth + 1,
            )
            return (
                ReactionProposal(
                    proposal=intercept,
                    target_operation_id=trigger.operation_id,
                    directive=ReactionDirective.CANCEL,
                ),
            )

    result = process_reaction_windows(
        (primary,),
        provider=Provider(),
        snapshot=SNAPSHOT,
        random_streams=RandomStreams(7),
        round_id="hold-line",
        budget=WorkBudget(max_reaction_depth=2),
    )

    assert result.statuses[primary.operation_id] is ProposalTerminalStatus.CANCELED
    assert result.statuses[OperationId("intercept-1")] is ProposalTerminalStatus.ACCEPTED
    assert len(result.reactions) == 1


@pytest.mark.unit
def test_intercept_counter_intercept_cycle_stops_at_depth_budget() -> None:
    primary = proposal("primary", actor_id="a", target=actor("b"))

    class Provider:
        def propose_reactions(self, *, trigger, world, reaction_depth, rng):
            child = proposal(
                f"reaction-{reaction_depth}",
                actor_id=f"reactor-{reaction_depth}",
                target=trigger.intent.actor,
                causal_parent=str(trigger.operation_id),
                causal_depth=reaction_depth,
            )
            return (
                ReactionProposal(
                    proposal=child,
                    target_operation_id=trigger.operation_id,
                    directive=ReactionDirective.CANCEL,
                ),
            )

    result = process_reaction_windows(
        (primary,),
        provider=Provider(),
        snapshot=SNAPSHOT,
        random_streams=RandomStreams(11),
        round_id="counter-cycle",
        budget=WorkBudget(max_reaction_depth=2, max_causal_depth=8),
    )

    assert len(result.reactions) == 2
    assert any(
        isinstance(audit, ReactionWindowAudit)
        and audit.status is ProposalTerminalStatus.OVERFLOWED
        for audit in result.audits
    )


@st.composite
def bounds(draw):
    return (
        draw(st.integers(min_value=0, max_value=6)),
        draw(st.integers(min_value=0, max_value=8)),
    )


@pytest.mark.unit
@settings(max_examples=60, deadline=None)
@given(bounds())
def test_bounded_reaction_structures_terminate_without_waiting(
    limits: tuple[int, int],
) -> None:
    max_depth, max_causal = limits
    primary = proposal("root", actor_id="root", target=actor("target"))

    class Provider:
        def propose_reactions(self, *, trigger, world, reaction_depth, rng):
            child = proposal(
                f"{trigger.operation_id}-r{reaction_depth}",
                actor_id=f"actor-{reaction_depth}",
                causal_parent=str(trigger.operation_id),
                causal_depth=reaction_depth,
            )
            return (
                ReactionProposal(
                    proposal=child,
                    target_operation_id=trigger.operation_id,
                    directive=ReactionDirective.MODIFY,
                    modifications={"reaction_depth": reaction_depth},
                ),
            )

    result = process_reaction_windows(
        (primary,),
        provider=Provider(),
        snapshot=SNAPSHOT,
        random_streams=RandomStreams(19),
        round_id="property",
        budget=WorkBudget(
            max_reaction_depth=max_depth,
            max_causal_depth=max_causal,
            max_proposals=16,
        ),
    )

    assert len(result.reactions) <= min(max_depth, max_causal, 16)
    assert all(status is not None for status in result.statuses.values())
