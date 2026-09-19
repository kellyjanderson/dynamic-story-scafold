from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Callable

from .schema import ContinuousComponentDefinition
from .state import ContinuousComponentState


class DynamicsError(ValueError):
    """Raised when a named dynamics method cannot evolve a component."""


@dataclass(frozen=True)
class DynamicsContext:
    forcing: float = 0.0


DynamicsMethod = Callable[
    [ContinuousComponentDefinition, ContinuousComponentState, Random, DynamicsContext],
    ContinuousComponentState,
]

_REGISTRY: dict[str, DynamicsMethod] = {}


def register_dynamics(name: str):
    def decorator(func: DynamicsMethod) -> DynamicsMethod:
        if name in _REGISTRY:
            raise RuntimeError(f"dynamics method {name!r} is already registered")
        _REGISTRY[name] = func
        return func

    return decorator


def available_dynamics() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def _clip_delta(
    definition: ContinuousComponentDefinition,
    delta: float,
) -> float:
    limit = definition.dynamics.max_delta
    if limit is None:
        return delta
    return max(-limit, min(limit, delta))


def _finish(
    definition: ContinuousComponentDefinition,
    state: ContinuousComponentState,
    delta: float,
    velocity: float | None = None,
) -> ContinuousComponentState:
    delta = _clip_delta(definition, delta)
    next_value = definition.bounds.clamp(state.value + delta)
    actual_delta = next_value - state.value
    return ContinuousComponentState(
        value=next_value,
        velocity=actual_delta if velocity is None else velocity,
    )


@register_dynamics("fixed")
def fixed(
    definition: ContinuousComponentDefinition,
    state: ContinuousComponentState,
    rng: Random,
    context: DynamicsContext,
) -> ContinuousComponentState:
    del definition, rng, context
    return ContinuousComponentState(value=state.value, velocity=0.0)


@register_dynamics("bounded_random_walk")
def bounded_random_walk(
    definition: ContinuousComponentDefinition,
    state: ContinuousComponentState,
    rng: Random,
    context: DynamicsContext,
) -> ContinuousComponentState:
    spec = definition.dynamics
    noise = rng.gauss(0.0, spec.jitter) if spec.jitter else 0.0
    delta = spec.drift + context.forcing + noise
    return _finish(definition, state, delta)


@register_dynamics("bounded_inertial")
def bounded_inertial(
    definition: ContinuousComponentDefinition,
    state: ContinuousComponentState,
    rng: Random,
    context: DynamicsContext,
) -> ContinuousComponentState:
    spec = definition.dynamics
    noise = rng.gauss(0.0, spec.jitter) if spec.jitter else 0.0
    impulse = spec.drift + context.forcing + noise
    velocity = spec.inertia * state.velocity + (1.0 - spec.inertia) * impulse

    max_velocity = spec.parameters.get("max_velocity")
    if max_velocity is not None:
        max_velocity = abs(float(max_velocity))
        velocity = max(-max_velocity, min(max_velocity, velocity))

    delta = _clip_delta(definition, velocity)
    return _finish(definition, state, delta, velocity=delta)


@register_dynamics("bounded_target")
def bounded_target(
    definition: ContinuousComponentDefinition,
    state: ContinuousComponentState,
    rng: Random,
    context: DynamicsContext,
) -> ContinuousComponentState:
    spec = definition.dynamics
    if "target" not in spec.parameters:
        raise DynamicsError(
            f"{definition.name}: bounded_target requires dynamics.target"
        )

    target = definition.bounds.clamp(float(spec.parameters["target"]))
    response = float(spec.parameters.get("response", 0.25))
    if not 0.0 <= response <= 1.0:
        raise DynamicsError(
            f"{definition.name}: bounded_target response must be between 0 and 1"
        )

    noise = rng.gauss(0.0, spec.jitter) if spec.jitter else 0.0
    delta = (target - state.value) * response
    delta += spec.drift + context.forcing + noise
    return _finish(definition, state, delta)


def evolve_continuous(
    definition: ContinuousComponentDefinition,
    state: ContinuousComponentState,
    rng: Random,
    *,
    forcing: float = 0.0,
) -> ContinuousComponentState:
    try:
        method = _REGISTRY[definition.dynamics.method]
    except KeyError as exc:
        raise DynamicsError(
            f"unknown dynamics method {definition.dynamics.method!r}; "
            f"available methods: {', '.join(available_dynamics())}"
        ) from exc

    return method(
        definition,
        state,
        rng,
        DynamicsContext(forcing=float(forcing)),
    )
