from __future__ import annotations

import hashlib
from collections.abc import Collection, Mapping
from random import Random
from typing import Any

from .core import (
    ComponentRef,
    EntityKind,
    EntityRef,
    KnowledgeLevel,
    Observation,
    RandomStreams,
    WorldSnapshot,
)


class BaselinePerceptionProvider:
    """Rules-based semantic-zone perception for the MVP.

    The provider is deliberately conservative about actor truth: observers see
    another actor's presence, obvious posture, and a coarse injury category,
    never the actor's private resources, relationships, inventory, arbitrary
    scenario values, or exact health.

    Zone adjacency is policy supplied by the caller.  This keeps map knowledge
    out of shared core and avoids scene- or species-specific branches.
    """

    def __init__(
        self,
        *,
        zone_adjacency: Mapping[str, Collection[str]] | None = None,
        environment_components: Collection[str] | None = None,
    ) -> None:
        self._zone_adjacency = {
            str(zone): frozenset(str(item) for item in adjacent)
            for zone, adjacent in (zone_adjacency or {}).items()
        }
        self._environment_components = (
            None
            if environment_components is None
            else frozenset(str(item) for item in environment_components)
        )

    def perceive(
        self,
        *,
        actor: EntityRef,
        world: WorldSnapshot,
        rng: Random,
    ) -> tuple[Observation, ...]:
        if actor.kind is not EntityKind.ACTOR:
            raise ValueError("baseline perception requires an actor observer")

        data = world.to_data()
        actors = _mapping(data.get("actors", {}))
        if actor.id not in actors:
            raise KeyError(actor.id)

        observer_data = _mapping(actors[actor.id])
        observer_zone = _zone_of(observer_data)
        streams = _child_streams(rng)
        observations: list[Observation] = []

        observations.extend(self._self_observations(actor, observer_data))

        for subject_id in sorted(str(item) for item in actors if str(item) != actor.id):
            subject_data = _mapping(actors[subject_id])
            subject_zone = _zone_of(subject_data)
            if not self._visible(observer_zone, subject_zone):
                continue

            subject = EntityRef(EntityKind.ACTOR, subject_id)
            distance_class = "same_zone" if observer_zone == subject_zone else "adjacent_zone"
            presence_confidence = self._confidence(
                streams,
                subject_id=subject_id,
                fact_key="actor.presence",
                same_zone=distance_class == "same_zone",
            )
            observations.append(
                Observation(
                    observer=actor,
                    subject=subject,
                    fact="actor.presence",
                    confidence=presence_confidence,
                    value={"zone": subject_zone, "distance_class": distance_class},
                    certainty=_certainty_for(presence_confidence),
                )
            )

            posture = subject_data.get("posture")
            if posture is not None:
                confidence = self._confidence(
                    streams,
                    subject_id=subject_id,
                    fact_key="actor.posture",
                    same_zone=distance_class == "same_zone",
                )
                observations.append(
                    Observation(
                        observer=actor,
                        subject=subject,
                        fact="actor.posture",
                        confidence=confidence,
                        value=str(posture),
                        certainty=_certainty_for(confidence),
                    )
                )

            health = _optional_float(subject_data.get("health"))
            if health is not None and health < 0.9:
                confidence = self._confidence(
                    streams,
                    subject_id=subject_id,
                    fact_key="actor.injury",
                    same_zone=distance_class == "same_zone",
                )
                observations.append(
                    Observation(
                        observer=actor,
                        subject=subject,
                        fact="actor.injury",
                        confidence=confidence,
                        value={"severity": _injury_category(health)},
                        certainty=_certainty_for(confidence),
                    )
                )

        observations.extend(self._environment_observations(actor, data))
        observations.extend(self._recent_event_observations(actor, data))
        return tuple(observations)

    def _self_observations(
        self,
        actor: EntityRef,
        data: Mapping[str, Any],
    ) -> tuple[Observation, ...]:
        observations: list[Observation] = []
        position = data.get("position")
        if isinstance(position, Mapping):
            observations.append(
                Observation(
                    observer=actor,
                    subject=actor,
                    fact="self.position",
                    confidence=1.0,
                    value={
                        "zone": position.get("zone"),
                        "x": position.get("x"),
                        "y": position.get("y"),
                        "z": position.get("z"),
                    },
                )
            )

        posture = data.get("posture")
        if posture is not None:
            observations.append(
                Observation(
                    observer=actor,
                    subject=actor,
                    fact="self.posture",
                    confidence=1.0,
                    value=str(posture),
                )
            )

        for fact, key in (("self.health", "health"), ("self.fatigue", "fatigue")):
            value = _optional_float(data.get(key))
            if value is not None:
                observations.append(
                    Observation(
                        observer=actor,
                        subject=actor,
                        fact=fact,
                        confidence=1.0,
                        value=value,
                    )
                )

        return tuple(observations)

    def _environment_observations(
        self,
        actor: EntityRef,
        data: Mapping[str, Any],
    ) -> tuple[Observation, ...]:
        observations: list[Observation] = []
        environment = _mapping(data.get("environment", {}))
        for element_name in sorted(str(item) for item in environment):
            components = _mapping(environment[element_name])
            for component_name in sorted(str(item) for item in components):
                reference = ComponentRef(element_name, component_name)
                if (
                    self._environment_components is not None
                    and reference.path not in self._environment_components
                ):
                    continue
                component_data = _mapping(components[component_name])
                if "value" not in component_data:
                    continue
                observations.append(
                    Observation(
                        observer=actor,
                        subject=reference,
                        fact="environment.value",
                        confidence=1.0,
                        value={"value": component_data["value"]},
                    )
                )
        return tuple(observations)

    def _recent_event_observations(
        self,
        actor: EntityRef,
        data: Mapping[str, Any],
    ) -> tuple[Observation, ...]:
        raw_events = data.get("recent_events", ())
        if not isinstance(raw_events, (list, tuple)):
            return ()

        world_subject = EntityRef(EntityKind.ENVIRONMENT, "world")
        observations: list[Observation] = []
        for raw in raw_events:
            if isinstance(raw, str):
                name = raw
                audible = True
                explicit = True
            elif isinstance(raw, Mapping):
                name = str(raw.get("name", ""))
                audible = bool(raw.get("audible", False))
                explicit = bool(raw.get("explicit", False))
            else:
                continue

            if not name or not (audible or explicit):
                continue
            observations.append(
                Observation(
                    observer=actor,
                    subject=world_subject,
                    fact="event.recent",
                    confidence=1.0,
                    value={
                        "name": name,
                        "audible": audible,
                        "explicit": explicit,
                    },
                )
            )
        return tuple(observations)

    def _visible(self, observer_zone: str | None, subject_zone: str | None) -> bool:
        if observer_zone is None or subject_zone is None:
            return False
        if observer_zone == subject_zone:
            return True
        return (
            subject_zone in self._zone_adjacency.get(observer_zone, ())
            or observer_zone in self._zone_adjacency.get(subject_zone, ())
        )

    @staticmethod
    def _confidence(
        streams: RandomStreams,
        *,
        subject_id: str,
        fact_key: str,
        same_zone: bool,
    ) -> float:
        sample = streams.stream(subject_id, fact_key).random()
        if same_zone:
            return 0.9 + (sample * 0.1)
        return 0.55 + (sample * 0.3)


def _child_streams(rng: Random) -> RandomStreams:
    """Derive stable fact substreams without advancing the caller's RNG."""

    state_bytes = repr(rng.getstate()).encode("utf-8")
    digest = hashlib.blake2b(state_bytes, digest_size=16).digest()
    return RandomStreams(int.from_bytes(digest, "big"))


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("expected mapping in world snapshot")
    return value


def _zone_of(actor_data: Mapping[str, Any]) -> str | None:
    position = actor_data.get("position")
    if not isinstance(position, Mapping):
        return None
    zone = position.get("zone")
    return None if zone is None else str(zone)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _injury_category(health: float) -> str:
    if health < 0.35:
        return "severe"
    if health < 0.7:
        return "moderate"
    return "minor"


def _certainty_for(confidence: float) -> KnowledgeLevel:
    if confidence >= 0.8:
        return KnowledgeLevel.KNOWN
    if confidence >= 0.65:
        return KnowledgeLevel.INFERRED
    return KnowledgeLevel.SUSPECTED
