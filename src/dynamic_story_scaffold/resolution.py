from __future__ import annotations

from collections.abc import Mapping
from random import Random
from typing import Any

from .core import (
    ActionIntent,
    ActionResolution,
    ActorUpdate,
    ComponentRef,
    DisturbanceSet,
    Effect,
    EffectStacking,
    EntityKind,
    EntityRef,
    Outcome,
    TimeSpan,
    WorldEvent,
    WorldForcing,
    WorldSnapshot,
)
from .schema import AbilityDefinition, CharacterDefinition, RoleDefinition, SceneDefinition


_OUTCOME_MULTIPLIER: dict[Outcome, float] = {
    Outcome.CRITICAL_FAILURE: 0.0,
    Outcome.FAILURE: 0.0,
    Outcome.PARTIAL: 0.5,
    Outcome.SUCCESS: 1.0,
    Outcome.STRONG_SUCCESS: 1.25,
    Outcome.CRITICAL_SUCCESS: 1.5,
}


class RulesActionResolver:
    """Mechanics-first resolver that returns typed proposals without mutation."""

    def __init__(self, scene: SceneDefinition) -> None:
        self.scene = scene

    def resolve(
        self,
        *,
        intent: ActionIntent,
        world: WorldSnapshot,
        rng: Random,
    ) -> ActionResolution:
        actor = self.scene.actor(intent.actor.id)
        role, ability = self._role_and_ability(actor, intent.ability)
        mechanics = {} if ability is None else ability.mechanics

        sample = rng.random()
        base_name, base_capability = self._base_capability(
            actor=actor,
            intent=intent,
            mechanics=mechanics,
        )
        modifiers = self._modifiers(
            intent=intent,
            role=role,
            ability=ability,
            mechanics=mechanics,
        )
        difficulty = self._difficulty(intent=intent, world=world, mechanics=mechanics)
        total = sample + base_capability + sum(value for _, value in modifiers)
        margin = total - difficulty
        outcome = _degree_of_success(margin)

        actor_updates, disturbances = self._consequences(
            intent=intent,
            world=world,
            mechanics=mechanics,
            outcome=outcome,
        )

        audit = {
            "sample": sample,
            "base_capability": {
                "name": base_name,
                "value": base_capability,
            },
            "modifiers": tuple(
                {"name": name, "value": value} for name, value in modifiers
            ),
            "difficulty": difficulty,
            "total": total,
            "margin": margin,
            "outcome": outcome.value,
            "actor": str(intent.actor),
            "target": None if intent.target is None else str(intent.target),
            "action": intent.action,
            "ability": intent.ability,
            "consequences": {
                "actor_updates": len(actor_updates),
                "forcing": len(disturbances.forcing),
                "events": len(disturbances.events),
                "effects": len(disturbances.effects),
            },
        }
        explanation = (
            f"sample {sample:.6f} + {base_name} {base_capability:.3f} "
            f"+ modifiers {sum(value for _, value in modifiers):.3f} "
            f"= {total:.6f} vs difficulty {difficulty:.3f}; "
            f"margin {margin:.6f} => {outcome.value}"
        )
        return ActionResolution(
            intent=intent,
            outcome=outcome,
            roll=sample,
            total=total,
            difficulty=difficulty,
            disturbances=disturbances,
            actor_updates=actor_updates,
            explanation=explanation,
            audit=audit,
            span=TimeSpan.instant(float(world.to_data().get("elapsed_seconds", 0.0))),
        )

    def _role_and_ability(
        self,
        actor: object,
        ability_name: str | None,
    ) -> tuple[RoleDefinition | None, AbilityDefinition | None]:
        if not isinstance(actor, CharacterDefinition):
            return None, None
        role = self.scene.roles[actor.role]
        if ability_name is None:
            return role, None
        for ability in role.abilities:
            if ability.name == ability_name:
                return role, ability
        raise ValueError(
            f"actor {actor.id!r} role {actor.role!r} has no ability {ability_name!r}"
        )

    @staticmethod
    def _base_capability(
        *,
        actor: Any,
        intent: ActionIntent,
        mechanics: Mapping[str, Any],
    ) -> tuple[str, float]:
        explicit = mechanics.get("base_capability")
        if isinstance(explicit, (int, float)):
            return "authored", float(explicit)

        requested = mechanics.get("capability")
        if requested is not None:
            name = str(requested)
        else:
            name = {
                "attack": "strength",
                "maneuver": "agility",
                "move": "agility",
                "defend": "endurance",
                "reaction": "endurance",
                "spell": "endurance",
                "control": "endurance",
                "observe": "agility",
            }.get(intent.action, "endurance")

        physical = actor.physical
        if name in physical:
            return name, float(physical[name])
        if physical:
            values = tuple(float(value) for value in physical.values())
            return "physical_average", sum(values) / len(values)
        return "baseline", 0.5

    @staticmethod
    def _modifiers(
        *,
        intent: ActionIntent,
        role: RoleDefinition | None,
        ability: AbilityDefinition | None,
        mechanics: Mapping[str, Any],
    ) -> tuple[tuple[str, float], ...]:
        result: list[tuple[str, float]] = []

        if ability is not None:
            for name, value in sorted(ability.modifiers.items()):
                result.append((f"ability:{name}", _scaled_modifier(float(value))))

        if role is not None:
            requested = mechanics.get("modifier")
            domain = mechanics.get("domain")
            keys = [str(item) for item in (requested, domain) if item is not None]
            if not keys and intent.action in role.modifiers:
                keys.append(intent.action)
            for key in dict.fromkeys(keys):
                if key in role.modifiers:
                    result.append(
                        (f"role:{key}", _scaled_modifier(float(role.modifiers[key])))
                    )

        situational = intent.data.get("situational_modifiers", {})
        if isinstance(situational, Mapping):
            for name, value in sorted(situational.items(), key=lambda item: str(item[0])):
                result.append((f"situational:{name}", float(value)))

        return tuple(result)

    @staticmethod
    def _difficulty(
        *,
        intent: ActionIntent,
        world: WorldSnapshot,
        mechanics: Mapping[str, Any],
    ) -> float:
        if "difficulty" in intent.data:
            return float(intent.data["difficulty"])
        if "difficulty" in mechanics:
            return float(mechanics["difficulty"])

        if isinstance(intent.target, EntityRef) and intent.target.kind is EntityKind.ACTOR:
            actors = world.to_data().get("actors", {})
            if isinstance(actors, Mapping):
                target = actors.get(intent.target.id)
                if isinstance(target, Mapping):
                    health = float(target.get("health", 1.0))
                    fatigue = float(target.get("fatigue", 0.0))
                    return 0.7 + (0.2 * health) - (0.1 * fatigue)
        if isinstance(intent.target, EntityRef) and intent.target.kind is EntityKind.TERRAIN:
            return 0.9
        return 0.75

    def _consequences(
        self,
        *,
        intent: ActionIntent,
        world: WorldSnapshot,
        mechanics: Mapping[str, Any],
        outcome: Outcome,
    ) -> tuple[tuple[ActorUpdate, ...], DisturbanceSet]:
        multiplier = _OUTCOME_MULTIPLIER[outcome]
        updates: list[ActorUpdate] = []
        forcing: list[WorldForcing] = []
        events: list[WorldEvent] = []
        effects: list[Effect] = []

        resource_delta = _resource_delta(mechanics)
        if resource_delta:
            updates.append(ActorUpdate(actor=intent.actor, resource_delta=resource_delta))

        authored = mechanics.get("consequences")
        if isinstance(authored, Mapping):
            selected = authored.get(outcome.value, authored.get("success" if multiplier else "failure"))
            if isinstance(selected, Mapping):
                self._apply_authored_consequences(
                    intent=intent,
                    consequence=selected,
                    multiplier=multiplier,
                    updates=updates,
                    forcing=forcing,
                    events=events,
                    effects=effects,
                )

        if multiplier > 0.0 and not authored:
            self._apply_generic_consequences(
                intent=intent,
                world=world,
                mechanics=mechanics,
                multiplier=multiplier,
                updates=updates,
                forcing=forcing,
                events=events,
                effects=effects,
            )

        return (
            tuple(updates),
            DisturbanceSet(
                forcing=tuple(forcing),
                events=tuple(events),
                effects=tuple(effects),
            ),
        )

    @staticmethod
    def _apply_authored_consequences(
        *,
        intent: ActionIntent,
        consequence: Mapping[str, Any],
        multiplier: float,
        updates: list[ActorUpdate],
        forcing: list[WorldForcing],
        events: list[WorldEvent],
        effects: list[Effect],
    ) -> None:
        actor_spec = consequence.get("actor_update")
        if isinstance(actor_spec, Mapping):
            target = _actor_target(intent, str(actor_spec.get("target", "target")))
            if target is not None:
                updates.append(
                    ActorUpdate(
                        actor=target,
                        health_delta=float(actor_spec.get("health_delta", 0.0)) * multiplier,
                        fatigue_delta=float(actor_spec.get("fatigue_delta", 0.0)) * multiplier,
                        posture=(
                            None
                            if actor_spec.get("posture") is None
                            else str(actor_spec["posture"])
                        ),
                        data=dict(actor_spec.get("data", {}))
                        if isinstance(actor_spec.get("data", {}), Mapping)
                        else {},
                    )
                )

        raw_forcing = consequence.get("forcing", ())
        if isinstance(raw_forcing, Mapping):
            raw_forcing = (raw_forcing,)
        if isinstance(raw_forcing, (list, tuple)):
            for item in raw_forcing:
                if not isinstance(item, Mapping):
                    continue
                forcing.append(
                    WorldForcing(
                        component=ComponentRef.parse(str(item["component"])),
                        amount=float(item.get("amount", 0.0)) * multiplier,
                        source=intent.actor,
                        reason=str(item.get("reason", intent.ability or intent.action)),
                    )
                )

        raw_events = consequence.get("events", ())
        if isinstance(raw_events, str):
            raw_events = (raw_events,)
        if isinstance(raw_events, (list, tuple)):
            for name in raw_events:
                events.append(
                    WorldEvent(
                        name=str(name),
                        source=intent.actor,
                        target=intent.target,
                        data={"action": intent.action, "ability": intent.ability},
                    )
                )

        effect_spec = consequence.get("effect")
        if isinstance(effect_spec, Mapping) and intent.target is not None:
            effects.append(
                Effect(
                    id=str(effect_spec.get("id", f"{intent.actor.id}:{intent.ability or intent.action}")),
                    kind=str(effect_spec.get("kind", intent.ability or intent.action)),
                    source=intent.actor,
                    target=intent.target,
                    magnitude=float(effect_spec.get("magnitude", 1.0)) * multiplier,
                    duration_seconds=(
                        None
                        if effect_spec.get("duration_seconds") is None
                        else float(effect_spec["duration_seconds"])
                    ),
                    stacking=EffectStacking(
                        str(effect_spec.get("stacking", EffectStacking.REPLACE.value))
                    ),
                    tags=tuple(str(item) for item in effect_spec.get("tags", ())),
                )
            )

    def _apply_generic_consequences(
        self,
        *,
        intent: ActionIntent,
        world: WorldSnapshot,
        mechanics: Mapping[str, Any],
        multiplier: float,
        updates: list[ActorUpdate],
        forcing: list[WorldForcing],
        events: list[WorldEvent],
        effects: list[Effect],
    ) -> None:
        if intent.action == "move" and intent.destination is not None:
            updates.append(ActorUpdate(actor=intent.actor, destination=intent.destination))
            return

        if intent.action == "defend":
            updates.append(ActorUpdate(actor=intent.actor, posture="defending"))
            return

        if (
            intent.action == "attack"
            and isinstance(intent.target, EntityRef)
            and intent.target.kind is EntityKind.ACTOR
        ):
            updates.append(
                ActorUpdate(actor=intent.target, health_delta=-0.08 * multiplier)
            )
            return

        if isinstance(intent.target, EntityRef) and intent.target.kind is EntityKind.TERRAIN:
            forcing.append(
                WorldForcing(
                    component=ComponentRef("terrain", "dam_integrity"),
                    amount=-0.08 * multiplier,
                    source=intent.actor,
                    reason=intent.ability or intent.action,
                )
            )
            events.append(
                WorldEvent(
                    "terrain_impacted",
                    source=intent.actor,
                    target=intent.target,
                    data={"ability": intent.ability, "action": intent.action},
                )
            )
            return

        if "force_vector" in mechanics and _component_exists(world, "water.flow_speed"):
            forcing.append(
                WorldForcing(
                    component=ComponentRef("water", "flow_speed"),
                    amount=float(mechanics["force_vector"]) * 0.1 * multiplier,
                    source=intent.actor,
                    reason=intent.ability or intent.action,
                )
            )
            events.append(
                WorldEvent(
                    "flow_forced",
                    source=intent.actor,
                    target=intent.target,
                    data={"ability": intent.ability},
                )
            )

        if mechanics.get("tether") and intent.target is not None:
            effects.append(
                Effect(
                    id=f"{intent.actor.id}:{intent.ability or intent.action}:tether",
                    kind="tethered",
                    source=intent.actor,
                    target=intent.target,
                    magnitude=multiplier,
                    duration_seconds=2.0,
                    stacking=EffectStacking.REFRESH,
                    tags=("control",),
                )
            )

        if mechanics.get("reveals_motion") and intent.target is not None:
            effects.append(
                Effect(
                    id=f"{intent.actor.id}:{intent.ability or intent.action}:reveals-motion",
                    kind="motion_revealed",
                    source=intent.actor,
                    target=intent.target,
                    magnitude=multiplier,
                    duration_seconds=2.0,
                    stacking=EffectStacking.REFRESH,
                    tags=("information",),
                )
            )


