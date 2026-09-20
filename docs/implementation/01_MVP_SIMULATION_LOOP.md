# MVP — Complete Bounded Simulation Loop

## Outcome

The MVP proves DSS as a simulation engine independently of rendering.

Given `examples/hollow_bank.yaml`, DSS must be able to:

1. create a simulation run and root timeline branch
2. initialize normalized actor/environment state
3. create an immutable round snapshot
4. give each actor a non-omniscient perception
5. generate action candidates
6. choose an intent from character/role/world factors
7. resolve simultaneous/conflicting actions with seeded stochastic arbitration
8. process bounded reactions/events/effects without recursion
9. aggregate forcing and evolve each environment component once
10. atomically commit one coherent next world state
11. persist the run/branch/checkpoint/round audit record
12. replay the same round from the same checkpoint and seed
13. expose the result for inspection through the CLI

No renderer is part of the MVP.

## Packages

Use existing dependencies for YAML, persistence, CLI, and packaging.

Add:

- `networkx` — dependency graph, topological operations, strongly connected
  components. Do not hand-write graph algorithms.
- `hypothesis` as a development dependency — property tests for termination,
  ordering independence, bounded state, idempotency, and replay.

Do not introduce an async framework in the MVP. Provider interfaces may later
become concurrent, but canonical coordination stays synchronous and
single-writer.

---

## Slice MVP-01 — Run identity, lineage, and immutable snapshots

### Goal

Introduce the minimum run/branch/checkpoint identity model needed so the MVP is
branch-capable without yet implementing user-facing branch operations.

### Depends on

- existing `core.refs`, `core.randomness`, `core.time`
- existing `WorldState`
- architecture in `docs/IMPLEMENTATION_PLAN.md`

### Shared code

**EXTEND** shared code with durable identifiers/lineage values:

- `RunId`
- `BranchId`
- `CheckpointId`
- `RoundId`
- `RunContext` or equivalent immutable run metadata
- `WorldSnapshot`

Prefer small frozen dataclasses/newtypes. Do not create a generic identity
framework.

### Packages

- stdlib `uuid` for opaque durable IDs
- stdlib `copy`/dataclasses as needed
- no new package

### Method

The scene's `simulation.seed` is only an optional default. Starting a run
chooses/stores the actual root seed.

A root run must immediately have:

- run ID
- root branch ID
- root seed
- scene identity/version information
- initial checkpoint ID

`WorldSnapshot` must be a detached representation. Providers must not receive a
mutable alias of canonical `WorldState`.

Agents should pay particular attention to nested dictionaries/lists in actor
state. A shallow copy is not sufficient.

The snapshot must be serializable using plain Python data so persistence does
not depend on pickling Python objects.

### Expected files

- `src/dynamic_story_scaffold/core/identity.py`
- `src/dynamic_story_scaffold/core/records.py`
- `src/dynamic_story_scaffold/state.py`
- exports in `core/__init__.py`
- tests under `tests/`

### Tests

- scene default seed is copied into run, not treated as permanent scene state
- explicit run seed overrides scene default
- missing seed generates and exposes a replayable run seed
- snapshot mutation cannot mutate canonical state
- snapshot round-trip serialization preserves actor/environment state
- root branch/checkpoint identities are stable within the run

### Completion

A run can be created with an immutable, serializable checkpoint snapshot and
root branch lineage.

### Do not

- implement branch creation/reroll commands
- implement campaign persistence beyond the MVP tables defined later

---

## Slice MVP-02 — Round coordinator skeleton and phase state machine

### Goal

Create the single-writer coordinator before any actor policy is implemented.

### Depends on

MVP-01.

### Shared code

**CREATE/EXTEND** shared execution records only where durable across features:

- coordinator phase enum
- proposal terminal-status enum
- causal/work budget value object
- round execution/audit metadata

Keep coordinator policy outside `core`.

### Packages

No new package.

### Method

Implement a coordinator with explicit phases, not nested callbacks:

1. snapshot
2. perceive
3. intent
4. normalize proposals
5. reaction/arbitration
6. resolve
7. collect disturbances/updates
8. commit
9. record

Add a non-reentrancy guard. Calling `advance_round()` while a round is already
advancing must fail immediately with a domain error.

Every proposal that enters coordination must end the round in one terminal
scheduler status:

- accepted
- rejected
- canceled
- deferred
- failed
- overflowed

There must be no `waiting` state after the round exits.

The coordinator owns canonical state mutation. Provider objects get snapshots,
not `WorldState`.

### Expected files

