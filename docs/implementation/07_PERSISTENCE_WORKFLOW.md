# Feature Upgrade — Durable Campaigns, Persistence, and Workflow

## Outcome

Expand MVP persistence into a durable workspace for multiple scenes, campaigns,
runs, branches, rendered assets, feedback, and long-lived replay.

This upgrade is about lifecycle and data organization, not simulation policy.

## Packages

Use:

- SQLAlchemy 2.x
- Alembic
- platformdirs
- Typer
- stdlib hashlib/json/pathlib

Only add compression such as **zstandard** after measured snapshot size justifies
it. Do not preemptively introduce custom binary formats.

---

## Slice PW-01 — Project/campaign and scene revision model

### Goal

Persist authored inputs independently from simulation runs.

### Depends on

MVP run persistence.

### Shared code

Scene definitions remain schema-domain values; DB models are persistence models.

### Packages

SQLAlchemy/Alembic.

### Method

Add durable entities:

- Project/Campaign
- Scene
- SceneRevision

SceneRevision stores:

- source YAML/text
- normalized parsed representation or canonical JSON
- content hash
- schema version
- creation metadata

SimulationRun references one immutable SceneRevision.

Editing a scene creates a new revision; it never mutates the historical input of
existing runs.

### Tests

- identical content can be detected by hash
- run remains pinned to old revision after scene edit
- invalid scene never becomes active revision

### Completion

Every run has immutable authored-input provenance.

---

## Slice PW-02 — Full simulation provenance

### Goal

Persist all information required to explain/replay a branch.

### Depends on

branching and interaction upgrades.

### Shared code

Use existing immutable round/action/event/effect records.

### Packages

SQLAlchemy/Alembic.

### Method

Durable provenance includes:

- run/root seed
- branch lineage/entropy
- checkpoint snapshots
- round records
- perceptions
- scored candidates
- intents
- arbitration records
- RNG stream keys/samples where required for audit
- resolutions
- actor updates
- effects/events
- environment component changes
- provider/rules version metadata

Avoid over-normalizing tiny immutable nested structures when JSON storage is
clearer; normalize entities that need identity/query constraints.

### Tests

Persist/load/replay complex round including cycle arbitration and effects.

### Completion

No important causal explanation exists only in memory.

---

## Slice PW-03 — Repository/service boundary

### Goal

Keep SQLAlchemy session mechanics out of simulation/domain code.

### Depends on

PW-01/PW-02.

### Shared code

Create persistence repositories/application services, not a generic ORM
abstraction framework.

### Packages

SQLAlchemy.

### Method

Repository methods should correspond to DSS operations:

- save scene revision
- create run/root branch
- load checkpoint
- commit completed round
- create branch
- store render request/result
- store feedback

Simulation coordinator knows an application persistence interface, not SQL
queries.

Transactions begin/end inside persistence service calls.

### Tests

Unit service tests plus SQLite integration.

### Completion

Domain/coordinator tests can run without a live persistent database where useful.

---

## Slice PW-04 — Crash recovery and incomplete operations

### Goal

Recover safely from process failure without duplicating committed work.

### Depends on

PW-03.

### Shared code

Use stable operation IDs already defined by simulation/rendering layers.

### Packages

SQLAlchemy.

### Method

Distinguish:

- proposed/in-progress external operation
- completed simulation round awaiting durable commit
- committed durable round
- render request
- render result

Simulation state is advanced durably only by committed round transaction.

On restart, detect incomplete operations and either:

- retry idempotently
- mark failed
- abandon safely

Never infer success solely because an output file partially exists.

### Tests

Simulated crash/failure around each transaction boundary.

### Completion

Restart cannot duplicate damage/events/rounds/assets.

---

## Slice PW-05 — Application-data layout

### Goal

Define predictable OS-aware storage for DB, authored sources, cached exports,
and generated assets.

### Depends on

asset store.

### Shared code

Use existing path helpers/platformdirs.

### Packages

platformdirs.

### Method

Define stable directories under app data, e.g.:

- database
- assets
- exports
- cache/temp if needed

Do not assume repository checkout is runtime storage.

### Tests

Path override and platform behavior; existing tests remain valid.

### Completion

Development, installed runtime, and artifact storage are cleanly separated.

---

## Slice PW-06 — Import/export bundle

### Goal

Move a scene/run/branch between installations without depending on DB internals.

### Depends on

PW-01 through PW-05.

### Shared code

Export format is application-level.

### Packages

stdlib zipfile/tarfile/json; do not create a custom archive format.

### Method

Bundle manifest contains:

- format version
- scene revision
- run/branch/checkpoint history selected for export
- seeds/entropy/provenance
- asset references plus optionally included files/hashes

Import validates hashes and IDs, remaps local storage as necessary, and never
silently overwrites unrelated local IDs.

### Tests

round-trip bundle; corrupted asset hash; version rejection.

### Completion

A reproducible timeline can be transferred or archived.

---

## Slice PW-07 — Workflow-oriented CLI

### Goal

Expose durable project/run workflow rather than individual low-level DB actions.

### Packages

Typer.

### Method

Commands approximately:

- project create/list/show
- scene import/revise/validate
- run start/list/show
- branch list/fork/activate
- run advance/replay
- moment/render/asset commands
- export/import

Prefer IDs plus human-readable aliases where useful.

JSON output remains available for orchestration.

### Tests

End-to-end fake-renderer workflow in a temporary data directory.

### Completion

A user can operate a durable DSS project without interacting with repository
paths or SQL directly.

---

## Upgrade qualification

Validate:

- historical scene immutability
- replay after process restart
- idempotent recovery
- branch ancestry
- asset provenance
- import/export integrity
- no long-running DB write transactions
