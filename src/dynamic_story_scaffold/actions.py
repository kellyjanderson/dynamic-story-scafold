from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .core import ComponentRef, EntityKind, EntityRef, Observation, Position, TargetRef, WorldSnapshot
from .schema import AbilityDefinition, ActorDefinition, CharacterDefinition, RoleDefinition, SceneDefinition


@dataclass(frozen=True, slots=True)
class ActionCandidate:
    """Legal, data-derived action considered by the intent policy."""

    action: str
    ability: str | None = None
    target: TargetRef | None = None
    destination: Position | None = None
    tags: tuple[str, ...] = ()
    role_affinity: float = 0.0
    expected_effect: float = 0.0
    resource_cost: float = 0.0
    risk: float = 0.0
    preferred_range: str | None = None

    @property
    def key(self) -> str:
        target = "" if self.target is None else str(self.target)
        ability = "" if self.ability is None else self.ability
        destination = "" if self.destination is None else str(self.destination.zone)
        return "|".join((self.action, ability, target, destination))


BASELINE_ACTIONS: tuple[ActionCandidate, ...] = (
    ActionCandidate(
        action="defend",
        tags=("defend", "protect_party", "self_preservation"),
        role_affinity=0.25,
        expected_effect=0.35,
        risk=0.10,
    ),
    ActionCandidate(
        action="observe",
        tags=("observe", "information", "understand_unknown_threats"),
        role_affinity=0.20,
        expected_effect=0.30,
        risk=0.02,
    ),
)


def generate_action_candidates(
    *,
    scene: SceneDefinition,
    actor: EntityRef,
    world: WorldSnapshot,
    observations: Sequence[Observation],
) -> tuple[ActionCandidate, ...]:
    """Generate legal action candidates without interpreting authored prose."""

    definition = scene.actor(actor.id)
    actor_state = _actor_state(world, actor.id)
    candidates: list[ActionCandidate] = list(BASELINE_ACTIONS)

    candidates.extend(_move_candidates(actor, observations))

    if isinstance(definition, CharacterDefinition):
        role = scene.roles[definition.role]
        for ability in role.abilities:
            candidates.extend(
                _ability_candidates(
                    actor=actor,
                    actor_state=actor_state,
                    observations=observations,
                    role=role,
                    ability=ability,
                )
            )

    legal = tuple(candidate for candidate in candidates if _legal(candidate, actor_state))
    if legal:
        return _deduplicate(legal)

    return (
        ActionCandidate(
            action="no_action",
            tags=("no_action",),
            role_affinity=-1.0,
            expected_effect=0.0,
            risk=0.0,
        ),
    )


def _move_candidates(
    actor: EntityRef,
    observations: Sequence[Observation],
) -> tuple[ActionCandidate, ...]:
    result: list[ActionCandidate] = []
    for observation in observations:
        if (
            observation.fact != "actor.presence"
            or observation.subject == actor
            or not isinstance(observation.subject, EntityRef)
            or not isinstance(observation.value, Mapping)
        ):
            continue
        zone = observation.value.get("zone")
        if not zone:
            continue
        result.append(
            ActionCandidate(
                action="move",
                target=observation.subject,
                destination=Position(zone=str(zone)),
                tags=("move", "positioning"),
                role_affinity=0.20,
                expected_effect=0.25,
                risk=0.15,
            )
        )
    return tuple(result)


