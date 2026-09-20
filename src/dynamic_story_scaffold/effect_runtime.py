from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from .core import Effect, EffectStacking


def _key(effect: Effect) -> tuple[str, str]:
    return (str(effect.target), effect.kind)


def _stamp(effect: Effect, now_seconds: float) -> Effect:
    data = dict(effect.data)
    data["_applied_at_seconds"] = float(now_seconds)
    return replace(effect, data=data)


def effect_expires_at(effect: Effect) -> float | None:
    if effect.duration_seconds is None:
        return None
    applied = effect.data.get("_applied_at_seconds")
    if applied is None:
        return None
    return float(applied) + effect.duration_seconds


def expire_effects(
    effects: Iterable[Effect],
    *,
    now_seconds: float,
) -> tuple[Effect, ...]:
    """Expire effects using simulation time only; no wall-clock scheduling."""

    active = []
    for effect in effects:
        expires_at = effect_expires_at(effect)
        if expires_at is None or expires_at > now_seconds:
            active.append(effect)
    return tuple(active)


def apply_effects(
    existing: Iterable[Effect],
    incoming: Iterable[Effect],
    *,
    now_seconds: float,
) -> tuple[Effect, ...]:
    """Centralized effect stacking by target + effect kind."""

    result = list(expire_effects(existing, now_seconds=now_seconds))
    for raw in incoming:
        effect = _stamp(raw, now_seconds)
        matches = [index for index, current in enumerate(result) if _key(current) == _key(effect)]

        if effect.stacking is EffectStacking.STACK or not matches:
            result.append(effect)
            continue

        if effect.stacking is EffectStacking.REPLACE:
            result = [current for current in result if _key(current) != _key(effect)]
            result.append(effect)
            continue

        if effect.stacking is EffectStacking.REFRESH:
            first = matches[0]
            result[first] = effect
            for index in reversed(matches[1:]):
                del result[index]
            continue

        if effect.stacking is EffectStacking.STRONGEST:
            strongest_index = max(matches, key=lambda index: abs(result[index].magnitude))
            if abs(effect.magnitude) > abs(result[strongest_index].magnitude):
                result[strongest_index] = effect
            for index in reversed(matches):
                if index != strongest_index:
                    del result[index]
            continue

        raise ValueError(f"unsupported effect stacking rule {effect.stacking!r}")

    return tuple(result)