- `src/dynamic_story_scaffold/coordinator.py`
- shared record/status additions
- `tests/test_coordinator.py`

### Tests

- phase order is explicit and recorded
- recursive round advancement fails
- exceptions before commit leave canonical state unchanged
- every submitted proposal has terminal status
- a no-op round still terminates and advances according to defined time policy

### Completion

A round can execute through empty providers and produce an auditable no-op
record without mutation leaks.

### Do not

- add perception or action policy yet
- add concurrency

---

## Slice MVP-03 — Claims, dependency graph, and bounded arbitration

### Goal

Give the coordinator a generic mechanism for action dependencies and conflicting
writes.

### Depends on

MVP-02.

### Shared code

**EXTEND** proposal/action records with:

- stable proposal/operation ID
- read set
- write set
- exclusive claims
- dependency references
- causal parent/depth

Use typed refs, not arbitrary dotted strings.

### Packages

- **networkx**

### Method

Build a directed graph of proposal dependencies.

Use NetworkX for:

- topological ordering of acyclic regions
- strongly connected component detection
- condensation graph if useful

A strongly connected component is not an error and never becomes a blocking
wait. Pass it to an explicit conflict/arbitration policy.

Arbitration policy interface should receive:

- stable conflict ID
- candidate proposals
- snapshot
- rule/context
- semantic RNG stream

It returns terminal/selected outcomes plus an audit record.

For stochastic arbitration, key RNG by something like:

`arbitration / round-id / conflict-id`

Never use coroutine completion order, dict/set order, or object address as a
tie-break.

Classify writes:

- aggregatable
- exclusive
- rule-governed

The MVP only needs enough types/policies for Hollow Bank, but the mechanism must
not mention specific otter roles.

### Expected files

- `src/dynamic_story_scaffold/arbitration.py`
- `src/dynamic_story_scaffold/dependencies.py`
- record extensions
- tests

### Tests

- acyclic graph resolves in dependency order
- two-node and three-node cycles terminate
- stochastic cycle resolution replays with same seed
- shuffled proposal input order produces same result
- conflicting exclusive claims cannot both commit
- aggregatable claims remain eligible together
- Hypothesis test: arbitrary bounded dependency graphs terminate

### Completion

The coordinator can turn a finite proposal set into a finite set of accepted or
terminally rejected/deferred proposals without waiting.

### Do not

- implement bespoke graph traversal
- treat cycles as exceptions by default

---

## Slice MVP-04 — Baseline perception provider

### Goal

Actors receive useful but non-omniscient observations from one stable snapshot.

### Depends on

MVP-01 through MVP-03.

### Shared code

**USE**:

- `PerceptionProvider`
- `Observation`
- `KnowledgeLevel`
- `EntityRef`
- `Position`
- `RandomStreams`

Do not create a second perception record type.

### Packages

No new package.

### Method

Implement a rules-based provider sufficient for semantic-zone MVP state.

Observation categories should include:

- self state
- actors in same/adjacent known zone when visible by baseline rules
- obvious posture/injury
- relevant environment components
- recent audible/explicit world events

Confidence and uncertainty may use semantic perception RNG:

`perception / round-id / observer-id / subject-id / fact-key`

Keep observation `fact` machine-readable and place the observed value in
`Observation.value`; prose belongs downstream.

Perception must not read data unavailable through the snapshot/provider context.

### Expected files

- `src/dynamic_story_scaffold/perception.py`
- tests

### Tests

- actors can receive different observations of same snapshot
- hidden/unavailable state is absent or UNKNOWN, never leaked
- same seed replays uncertainty
- consuming unrelated RNG streams does not change perception
- provider cannot mutate canonical state

### Completion

Every Hollow Bank actor receives an inspectable observation tuple from one
snapshot.

### Do not

- implement full line-of-sight geometry
- implement renderer descriptions

---

## Slice MVP-05 — Action candidates and utility intent selection

### Goal

Generate candidate actions from data and choose an intent without role-specific
engine branches.

### Depends on

MVP-04.

### Shared code

**USE**:

- `ActionIntent`
- `ScoreTerm`
- `ScoreBreakdown`
- `ScoredOption`
- role/ability definitions
- semantic RNG streams

**EXTEND** shared types only if a durable candidate record is truly needed.

### Packages

No new package.

### Method

Candidate generation reads role abilities plus generic baseline actions such as
move, defend, observe, no-action.

Utility scoring should expose terms instead of returning one opaque score.

Initial terms:

