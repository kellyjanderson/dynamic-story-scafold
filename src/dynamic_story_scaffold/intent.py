from __future__ import annotations

from collections.abc import Mapping, Sequence
from random import Random
from typing import Any

from .actions import ActionCandidate, generate_action_candidates
from .core import (
    ActionIntent,
    EntityRef,
    Observation,
    ScoreBreakdown,
    ScoredOption,
    ScoreTerm,
    WorldSnapshot,
)
from .schema import ActorDefinition, SceneDefinition


class UtilityIntentProvider:
    """Rules-based, inspectable utility intent selection.

    Human-readable priority/quirk prose is deliberately ignored. Machine
    behavior is driven by explicit authored semantic weights and ability tags.
    """

    def __init__(
        self,
        scene: SceneDefinition,
        *,
        decision_jitter: float = 0.05,
    ) -> None:
        if decision_jitter < 0:
            raise ValueError("decision_jitter must be non-negative")
        self.scene = scene
        self.decision_jitter = decision_jitter

    def choose_intent(
        self,
        *,
        actor: EntityRef,
        world: WorldSnapshot,
        observations: Sequence[Observation],
        rng: Random,
    ) -> ActionIntent:
        definition = self.scene.actor(actor.id)
        candidates = generate_action_candidates(
            scene=self.scene,
            actor=actor,
            world=world,
            observations=observations,
        )
        scored = tuple(
            ScoredOption(
                candidate,
                self._score(
                    definition=definition,
                    candidate=candidate,
                    world=world,
                    observations=observations,
                    rng=rng,
                ),
            )
            for candidate in candidates
        )

        selected = max(scored, key=lambda item: (item.total, item.value.key))
        candidate = selected.value
        audit = tuple(
            {
                "candidate": option.value.key,
                "action": option.value.action,
                "ability": option.value.ability,
                "target": (
                    None if option.value.target is None else str(option.value.target)
                ),
                "total": option.total,
                "deterministic_total": option.score.deterministic_total,
                "jitter": option.score.jitter,
                "terms": tuple(
                    {
                        "name": term.name,
                        "value": term.value,
                        "weight": term.weight,
                        "contribution": term.contribution,
                    }
                    for term in option.score.terms
                ),
            }
            for option in scored
        )

        return ActionIntent(
            actor=actor,
            action=candidate.action,
            target=candidate.target,
            ability=candidate.ability,
            destination=candidate.destination,
            risk_tolerance=definition.risk_tolerance,
            score=selected.score,
            data={
                "selection_policy": "max_utility",
                "selection_sample": None,
                "candidate_scores": audit,
            },
        )

    def _score(
        self,
        *,
        definition: ActorDefinition,
        candidate: ActionCandidate,
        world: WorldSnapshot,
        observations: Sequence[Observation],
        rng: Random,
    ) -> ScoreBreakdown:
        positional = _positional_suitability(candidate, observations)
        recent_penalty = _recent_action_penalty(
            world=world,
            actor_id=definition.id,
            candidate=candidate,
        )
        terms = (
            ScoreTerm(
                "objective_relevance",
                _tag_relevance(self.scene.setting.objective_weights, candidate.tags),
            ),
            ScoreTerm(
                "motivation_relevance",
                _tag_relevance(definition.motivations, candidate.tags),
            ),
            ScoreTerm(
                "priority_relevance",
                _tag_relevance(definition.priority_weights, candidate.tags),
            ),
            ScoreTerm("role_affinity", candidate.role_affinity),
            ScoreTerm("positional_suitability", positional),
            ScoreTerm("expected_effect", candidate.expected_effect),
            ScoreTerm("resource_cost", -candidate.resource_cost),
            ScoreTerm(
                "risk",
                -(candidate.risk * (1.0 - definition.risk_tolerance)),
            ),
            ScoreTerm("recent_action_repetition", recent_penalty),
            ScoreTerm(
                "quirk_modifiers",
                _tag_relevance(definition.quirk_weights, candidate.tags),
            ),
        )
        jitter = (
            0.0
            if self.decision_jitter == 0
            else rng.uniform(-self.decision_jitter, self.decision_jitter)
        )
        return ScoreBreakdown(
            terms=terms,
            jitter=jitter,
            metadata={
                "candidate": candidate.key,
                "policy": "max_utility",
            },
        )


def _tag_relevance(weights: Mapping[str, float], tags: Sequence[str]) -> float:
    if not tags:
        return 0.0
    matches = [float(weights[tag]) for tag in tags if tag in weights]
    if not matches:
        return 0.0
    return sum(matches) / len(matches)


def _positional_suitability(
    candidate: ActionCandidate,
    observations: Sequence[Observation],
) -> float:
    if candidate.target is None or candidate.preferred_range is None:
        return 0.0

    distance_class: str | None = None
    for observation in observations:
        if observation.subject != candidate.target or observation.fact != "actor.presence":
            continue
        if isinstance(observation.value, Mapping):
            raw = observation.value.get("distance_class")
            distance_class = None if raw is None else str(raw)
        break

    if distance_class is None:
        return 0.0

    preferred = candidate.preferred_range.lower()
    if preferred in {"close", "melee", "near"}:
        return 0.35 if distance_class == "same_zone" else -0.20
    if preferred in {"mid", "medium"}:
        return 0.25 if distance_class == "adjacent_zone" else 0.10
    if preferred in {"long", "ranged", "far"}:
        return 0.30 if distance_class == "adjacent_zone" else -0.10
    if preferred in {"flexible", "any"}:
        return 0.15
    return 0.0


def _recent_action_penalty(
    *,
    world: WorldSnapshot,
    actor_id: str,
    candidate: ActionCandidate,
) -> float:
    actors = world.to_data().get("actors", {})
    if not isinstance(actors, Mapping):
        return 0.0
    actor = actors.get(actor_id)
    if not isinstance(actor, Mapping):
        return 0.0
    values = actor.get("values", {})
    if not isinstance(values, Mapping):
        return 0.0
    recent = values.get("recent_actions", ())
    if not isinstance(recent, (list, tuple)):
        return 0.0

    identity = candidate.ability or candidate.action
    repetitions = sum(1 for item in recent if str(item) == identity)
    return -min(0.75, repetitions * 0.25)
