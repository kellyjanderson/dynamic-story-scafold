from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable, Iterable

from .core import DisturbanceSet, Effect, OperationId, WorkBudget, WorldEvent, WorldSnapshot


class GenerationKind(StrEnum):
    EVENT = "event"
    EFFECT = "effect"


class GenerationStatus(StrEnum):
    APPLIED = "applied"
    DUPLICATE = "duplicate"
    OVERFLOWED = "overflowed"
    DEFERRED = "deferred"


@dataclass(frozen=True, slots=True)
class GenerationItem:
    operation_id: OperationId
    payload: WorldEvent | Effect
    causal_parent: OperationId | None = None
    causal_depth: int = 0
    generation: int = 0

    def __post_init__(self) -> None:
        if self.causal_depth < 0:
            raise ValueError("causal depth must be non-negative")
        if self.generation < 0:
            raise ValueError("generation must be non-negative")

    @property
    def kind(self) -> GenerationKind:
        return GenerationKind.EVENT if isinstance(self.payload, WorldEvent) else GenerationKind.EFFECT


@dataclass(frozen=True, slots=True)
class GenerationAudit:
    operation_id: OperationId
    kind: GenerationKind
    status: GenerationStatus
    causal_parent: OperationId | None
    causal_depth: int
    generation: int
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class GenerationResult:
    disturbances: DisturbanceSet
    audits: tuple[GenerationAudit, ...]
    deferred: tuple[GenerationItem, ...]


GenerationHandler = Callable[[GenerationItem, WorldSnapshot], DisturbanceSet]


class CausalGenerationQueue:
    """Bounded FIFO event/effect propagation with idempotent operation IDs."""

    def __init__(self, budget: WorkBudget) -> None:
        self.budget = budget

    def process(
        self,
        initial: Iterable[GenerationItem],
        *,
        snapshot: WorldSnapshot,
        event_handler: GenerationHandler | None = None,
        effect_handler: GenerationHandler | None = None,
    ) -> GenerationResult:
        queue = deque(initial)
        seen: set[OperationId] = set()
        audits: list[GenerationAudit] = []
        deferred: list[GenerationItem] = []
        forcing = []
        events: list[WorldEvent] = []
        effects: list[Effect] = []
        event_count = 0
        deferral_count = 0

        while queue:
            item = queue.popleft()
            if item.operation_id in seen:
                audits.append(self._audit(item, GenerationStatus.DUPLICATE, "duplicate operation id"))
                continue
            seen.add(item.operation_id)

            if item.causal_depth > self.budget.max_causal_depth:
                deferral_count = self._defer(
                    item,
                    "causal depth budget exceeded",
                    audits,
                    deferred,
                    deferral_count,
                )
                continue

            if item.kind is GenerationKind.EVENT:
                if event_count >= self.budget.max_events_per_round:
                    deferral_count = self._defer(
                        item,
                        "event budget exceeded",
                        audits,
                        deferred,
                        deferral_count,
                    )
                    continue
                event_count += 1
                events.append(item.payload)
                handler = event_handler
            else:
                effects.append(item.payload)
                handler = effect_handler

            audits.append(self._audit(item, GenerationStatus.APPLIED))
            if handler is None:
                continue

            generated = handler(item, snapshot)
            forcing.extend(generated.forcing)
            children: list[tuple[GenerationKind, WorldEvent | Effect]] = []
            children.extend((GenerationKind.EVENT, event) for event in generated.events)
            children.extend((GenerationKind.EFFECT, effect) for effect in generated.effects)
            for index, (kind, payload) in enumerate(children):
                queue.append(
                    GenerationItem(
                        operation_id=self._child_operation_id(item, kind, index, payload),
                        payload=payload,
                        causal_parent=item.operation_id,
                        causal_depth=item.causal_depth + 1,
                        generation=item.generation + 1,
                    )
                )

        return GenerationResult(
            disturbances=DisturbanceSet(
                forcing=tuple(forcing),
                events=tuple(events),
                effects=tuple(effects),
            ),
            audits=tuple(audits),
            deferred=tuple(deferred),
        )

    def _defer(
        self,
        item: GenerationItem,
        detail: str,
        audits: list[GenerationAudit],
        deferred: list[GenerationItem],
        deferral_count: int,
    ) -> int:
        if deferral_count < self.budget.max_deferrals:
            deferred.append(item)
            audits.append(self._audit(item, GenerationStatus.DEFERRED, detail))
            return deferral_count + 1
        audits.append(
            self._audit(
                item,
                GenerationStatus.OVERFLOWED,
                f"{detail}; deferral budget exceeded",
            )
        )
        return deferral_count

    @staticmethod
    def _audit(
        item: GenerationItem,
        status: GenerationStatus,
        detail: str | None = None,
    ) -> GenerationAudit:
        return GenerationAudit(
            operation_id=item.operation_id,
            kind=item.kind,
            status=status,
            causal_parent=item.causal_parent,
            causal_depth=item.causal_depth,
            generation=item.generation,
            detail=detail,
        )

    @staticmethod
    def _child_operation_id(
        parent: GenerationItem,
        kind: GenerationKind,
        index: int,
        payload: WorldEvent | Effect,
    ) -> OperationId:
        if isinstance(payload, WorldEvent) and payload.operation_id is not None:
            return payload.operation_id
        identity = payload.name if isinstance(payload, WorldEvent) else payload.id
        return OperationId(f"{parent.operation_id}:{kind.value}:{index}:{identity}")


def generation_items_for_disturbances(
    disturbances: DisturbanceSet,
    *,
    parent_operation_id: OperationId,
    causal_depth: int,
) -> tuple[GenerationItem, ...]:
    """Wrap resolver consequences in stable queue operation identities."""

    items: list[GenerationItem] = []
    for index, event in enumerate(disturbances.events):
        operation_id = event.operation_id or OperationId(
            f"{parent_operation_id}:event:{index}:{event.name}"
        )
        items.append(
            GenerationItem(
                operation_id=operation_id,
                payload=event,
                causal_parent=parent_operation_id,
                causal_depth=max(causal_depth, event.causal_depth),
                generation=event.generation,
            )
        )
    for index, effect in enumerate(disturbances.effects):
        items.append(
            GenerationItem(
                operation_id=OperationId(
                    f"{parent_operation_id}:effect:{index}:{effect.id}"
                ),
                payload=effect,
                causal_parent=parent_operation_id,
                causal_depth=causal_depth,
                generation=0,
            )
        )
    return tuple(items)