- objective relevance
- motivation relevance
- priority relevance
- role affinity
- positional suitability
- expected effect
- resource cost
- risk
- recent-action repetition penalty
- quirk modifiers
- bounded decision jitter

Avoid NLP interpretation of free-text priorities in the engine. For MVP, map
the Hollow Bank data into explicit tags/metadata where machine interpretation is
required rather than writing brittle string parsers.

The selection policy may choose max utility or weighted seeded choice among
near-optimal candidates. Whichever method is used must record the scored
candidate set.

### Expected files

- `src/dynamic_story_scaffold/actions.py`
- `src/dynamic_story_scaffold/intent.py`
- schema/YAML metadata additions if required
- tests

### Tests

- same role with different motivations can choose differently
- fixed seed replays selection
- candidate score breakdown is inspectable
- intent generation does not mutate state
- impossible abilities are filtered before scoring
- no legal candidate yields explicit no-action, not failure

### Completion

All Hollow Bank actors can produce valid intents from perceptions and authored
capabilities.

### Do not

- hard-code Reedshadow/Shellbreaker/etc. in engine policy
- ask an LLM to interpret the YAML

---

## Slice MVP-06 — Action resolution and typed consequences

### Goal

Turn accepted intents into auditable resolutions containing actor updates,
effects, forcing, and events.

### Depends on

MVP-05.

### Shared code

**USE**:

- `ActionResolution`
- `ActorUpdate`
- `DisturbanceSet`
- `WorldForcing`
- `WorldEvent`
- `Effect`
- `Outcome`
- `TimeSpan`

### Packages

No new package.

### Method

Resolution is mechanics-first and may be stochastic.

Use semantic streams:

`resolution / round-id / actor-id / intent-id`

A resolver returns proposed consequences. It does not mutate world state.

Implement a small generic check model sufficient for the authored abilities:

- base capability/modifier
- situational modifiers
- target resistance/difficulty
- seeded sample
- degree of success

Map degrees of success to data-defined consequences where possible.

Environmental consequences must be forcing/events, never direct component
assignment.

Actor consequences are `ActorUpdate` objects.

Every resolution records:

- sampled value
- modifiers
- difficulty/opposition
- outcome
- explanation/audit data

### Expected files

- `src/dynamic_story_scaffold/resolution.py`
- ability mechanics adapters/data
- tests

### Tests

- successful physical attack yields typed actor consequences
- terrain-impact ability yields bounded forcing/event, not direct terrain write
- stochastic resolution replays
- failed resolution leaves no hidden mutations
- outcome explanation contains enough data to reconstruct the check

### Completion

Every MVP intent can resolve into typed proposals without mutating canonical
state.

### Do not

- model real-world physics
- embed visual effects into mechanics

---

## Slice MVP-07 — Bounded reactions, events, and effects

### Goal

Support interception and effect/event chains without recursion or causal
explosion.

### Depends on

MVP-06.

### Shared code

**USE/EXTEND**:

- `Effect`, `EffectStacking`
- `WorldEvent`
- operation IDs/causal metadata
- work budgets

### Packages

No new package.

### Method

Implement explicit reaction windows and event generations.

Do not call resolver/coordinator recursively.

Process:

1. primary accepted proposal opens declared reaction window
2. eligible reactors produce reaction proposals
3. coordinator arbitrates them
4. accepted reactions modify/cancel/redirect proposals
5. generated events/effects enter explicit queues
6. next generation is processed only if budget allows
7. overflow is recorded and deferred/terminated

Define initial hard/configurable budgets for:

- reaction depth
- causal depth
- events per round
- resolutions per round
- deferrals

Effect stacking must be centralized by target + effect identity/kind according
to REPLACE/STACK/STRONGEST/REFRESH.

### Expected files

- `src/dynamic_story_scaffold/reactions.py`
- `src/dynamic_story_scaffold/effect_runtime.py`
- `src/dynamic_story_scaffold/events.py`
- tests

### Tests

Explicitly include:

- Hold-the-Line style intercept
- intercept/counter-intercept cycle
- event A → effect B → event A
- self-refreshing effect
- causal budget exhaustion
- duplicate operation ID
- termination property with Hypothesis

### Completion

Reaction/event/effect processing always terminates within declared work bounds.

### Do not

- silently drop overflow; record it
- let effects call `advance_round` or `tick`

---

## Slice MVP-08 — Aggregate, validate, and atomically commit a round

### Goal

Apply all accepted consequences exactly once to produce one coherent next state.

### Depends on

MVP-07.

### Shared code

