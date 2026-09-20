from __future__ import annotations

from dataclasses import replace

import pytest

from dynamic_story_scaffold.core import (
    DisturbanceSet,
    Effect,
    EffectStacking,
    EntityKind,
    EntityRef,
    OperationId,
    WorkBudget,
    WorldEvent,
    WorldSnapshot,
)
from dynamic_story_scaffold.effect_runtime import apply_effects
from dynamic_story_scaffold.events import (
    CausalGenerationQueue,
    GenerationItem,
    GenerationStatus,
)


SNAPSHOT = WorldSnapshot.from_data({"tick": 0, "elapsed_seconds": 0.0, "actors": {}})


def actor(name: str) -> EntityRef:
    return EntityRef(EntityKind.ACTOR, name)


@pytest.mark.unit
def test_event_effect_event_feedback_loop_is_bounded() -> None:
    source = actor("source")
    target = actor("target")
    initial = GenerationItem(
        operation_id=OperationId("event-a-root"),
        payload=WorldEvent("event-a", source=source, target=target),
    )

    def on_event(item, snapshot):
        return DisturbanceSet(
            effects=(
                Effect(
                    id="effect-b",
                    kind="effect-b",
                    source=source,
                    target=target,
                    stacking=EffectStacking.REFRESH,
                ),
            )
        )

    def on_effect(item, snapshot):
        return DisturbanceSet(
            events=(WorldEvent("event-a", source=source, target=target),)
        )

    result = CausalGenerationQueue(
        WorkBudget(max_causal_depth=3, max_events_per_round=8, max_deferrals=4)
    ).process(
        (initial,),
        snapshot=SNAPSHOT,
        event_handler=on_event,
        effect_handler=on_effect,
    )

    assert result.deferred
    assert any(
        audit.status is GenerationStatus.DEFERRED
        and audit.detail == "causal depth budget exceeded"
        for audit in result.audits
    )


@pytest.mark.unit
def test_self_refreshing_effect_stays_single_and_refreshes_simulation_time() -> None:
    source = actor("source")
    target = actor("target")
    effect = Effect(
        id="ward-1",
        kind="ward",
        source=source,
        target=target,
        magnitude=1.0,
        duration_seconds=5.0,
        stacking=EffectStacking.REFRESH,
    )

    first = apply_effects((), (effect,), now_seconds=10.0)
    second = apply_effects(first, (replace(effect, magnitude=2.0),), now_seconds=12.0)

    assert len(second) == 1
    assert second[0].magnitude == 2.0
    assert second[0].data["_applied_at_seconds"] == 12.0


@pytest.mark.unit
def test_event_and_deferral_budget_exhaustion_is_recorded() -> None:
    items = tuple(
        GenerationItem(
            operation_id=OperationId(f"event-{index}"),
            payload=WorldEvent(f"event-{index}"),
        )
        for index in range(3)
    )

    result = CausalGenerationQueue(
        WorkBudget(max_events_per_round=1, max_deferrals=1)
    ).process(items, snapshot=SNAPSHOT)

    statuses = [audit.status for audit in result.audits]
    assert statuses.count(GenerationStatus.APPLIED) == 1
    assert statuses.count(GenerationStatus.DEFERRED) == 1
    assert statuses.count(GenerationStatus.OVERFLOWED) == 1
    assert len(result.deferred) == 1


@pytest.mark.unit
def test_duplicate_operation_id_is_not_applied_twice() -> None:
    operation_id = OperationId("same-operation")
    first = GenerationItem(operation_id, WorldEvent("first"))
    second = GenerationItem(operation_id, WorldEvent("second"))

    result = CausalGenerationQueue(WorkBudget()).process(
        (first, second),
        snapshot=SNAPSHOT,
    )

    assert tuple(event.name for event in result.disturbances.events) == ("first",)
    assert [audit.status for audit in result.audits] == [
        GenerationStatus.APPLIED,
        GenerationStatus.DUPLICATE,
    ]
