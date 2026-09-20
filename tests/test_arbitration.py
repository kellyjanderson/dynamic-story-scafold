from __future__ import annotations

import random

import pytest
from hypothesis import given, settings, strategies as st

from dynamic_story_scaffold.arbitration import arbitrate_proposals
from dynamic_story_scaffold.core import (
    ActionIntent,
    ActionProposal,
    ComponentRef,
    EntityKind,
    EntityRef,
    OperationId,
    ProposalTerminalStatus,
    RandomStreams,
    StateRef,
    SubresourceKey,
    WorldSnapshot,
    WriteClaim,
    WriteClass,
)
from dynamic_story_scaffold.dependencies import dependency_plan


def _actor(name: str) -> EntityRef:
    return EntityRef(EntityKind.ACTOR, name)


def _proposal(
    name: str,
    *,
    dependencies: tuple[str, ...] = (),
    write_set: tuple[WriteClaim, ...] = (),
    exclusive_claims: frozenset[StateRef] = frozenset(),
) -> ActionProposal:
    operation_id = OperationId(name)
    return ActionProposal(
        operation_id=operation_id,
        intent=ActionIntent(actor=_actor(name), action="wait"),
        dependencies=frozenset(OperationId(item) for item in dependencies),
        write_set=write_set,
        exclusive_claims=exclusive_claims,
    )


SNAPSHOT = WorldSnapshot.from_data({"tick": 0, "actors": {}})


@pytest.mark.unit
def test_acyclic_graph_resolves_in_declared_dependency_order() -> None:
    proposals = (
        _proposal("third", dependencies=("second",)),
        _proposal("first"),
        _proposal("second", dependencies=("first",)),
    )

    plan = dependency_plan(proposals)
    result = arbitrate_proposals(
        proposals,
        snapshot=SNAPSHOT,
        random_streams=RandomStreams(7),
        round_id="round-1",
    )

    assert tuple(component.operations for component in plan.components) == (
        (OperationId("first"),),
        (OperationId("second"),),
        (OperationId("third"),),
    )
    assert result.resolution_order == (
        OperationId("first"),
        OperationId("second"),
        OperationId("third"),
    )
    assert all(
        outcome.status is ProposalTerminalStatus.ACCEPTED
        for outcome in result.outcomes
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "proposals",
    [
        (
            _proposal("a", dependencies=("b",)),
            _proposal("b", dependencies=("a",)),
        ),
        (
            _proposal("a", dependencies=("c",)),
            _proposal("b", dependencies=("a",)),
            _proposal("c", dependencies=("b",)),
        ),
    ],
)
def test_two_and_three_node_cycles_terminate(proposals: tuple[ActionProposal, ...]) -> None:
    result = arbitrate_proposals(
        proposals,
        snapshot=SNAPSHOT,
        random_streams=RandomStreams(11),
        round_id="cycle-round",
    )

    assert len(result.outcomes) == len(proposals)
    assert sum(
        outcome.status is ProposalTerminalStatus.ACCEPTED
        for outcome in result.outcomes
    ) == 1
    assert all(outcome.status is not None for outcome in result.outcomes)
    assert len(result.audits) == 1


@pytest.mark.unit
def test_same_seed_replays_stochastic_cycle_arbitration() -> None:
    proposals = (
        _proposal("a", dependencies=("b",)),
        _proposal("b", dependencies=("a",)),
    )

    first = arbitrate_proposals(
        proposals,
        snapshot=SNAPSHOT,
        random_streams=RandomStreams(101),
        round_id="round-stable",
    )
    second = arbitrate_proposals(
        proposals,
        snapshot=SNAPSHOT,
        random_streams=RandomStreams(101),
        round_id="round-stable",
    )

    assert first == second
    audit = first.audits[0]
    assert audit.semantic_stream_key == (
        "arbitration",
        "round-stable",
        audit.conflict_id,
    )
    assert audit.sampled_value is not None
    assert audit.chosen_result is not None


@pytest.mark.unit
def test_different_seed_may_choose_different_valid_candidate() -> None:
    proposals = (
        _proposal("a", dependencies=("b",)),
        _proposal("b", dependencies=("a",)),
    )

    chosen = {
        arbitrate_proposals(
            proposals,
            snapshot=SNAPSHOT,
            random_streams=RandomStreams(seed),
            round_id="round-variable",
        ).audits[0].chosen_result
        for seed in range(1, 65)
    }

    assert chosen == {OperationId("a"), OperationId("b")}


