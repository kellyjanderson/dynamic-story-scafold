# Implementation Plan Set

These documents are written for Esther, another orchestrator, or a chain of
implementation agents. The architecture source of truth remains
`docs/IMPLEMENTATION_PLAN.md`; this directory turns that architecture into
bounded implementation work.

## Execution order

1. `01_MVP_SIMULATION_LOOP.md`
2. `02_TIMELINE_BRANCHING.md`
3. `03_SPATIAL_PERCEPTION.md`
4. `04_INTERACTIONS_EFFECTS.md`
5. `05_CINEMATIC_OBSERVER.md`
6. `06_RENDER_PIPELINE.md`
7. `07_PERSISTENCE_WORKFLOW.md`
8. `08_EVALUATION_EXPLORATION.md`
9. `09_EXTERNAL_DECISION_PROVIDERS.md`

Later documents may be implemented partially or reordered when their declared
dependencies permit it. Do not pull later policy into the MVP merely because it
is described elsewhere.

## Orchestrator rules

### A slice is one implementation prompt

Each numbered slice is intentionally sized so one coding agent can:

1. inspect the named existing files/contracts
2. implement one coherent behavior
3. add/adjust tests
4. run local qualification
5. commit the result
6. return a concise handoff

If a slice reveals work large enough to need a second independent design
decision, split it before implementation.

### Agents must not redesign shared contracts casually

Shared code currently lives under `dynamic_story_scaffold.core` and is
documented in `docs/CORE_LIBRARY.md`.

A slice explicitly says whether it must:

- **USE** shared code unchanged
- **EXTEND** shared code
- **CREATE** a new shared abstraction

If an agent believes an undeclared shared abstraction is required, it should
report that as a plan deviation instead of silently introducing a competing
type.

### Prefer mature packages over generic custom infrastructure

Before implementing a non-DSS-specific algorithm or infrastructure concern,
check for an established package.

Packages selected by this plan:

- existing: PyYAML, SQLAlchemy, Alembic, Typer, platformdirs, GitPython,
  Hatch/Hatchling, pytest
- add for MVP: **networkx** for dependency graphs/SCC/topological operations
- add for development tests: **Hypothesis** for bounded termination,
  idempotency, ordering, and replay properties
- later renderer/provider retry work: **tenacity** only where retries are
  actually required

Do not write custom graph algorithms, migration frameworks, CLI parsers,
task runners, retry frameworks, or build systems.

### Keep policy out of the core library

Core should contain durable domain values and interfaces.

Feature modules own policy such as:

- visibility rules
- action utility weights
- attack formulas
- reaction eligibility
- conflict-arbitration weights
- cinematic ranking weights
- prompt construction
- renderer-specific behavior

### Simulation mutation has one owner

Canonical world-state mutation belongs to the round/simulation coordinator.

Providers may read snapshots and emit proposals. They do not mutate
`WorldState`, advance time, persist partial work, or recursively call the
coordinator.

### Stochastic does not mean unreplayable

Resolutions and conflict arbitration may use randomness.

Every stochastic decision must use `RandomStreams` with a semantic key. Same
state + same proposals + same seed/branch entropy must replay the same sampled
outcome regardless of coroutine completion order or container iteration order.

### Visual-frequency terminology

When discussing rendering quality, do not use "noise" as shorthand for all fine
detail.

Distinguish:

- **random image noise/artifacts** — unwanted stochastic or generation error
- **high-spatial-frequency signal** — legitimate fine structure such as fur,
  droplets, bark, foliage edges, ripples, and reflections
- **perceptual interference** — too much competing high-frequency signal spread
  across the frame, weakening focal hierarchy and reading as visual noise to a
  human observer

Art-direction work should manage the **distribution and concentration of
high-spatial-frequency signal**, preserving it where it supports the focal
subject/action and reducing competing fine detail elsewhere.

### Branch-capable history from the beginning

Even before full multiverse tooling exists, persisted simulation history must
not assume there can only ever be one linear future.

The MVP creates:

- run identity
- root branch identity
- checkpoints
- parent checkpoint references
- round lineage

Upgrade 02 adds user-facing forking/reroll/exploration operations.

## Required slice structure

Every slice in this directory contains:

### Goal
What must be true after the slice.

### Depends on
Earlier slices/contracts that must exist.

### Shared code
Exactly what common code is used, extended, or created.

### Packages
Existing/additional Python packages and what they are used for.

### Method
Architecturally important implementation details. This is deliberately detailed
for concurrency, replay, graph resolution, mutation boundaries, persistence,
and other areas where coding agents tend to drift.

### Expected files
Likely files to create/modify when the slice benefits from naming them. Agents
may adjust filenames when repository structure makes that clearly better, but
should preserve the stated boundaries.

### Tests
Behavior and invariants that must be proved.

### Completion
A short objective stop condition.

### Do not
Use when a slice has an important scope trap. It may be omitted when the
document-level boundaries already make the exclusion unambiguous.

The mandatory fields for every dispatched slice are **Goal, Depends on, Shared
code, Packages, Method, Tests, and Completion**.

## Standard handoff from every slice

The implementing agent should return:

- commit SHA
- files changed
- tests run and results
- any new dependency
- any schema migration
- any plan deviation
- any newly discovered follow-up work

Do not open a PR after every slice. Work on the feature branch, qualify locally,
and open the PR only when the implementation document's final slice is ready.
CI is intentionally PR-open-only.

## Local qualification

Default:

```bash
hatch run test
```

For slices that alter packaging/database installation:

```bash
hatch run build
hatch run dss install
```

Use focused test invocations during development, but finish a document with the
full local test suite before its PR is opened.