def _ability_candidates(
    *,
    actor: EntityRef,
    actor_state: Mapping[str, Any],
    observations: Sequence[Observation],
    role: RoleDefinition,
    ability: AbilityDefinition,
) -> tuple[ActionCandidate, ...]:
    mechanics = ability.mechanics
    targets = _targets_for(ability, actor, observations)
    if targets is None:
        return ()

    cost = _resource_cost(mechanics)
    risk = float(mechanics.get("risk", 0.20))
    expected = float(mechanics.get("expected_effect", 0.60))
    preferred_range = (
        str(mechanics["preferred_range"])
        if mechanics.get("preferred_range") is not None
        else role.preferred_range
    )
    affinity = float(mechanics.get("role_affinity", 0.70))
    tags = tuple(dict.fromkeys((*ability.tags, ability.kind)))

    if not targets:
        targets = (None,)

    return tuple(
        ActionCandidate(
            action=ability.kind,
            ability=ability.name,
            target=target,
            tags=tags,
            role_affinity=affinity,
            expected_effect=expected,
            resource_cost=cost,
            risk=risk,
            preferred_range=preferred_range,
        )
        for target in targets
        if _ability_legal(ability, actor_state, observations)
    )


def _targets_for(
    ability: AbilityDefinition,
    actor: EntityRef,
    observations: Sequence[Observation],
) -> tuple[TargetRef | None, ...] | None:
    targeting = str(ability.mechanics.get("targeting", "none"))
    if targeting in {"none", "self"}:
        return (actor,) if targeting == "self" else (None,)
    if targeting in {"water_volume", "region", "environment", "flow_region"}:
        return (EntityRef(EntityKind.ENVIRONMENT, "world"),)
    if targeting in {"terrain", "terrain_region"}:
        return (EntityRef(EntityKind.TERRAIN, "local"),)

    if targeting in {
        "creature",
        "actor",
        "ally",
        "enemy",
        "object_or_creature",
        "visible_actor",
        "vulnerable_seam",
        "contact",
    }:
        actors = tuple(
            observation.subject
            for observation in observations
            if observation.fact == "actor.presence"
            and isinstance(observation.subject, EntityRef)
            and observation.subject.kind is EntityKind.ACTOR
            and observation.subject != actor
        )
        return actors if actors else None

    # Unknown targeting semantics are not guessed. Authored data must define a
    # supported target class before the ability becomes legal.
    return None


def _ability_legal(
    ability: AbilityDefinition,
    actor_state: Mapping[str, Any],
    observations: Sequence[Observation],
) -> bool:
    mechanics = ability.mechanics
    health = float(actor_state.get("health", 1.0))
    fatigue = float(actor_state.get("fatigue", 0.0))
    if health < float(mechanics.get("min_health", 0.0)):
        return False
    if fatigue > float(mechanics.get("max_fatigue", 1.0)):
        return False

    required_fact = mechanics.get("requires_observation")
    if required_fact is not None and not any(
        item.fact == str(required_fact) for item in observations
    ):
        return False

    resources = actor_state.get("resources", {})
    if not isinstance(resources, Mapping):
        return False
    for name, amount in _resource_costs(mechanics).items():
        if float(resources.get(name, 0.0)) < amount:
            return False
    return True


def _legal(candidate: ActionCandidate, actor_state: Mapping[str, Any]) -> bool:
    if float(actor_state.get("health", 1.0)) <= 0.0:
        return False
    if candidate.destination is not None and actor_state.get("position") is None:
        return False
    return True


def _resource_costs(mechanics: Mapping[str, Any]) -> dict[str, float]:
    raw = mechanics.get("resource_cost", {})
    if raw is None:
        return {}
    if isinstance(raw, Mapping):
        return {str(key): max(0.0, float(value)) for key, value in raw.items()}
    return {}


def _resource_cost(mechanics: Mapping[str, Any]) -> float:
    return min(1.0, sum(_resource_costs(mechanics).values()))


def _actor_state(world: WorldSnapshot, actor_id: str) -> Mapping[str, Any]:
    actors = world.to_data().get("actors", {})
    if not isinstance(actors, Mapping):
        raise ValueError("world snapshot actors must be a mapping")
    data = actors.get(actor_id)
    if not isinstance(data, Mapping):
        raise KeyError(actor_id)
    return data


def _deduplicate(candidates: Sequence[ActionCandidate]) -> tuple[ActionCandidate, ...]:
    by_key = {candidate.key: candidate for candidate in candidates}
    return tuple(by_key[key] for key in sorted(by_key))