@pytest.mark.unit
def test_shuffled_proposal_order_is_stable_for_same_entropy() -> None:
    proposals = [
        _proposal("a", dependencies=("c",)),
        _proposal("b", dependencies=("a",)),
        _proposal("c", dependencies=("b",)),
    ]
    baseline = arbitrate_proposals(
        proposals,
        snapshot=SNAPSHOT,
        random_streams=RandomStreams(31337),
        round_id="shuffle-round",
    )

    shuffled = list(proposals)
    random.Random(99).shuffle(shuffled)
    replay = arbitrate_proposals(
        shuffled,
        snapshot=SNAPSHOT,
        random_streams=RandomStreams(31337),
        round_id="shuffle-round",
    )

    assert replay == baseline


@pytest.mark.unit
def test_conflicting_exclusive_claims_cannot_both_be_accepted() -> None:
    object_ref = StateRef(
        _actor("unique-object"),
        SubresourceKey.of("inventory", "owner"),
    )
    proposals = (
        _proposal("a", exclusive_claims=frozenset({object_ref})),
        _proposal("b", exclusive_claims=frozenset({object_ref})),
    )

    result = arbitrate_proposals(
        proposals,
        snapshot=SNAPSHOT,
        random_streams=RandomStreams(23),
        round_id="exclusive-round",
    )

    accepted = [
        outcome
        for outcome in result.outcomes
        if outcome.status is ProposalTerminalStatus.ACCEPTED
    ]
    assert len(accepted) == 1
    assert result.audits[0].conflict_id.startswith("exclusive:")


@pytest.mark.unit
def test_compatible_aggregatable_claims_remain_eligible_together() -> None:
    target = StateRef(ComponentRef("terrain", "dam_integrity"))
    claim = WriteClaim(target, WriteClass.AGGREGATABLE)
    proposals = (
        _proposal("a", write_set=(claim,)),
        _proposal("b", write_set=(claim,)),
    )

    result = arbitrate_proposals(
        proposals,
        snapshot=SNAPSHOT,
        random_streams=RandomStreams(29),
        round_id="aggregate-round",
    )

    assert {
        outcome.status for outcome in result.outcomes
    } == {ProposalTerminalStatus.ACCEPTED}
    assert result.resolution_order == (OperationId("a"), OperationId("b"))
    assert result.audits == ()


@pytest.mark.unit
def test_rule_governed_write_requires_explicit_rule() -> None:
    target = StateRef(ComponentRef("weather", "wind_speed"))
    with pytest.raises(ValueError, match="require a rule"):
        WriteClaim(target, WriteClass.RULE_GOVERNED)


@st.composite
def bounded_graphs(draw):
    size = draw(st.integers(min_value=1, max_value=12))
    names = tuple(f"p{index}" for index in range(size))
    edges = draw(
        st.sets(
            st.tuples(
                st.integers(min_value=0, max_value=size - 1),
                st.integers(min_value=0, max_value=size - 1),
            ),
            max_size=min(size * size, 48),
        )
    )
    dependencies = {name: set() for name in names}
    for dependent, dependency in edges:
        dependencies[names[dependent]].add(names[dependency])
    return tuple(
        _proposal(name, dependencies=tuple(sorted(dependencies[name])))
        for name in names
    )


@pytest.mark.unit
@settings(max_examples=100, deadline=None)
@given(bounded_graphs())
def test_bounded_dependency_graphs_always_terminate_without_waiting(
    proposals: tuple[ActionProposal, ...],
) -> None:
    result = arbitrate_proposals(
        proposals,
        snapshot=SNAPSHOT,
        random_streams=RandomStreams(41),
        round_id="property-round",
    )

    assert len(result.outcomes) == len(proposals)
    assert {outcome.operation_id for outcome in result.outcomes} == {
        proposal.operation_id for proposal in proposals
    }
    assert all(
        outcome.status
        in {
            ProposalTerminalStatus.ACCEPTED,
            ProposalTerminalStatus.REJECTED,
            ProposalTerminalStatus.DEFERRED,
            ProposalTerminalStatus.CANCELED,
            ProposalTerminalStatus.FAILED,
            ProposalTerminalStatus.OVERFLOWED,
        }
        for outcome in result.outcomes
    )