def _scaled_modifier(value: float) -> float:
    return value if abs(value) <= 1.0 else value * 0.05


def _degree_of_success(margin: float) -> Outcome:
    if margin <= -0.4:
        return Outcome.CRITICAL_FAILURE
    if margin < 0.0:
        return Outcome.FAILURE
    if margin < 0.2:
        return Outcome.PARTIAL
    if margin < 0.45:
        return Outcome.SUCCESS
    if margin < 0.7:
        return Outcome.STRONG_SUCCESS
    return Outcome.CRITICAL_SUCCESS


def _resource_delta(mechanics: Mapping[str, Any]) -> dict[str, float]:
    raw = mechanics.get("resource_cost", {})
    if not isinstance(raw, Mapping):
        return {}
    return {str(name): -abs(float(value)) for name, value in raw.items()}


def _actor_target(intent: ActionIntent, selector: str) -> EntityRef | None:
    if selector == "self":
        return intent.actor
    if (
        selector == "target"
        and isinstance(intent.target, EntityRef)
        and intent.target.kind is EntityKind.ACTOR
    ):
        return intent.target
    return None


def _component_exists(world: WorldSnapshot, path: str) -> bool:
    ref = ComponentRef.parse(path)
    environment = world.to_data().get("environment", {})
    if not isinstance(environment, Mapping):
        return False
    element = environment.get(ref.element)
    return isinstance(element, Mapping) and ref.component in element