**USE** existing actor-update and disturbance contracts.

### Packages

No new package.

### Method

Before mutation:

- validate all accepted actor updates
- aggregate commutative deltas
- confirm exclusive conflicts are already arbitrated
- centralize effect stacking
- aggregate forcing by `ComponentRef`

Create a candidate next state detached from canonical state. Apply:

1. actor updates
2. accepted effects
3. aggregated environment forcing/events
4. exactly one environment evolution per component/tick

Only after all application succeeds replace/commit canonical state.

If applying any accepted proposal fails validation, the round fails before
canonical mutation.

The round audit must contain state-before and state-after checkpoint hashes or
IDs plus all intermediate decisions.

### Expected files

- coordinator/commit module
- `simulation.py` integration
- state helpers
- tests

### Tests

- two forces to same component aggregate before one dynamics evolution
- health/fatigue bounds hold
- two exclusive writes cannot last-write-win
- failed commit leaves old canonical state intact
- input ordering does not change committed state
- same seed/input reproduces byte-equivalent normalized snapshot

### Completion

A complete Hollow Bank round advances state through one atomic coordinator
commit.

---

## Slice MVP-09 — Minimal simulation persistence and idempotent round commit

### Goal

Persist enough history to resume, replay, and later branch without turning
SQLite into a runtime coordination mechanism.

### Depends on

MVP-08.

### Shared code

**CREATE** persistence-specific SQLAlchemy models, not duplicate domain models.

Minimum durable entities:

- SimulationRun
- TimelineBranch
- Checkpoint
- SimulationRound
- optional normalized operation table if needed for idempotency

### Packages

- SQLAlchemy
- Alembic
- stdlib `json`; use SQLAlchemy JSON type where portable for SQLite

### Method

Add an Alembic migration.

Run/branch model:

- run owns root seed and scene identity
- root branch belongs to run
- checkpoint belongs to branch and references previous checkpoint
- round references input checkpoint and output checkpoint
- branch stores active head checkpoint

Persist serialized snapshots/history, not pickled Python objects.

Round commit is one short DB transaction after simulation computation.

Use stable operation/round IDs and a unique constraint so retrying persistence
cannot create duplicate durable rounds.

Never hold the transaction while computing perception/intent/resolution.

### Expected files

- DB models
- Alembic revision
- repository/service module for simulation persistence
- tests

### Tests

- run/root branch/checkpoint creation
- round persistence advances branch head atomically
- duplicate round commit is idempotent or cleanly rejected without duplicate
- failed DB transaction does not partially advance head
- replay can load input checkpoint and round audit

### Completion

A committed round is durable, resumable, and structurally ready to have sibling
branches.

---

## Slice MVP-10 — Replay service and CLI inspection

### Goal

Demonstrate the MVP from the command line and prove replay.

### Depends on

MVP-09.

### Shared code

**USE** application services; CLI contains no simulation policy.

### Packages

- Typer

### Method

Add commands approximately:

- `dss scene validate PATH`
- `dss run start PATH [--seed N]`
- `dss run advance RUN_OR_BRANCH_ID`
- `dss run show ...`
- `dss round show ROUND_ID`
- `dss run replay ROUND_ID`

Exact command names may be refined for Typer ergonomics.

Replay should load the round's input checkpoint plus stored run/branch entropy
and reproduce the same normalized output and stochastic audit.

Provide JSON output option for orchestrators/tests.

### Expected files

- CLI
- application service layer if not already created
- tests

### Tests

- start + advance Hollow Bank through CLI/service
- JSON result contains IDs, seed, intents, outcomes, state diff
- replay matches stored output checkpoint
- malformed/unknown IDs produce clear errors

### Completion

The Hollow Bank example can execute and replay one complete persisted round with
no renderer.

---

## MVP qualification

Before opening the MVP PR:

```bash
hatch run test
hatch run build
hatch run package
```

For installed-runtime qualification, install the produced wheel into a clean
environment, run `dss-maintain setup`, then exercise the installed `dss`
entry point. Do not invoke `dss` from the Hatch/source environment as an
installation step.

Required adversarial coverage:

- cycles terminate
- no proposal left waiting
- same seed replays
- different seed may produce different outcomes
- unrelated RNG streams remain isolated
- input/completion ordering cannot alter replay result
- event/reaction budgets terminate feedback loops
- failed commit cannot partially mutate canonical/durable state
- persistence retry cannot duplicate a committed round

The MVP is complete only when the simulation can explain **why** a stochastic
outcome occurred, not merely return the resulting state.
