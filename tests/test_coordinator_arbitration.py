from __future__ import annotations

from pathlib import Path

import pytest

from dynamic_story_scaffold import Simulation, load_scene
from dynamic_story_scaffold.coordinator import RoundCoordinator
from dynamic_story_scaffold.core import (
    ActionIntent,
    ActionProposal,
    ActionResolution,
    EntityKind,
    EntityRef,
    OperationId,
    Outcome,
    ProposalTerminalStatus,
    StateRef,
    SubresourceKey,
)

EXAMPLE = Path(__file__).parents[1] / "examples" / "hollow_bank.yaml"


@pytest.mark.integration
def test_coordinator_arbitrates_exclusive_claims_before_resolution() -> None:
    sim = Simulation(load_scene(EXAMPLE), seed=73)
    unique_object = StateRef(
        EntityRef(EntityKind.OBJECT, "single-token"),
        SubresourceKey.of("ownership"),
    )
    resolved: list[str] = []

    class Intent:
        def choose_intent(self, *, actor, world, observations, rng):
            return ActionProposal(
                operation_id=OperationId(f"claim:{actor.id}"),
                intent=ActionIntent(actor=actor, action="claim"),
                exclusive_claims=frozenset({unique_object}),
            )

    class Resolver:
        def resolve(self, *, intent, world, rng):
            resolved.append(intent.actor.id)
            return ActionResolution(intent=intent, outcome=Outcome.SUCCESS)

    record = RoundCoordinator(
        sim,
        intent_provider=Intent(),
        resolver=Resolver(),
    ).advance_round()

    assert record.execution is not None
    statuses = [proposal.status for proposal in record.execution.proposals]
    assert statuses.count(ProposalTerminalStatus.ACCEPTED) == 1
    assert statuses.count(ProposalTerminalStatus.REJECTED) == len(statuses) - 1
    assert len(resolved) == 1
    assert len(record.execution.arbitrations) == 1

    audit = record.execution.arbitrations[0]
    assert audit["conflict_id"].startswith("exclusive:")
    assert audit["stochastic_rule"] == "weighted_choice"
    assert audit["sampled_value"] is not None
    assert tuple(audit["semantic_stream_key"][:1]) == ("arbitration",)
