# Feature Upgrade — Advanced Interactions, Reactions, and Effects

## Outcome

Expand the MVP's safe interaction framework into a richer simultaneous-action
system: movement conflicts, grabs/holds, group effects, AoE, persistent effects,
environment coupling, and more sophisticated reactions.

The coordinator remains single-writer and bounded.

## Packages

Use existing:

- networkx
- Hypothesis
- SQLAlchemy/Alembic if persistence schema needs extension

No custom event loop or workflow engine.

---

## Slice IX-01 — Formal resource/read/write claim model

### Goal

Make conflict semantics explicit enough for advanced actions.

### Depends on

MVP dependency/arbitration layer.

### Shared code

**EXTEND** proposal claim contracts with durable categories.

### Packages

No new package.

### Method

Formalize claim types:

- READ
- AGGREGATE_WRITE
- EXCLUSIVE_WRITE
- EXCLUSIVE_CLAIM
- RULE_GOVERNED

Targets are typed refs plus optional subresource keys.

Examples:

- actor position → EXCLUSIVE_WRITE
- actor health delta → AGGREGATE_WRITE
- unique rope → EXCLUSIVE_CLAIM
- dam integrity forcing → AGGREGATE_WRITE
- effect stack → RULE_GOVERNED

Conflict detection must be pure and inspectable.

### Tests

Pairwise conflict matrix plus Hypothesis symmetry tests where applicable.

### Completion

The coordinator can explain *why* two proposals conflict.

---

## Slice IX-02 — Timing and initiative policy

### Goal

Support overlapping action timing without making wall-clock execution semantic.

### Depends on

IX-01.

### Shared code

**USE** `TimeSpan`, semantic RNG, scoring/audit records.

### Packages

No new package.

### Method

Separate:

- declared action duration
- initiative/timing score
- resolution ordering
- actual Python execution order

Timing/initiative may combine:

- actor attributes
- action modifiers
- situational factors
- seeded random sample

Record all inputs and sample.

Equal/overlapping timing may be resolved simultaneously or stochastically
according to policy.

### Tests

- same seed replays timing
- coroutine/order changes cannot change semantic timing
- simultaneous timing remains simultaneous rather than arbitrary list order

### Completion

The coordinator has explicit narrative/simulation timing independent of runtime
scheduling.

---

## Slice IX-03 — Movement and occupancy conflicts

### Goal

Resolve actors attempting incompatible movement/occupancy.

### Depends on

spatial upgrade + IX-02.

### Shared code

**USE** spatial query service and claim model.

### Packages

networkx/Shapely already available.

### Method

Movement remains a proposal until arbitration.

Handle:

- two actors entering exclusive narrow location
- swap/crossing
- interception of movement
- forced movement
- movement canceled by changed reachability

Prefer domain policy + seeded arbitration over last-writer-wins.

### Tests

- narrow-space collision
- simultaneous swap
- forced displacement versus voluntary movement
- reproducible stochastic winner

### Completion

Position commits cannot contradict occupancy rules.

---

## Slice IX-04 — Holds, grapples, and relational state

### Goal

Represent actions whose state spans multiple actors.

### Depends on

IX-01/IX-03.

### Shared code

**CREATE/EXTEND** a generic relation/effect representation if current Effects
cannot model it cleanly.

### Packages

No new package.

### Method

A grapple/hold is not duplicated booleans on two actors. Represent one durable
relationship/effect with source/target and constraints.

Movement/action eligibility queries relationship state.

Breaking/redirecting the relation goes through resolution and commit.

### Tests

- relation has one canonical identity
- both actors observe consistent relation
- movement conflict respects hold
- deleting/ending relation is idempotent

### Completion

Cross-actor persistent state has a single source of truth.

---

## Slice IX-05 — Area/group targeting

### Goal

Support AoE and group effects without generating unbounded ad-hoc target loops.

### Depends on

spatial upgrade and effects runtime.

### Shared code

**EXTEND** target abstraction only if region/group targets are not sufficient.

### Packages

Shapely where geometric region membership is used.

### Method

Resolve target set once from the phase snapshot.

Record:

- area/group selector
- resolved target IDs
- eligibility reason

Subsequent target changes during resolution do not retroactively alter that
target set unless the ability explicitly defines dynamic targeting.

Apply per-target consequences as child resolution records under one parent
operation and count them toward causal/event budgets.

### Tests

- target set stable for snapshot
- no duplicate target application
- causal budget includes generated child work
- group target works without geometry

### Completion

AoE/group abilities are bounded, inspectable, and replayable.

---

## Slice IX-06 — Persistent effect scheduler

### Goal

Make duration/expiry/periodic effects first-class.

### Depends on

IX-04/IX-05.

### Shared code

**USE** `Effect`, `EffectStacking`, `TimeSpan`; extend with scheduling
metadata only if generic.

### Packages

No new package.

### Method

Do not run background timers.

At each simulation advancement, derive which effects:

- remain active
- expire
- produce scheduled pulse/consequence
- refresh/replace/stack

Periodic effects enqueue bounded proposals/events into the coordinator.

Expiry and pulse processing use simulation time, never wall-clock time.

### Tests

- duration expiry
- refresh/replace/strongest/stack
- replay across multiple rounds
- self-trigger loop bounded
- advancing wall-clock without simulation time changes nothing

### Completion

Persistent effects behave consistently across ticks/rounds.

---

## Slice IX-07 — Advanced environment coupling

### Goal

Allow interactions to produce multi-domain environmental consequences while
preserving one-evolution-per-component semantics.

### Depends on

persistent effects and existing dynamics.

### Shared code

**USE** `DisturbanceSet` and component refs.

### Packages

No new package.

### Method

Allow rule/data definitions to map one resolved action/event to several forcing
outputs.

Example:

heavy impact may affect:

- dam integrity
- water turbidity
- footing stability
- ecology activity

All contributions aggregate by component before dynamics evolution.

Derived environment events are queued after commit for defined future reaction
windows; they do not recursively evolve the same component again.

### Tests

- multi-domain impact
- two sources aggregate
- derived event cannot double-evolve source component
- max delta/bounds preserved

### Completion

Complex action/environment coupling remains bounded and auditable.

---

## Slice IX-08 — Adversarial interaction qualification

### Goal

Prove termination and consistency under intentionally pathological interactions.

### Depends on

IX-01 through IX-07 and the MVP coordinator/replay infrastructure.

### Shared code

**USE** proposal terminal states, causal budgets, dependency/claim records,
semantic random streams, round records, and replay services. Do not introduce
test-only alternate scheduling semantics.

### Packages

- Hypothesis

### Method

Generate bounded combinations of:

- dependency cycles
- reactions
- claims
- effect chains
- event graphs
- movement conflicts

Assertions:

- finite termination within declared budget
- no proposal left waiting
- no duplicate operation commit
- canonical state validates
- replay from same seed matches
- shuffled proposal/provider completion order matches
- different seeds may legitimately select different valid outcomes

### Tests

The generated pathological scenarios are themselves the test suite. Retain
minimal failing examples produced by Hypothesis as focused regression fixtures
when they expose a real engine bug.

### Completion

The interaction engine has property-level evidence against deadlock/livelock and
order-dependent corruption.
