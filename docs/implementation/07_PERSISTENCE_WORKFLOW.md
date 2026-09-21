# v0.7.0 — Durable Campaigns, Persistence, and Workflow

## Outcome

Expand MVP persistence into a durable workspace for multiple scenes, campaigns,
runs, branches, rendered assets, feedback, and long-lived replay.

This upgrade is about lifecycle and data organization, not simulation policy.

Authored sub-prose, prose profiles, compiled passages, sentence provenance,
keyframe descriptions, continuity references, and derived assets are durable
project data in this release.


Database schema changes are an **installer/maintenance concern**. The normal
`dss` runtime must verify that application state is ready and fail clearly if
it is not; it must never run Alembic upgrades implicitly. Explicit setup and
support migrations belong to the separate `dss-maintain` executable.

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

### Depends on

PW-01 through PW-06 plus the simulation/branch/render application services that
are available at implementation time.

### Shared code

**USE** existing durable IDs, repository/application services, and Typer command
groups. The CLI is an adapter; it must not own persistence transactions or
simulation policy.

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

## Slice PW-08 — Durable prose library and description provenance

### Goal

Persist reusable authored language and compiled descriptions with complete
revision and source provenance.

### Depends on

PW-01 through PW-07 and the description contracts available from v0.6.0.

### Shared code

**USE** project/scene revision IDs, entity/effect/condition refs,
DescriptionRequest/Result, moment IDs, style/prose profile IDs, and asset refs.

### Packages

Existing SQLAlchemy/Alembic/platformdirs/Typer.

### Method

Store versioned sub-prose libraries separately from runtime state, including
stable identity prose, environment/place prose, object/material prose,
effect/condition variants, profiles, and invariants. Persist compiled passages
and keyframe sequences with exact input revisions and claim provenance. Scene
revision must freeze the language it used. Import/export includes all referenced
language and rejects missing or hash-mismatched dependencies.

### Tests

- old scene/run descriptions replay after prose library revision
- passage provenance resolves after restart and export/import
- deleting or editing a current library cannot rewrite historical output
- missing referenced language/profile fails import clearly
- CLI can list/show/recompile descriptions through application services

### Completion

Long-lived projects retain both their authored descriptive language and exact
historical prose outputs.

---

## Slice PW-09 — Resumable campaign play session

### Goal

Make the directed-turn-to-image loop resumable across installed DSS sessions.

### Depends on

PW-01 through PW-08 and RP-10.

### Shared code

**CREATE** campaign/session records in the `campaign` library. **USE** shared
play, timeline, description, rendering, and asset contracts. Persistence maps
those records; it does not define competing session objects.

### Packages

Existing SQLAlchemy/Alembic/Typer/platformdirs. Do not add a workflow engine.

### Method

Persist the campaign's active scene revision, active branch/checkpoint, player
actor assignments, prose/style profile, latest continuity references, turn
history, selected moments, descriptions, assets, and incomplete render status.
Allow open, inspect, play-one-turn, rerender, branch, and resume operations.
Session pointers are user workflow state and never delete alternate histories.

### Tests

- restart resumes the exact active checkpoint and continuity references
- one session turn links choice, round, moment, prose, and asset
- switching branches updates the session pointer without deleting siblings
- incomplete rendering resumes idempotently without replaying the turn
- export/import preserves the playable campaign session

### Completion

A progressive illustrated campaign can continue over many installed DSS runs.

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
- resumable directed-turn-to-image campaign workflow
