# Shared Core Library

The implementation plan contains several concepts that are used by more than one
simulation phase. Those concepts belong in `dynamic_story_scaffold.core`, not in
perception, intent, resolution, environment, or rendering implementations.

The purpose of the core package is to give every layer the same vocabulary while
remaining renderer- and ruleset-independent.

## Modules

### `core.refs`

Stable references used instead of passing unqualified strings between layers.

- `EntityRef`
- `EntityKind`
- `ComponentRef`
- `TargetRef`

A world component is therefore referenced as
`ComponentRef("weather", "wind_speed")`, while an actor is referenced as
`EntityRef(EntityKind.ACTOR, "blackjaw")`.

### `core.time`

- `TimeSpan`

Actions, ticks, rounds, and eventually cinematic moments all use the same time
interval representation.

### `core.randomness`

- `RandomStreams`

The current implementation derives replayable semantic substreams from a run seed. The
planned run/branch context extends this by incorporating branch entropy after a
timeline fork while preserving the same semantic-key model.

Examples:

- `environment / tick / component`
- `perception / tick / actor`
- `decision / round / actor`
- `action / round / actor / ability`
- `initiative / round / actor`

This deliberately prevents random-number consumption in one subsystem from
changing another subsystem's results. A future branch may change all post-fork
entropy or override one scoped semantic stream without perturbing unrelated
streams.

### `core.values`

- `NumericRange`
- `UNIT_INTERVAL`

Environment bounds, probabilities, confidence, risk tolerance, health, and
fatigue share the same range/clamping semantics.

### `core.spatial`

- `Position`

The current implementation supports semantic zones and optional coordinates.
This allows the early engine to use locations such as `west_log` without
preventing later 2D/3D distance calculations.

### `core.effects`

- `Effect`
- `EffectStacking`

Effects use the same source and target references regardless of whether the
effect came from a spell, terrain, ecology, equipment, or another actor.

### `core.scoring`

- `ScoreTerm`
- `ScoreBreakdown`
- `ScoredOption[T]`

Intent selection and cinematic-moment selection both need weighted, inspectable
scores. The scoring representation is shared; the terms and weights are
feature-specific.

### `core.records`

Immutable records crossing subsystem boundaries:

- `WorldForcing`
- `WorldEvent`
- `DisturbanceSet`
- `ComponentChange`
- `Observation`
- `KnowledgeLevel`
- `ActionIntent`
- `ActorUpdate`
- `ActionResolution`
- `Outcome`
- `TickRecord`
- `RoundRecord`

The key boundary is `DisturbanceSet`.

Actors and systems produce disturbances. Bounded world dynamics consume them.

A resolution does not directly set wind speed, dam integrity, or other dynamic
environment values. It emits forcing/events, and the environment decides the
legal next state.

### `core.interfaces`

Protocols for replaceable feature implementations:

- `PerceptionProvider`
- `IntentProvider`
- `ActionResolver`

A later deterministic provider, rules-based provider, or LLM-backed provider can
therefore use the same contract without changing the simulation coordinator.

## Actor definitions and state

`schema.ActorDefinition` contains fields common to both characters and
creatures:

- id
- name
- species
- physical attributes
- motivations
- initial state

`CharacterDefinition` adds role, priorities, and quirks.

`CreatureDefinition` adds behaviors.

Runtime `ActorState` similarly normalizes state shared by all actors:

- position
- posture
- health
- fatigue
- resources
- inventory
- active effects
- relationships
- scenario-specific values

`ActorUpdate` is the shared mutation request. Applying an actor update is
centralized in `ActorState.apply`, including health/fatigue bounds.

## Invariants

Feature implementations should preserve these rules:

1. **Use references, not ambiguous IDs or component-path strings, at subsystem
   boundaries.**
2. **Use semantic random streams.** Never share one mutable RNG across unrelated
   subsystems. Run/branch entropy changes the stream seed material; subsystem
   isolation remains intact.
3. **Intent does not mutate state.**
4. **Resolution emits actor updates and world disturbances.**
5. **Dynamic environment values change only through their dynamics model.**
6. **History records are immutable observations of what occurred.**
7. **Scores remain inspectable.** Do not collapse decision reasoning to one
   unexplained number.
8. **Rendering must not alter simulation truth.**
9. **Role-specific behavior belongs in data/providers, not shared core types.**
10. **Hollow Bank is an integration dataset, never a source of engine special
    cases.**

## What does not belong in core

Do not move something into `core` merely because two current classes use it.

Keep these concerns in feature modules:

- visibility algorithms
- utility terms/weights
- attack formulas
- role-specific behavior
- spell implementations
- initiative policy
- cinematic ranking policy
- prompt construction
- renderer adapters
- campaign-specific rules

The core library defines contracts and durable values. Feature layers define
policy.

## Shared libraries beyond `core`

Shared code does not imply that every reusable type belongs in `core`. Each
cross-release concern has one owning library boundary:

| Concern | Owning library | Reused by |
|---|---|---|
| identity, references, time, scores, random streams, immutable transition records | `dynamic_story_scaffold.core` | all domains |
| branch lineage, checkpoint ancestry, causal difference | `dynamic_story_scaffold.timeline` | play, observer, persistence, evaluation |
| legal choice presentation and player/GM action requests | `dynamic_story_scaffold.play` | CLI, campaign sessions, provider adapters |
| visible fact claims, authored fragments, description requests/results, prose profiles | `dynamic_story_scaffold.description` | spatial projection, observer, prose, providers, persistence, evaluation |
| renderer-neutral requests/results, assets, continuity references | `dynamic_story_scaffold.rendering` | adapters, workflow, persistence, evaluation |
| campaign/session/revision records | `dynamic_story_scaffold.campaign` | application workflow, persistence, import/export |
| provider capability, provenance, normalized failure/fallback records | `dynamic_story_scaffold.providers` | image, intent, and prose adapters once common behavior is proven |
| findings, metrics, feedback, comparison reports | `dynamic_story_scaffold.evaluation` | validators and review workflows |

A slice must extend the owning library instead of declaring a local substitute.
CLI commands and application services orchestrate these libraries; they do not
own duplicate domain models. Provider-specific SDK objects stop at adapters.
Persistence models map to shared records and do not become the domain API.

Create a generic abstraction only after two real consumers demonstrate the same
contract. Until then, keep the implementation in its bounded domain and leave a
clear extraction point.
