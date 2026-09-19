# Feature Upgrade — Timeline Branching / Multiverse Simulation

## Outcome

Expose the branch-capable history model as first-class simulation functionality.

Users can fork any eligible checkpoint, reroll a disliked outcome, intervene in
state, explore multiple stochastic futures, compare siblings, and select an
active timeline without deleting alternatives.

This feature extends the MVP lineage model; it does not create a second
simulation engine.

## Packages

Use existing SQLAlchemy/Alembic/Typer.

No graph package is needed for timeline ancestry unless queries become complex
enough to justify one; the persisted model is a parent-linked DAG/tree of
branches and checkpoints, not an in-memory action dependency graph.

---

## Slice BR-01 — Branch service and lineage invariants

### Goal

Create sibling timeline branches from existing checkpoints.

### Depends on

MVP persistence/run/checkpoint model.

### Shared code

**EXTEND** durable lineage values only if necessary:

- branch point kind
- branch entropy metadata
- optional intervention record

### Packages

- SQLAlchemy/Alembic

### Method

A branch must reference:

- parent branch
- parent checkpoint
- branch-point kind
- branch entropy seed/salt
- creation metadata

Do not copy all historical rounds into the new branch. History before the fork
is shared through ancestry.

A new branch head initially points at the parent checkpoint.

Disallow ancestry cycles at service and DB-reference level.

### Tests

- fork from any valid checkpoint
- sibling branches share parent history
- fork does not mutate parent head/history
- invalid cross-run parent reference rejected
- branch ancestry is acyclic

### Completion

Branches can be created durably without advancing them.

---

## Slice BR-02 — Full-future reroll

### Goal

Rerun from a checkpoint with new post-fork entropy.

### Depends on

BR-01.

### Shared code

**USE** `RandomStreams` and run/branch context.

### Packages

No new package.

### Method

Derive post-fork semantic streams from:

- root run seed
- branch lineage/entropy
- semantic stream key

Do not mutate old round records.

A reroll before round N creates a new branch whose first advanced round is a new
round with a new ID and sampled outcomes.

Same branch entropy must replay identically.

### Tests

- original future remains intact
- new branch can diverge
- same branch seed replays
- pre-fork checkpoint snapshot is identical for siblings

### Completion

A user can fork immediately before a disliked resolution and obtain a new future.

---

## Slice BR-03 — Scoped stochastic reroll

### Goal

Allow one semantic stochastic decision to be resampled without unnecessarily
changing unrelated streams.

### Depends on

BR-02.

### Shared code

**EXTEND** run/branch entropy context with scoped stream overrides.

### Packages

No new package.

### Method

Represent overrides as data:

- semantic stream key/prefix
- replacement entropy salt/seed
- branch/checkpoint scope
- reason/user note

Random stream resolution checks the most-specific active override before falling
back to branch/root entropy.

Do not patch RNG outputs directly and do not store a giant sequence of random
numbers.

Example key:

`resolution / <round-id> / blackjaw / tail-sweep`

### Tests

- rerolled target stream changes
- unrelated weather stream stays identical
- unrelated actor perception stays identical
- replay of scoped reroll is stable

### Completion

One conflict/action can be rerolled while unrelated stochastic behavior remains
unchanged.

---

## Slice BR-04 — Explicit state intervention branches

### Goal

Create a branch where the divergence is a deliberate state edit rather than
randomness.

### Depends on

BR-01.

### Shared code

**CREATE** a typed intervention record that uses existing refs/update types.

### Packages

No new package.

### Method

Interventions are applied at a checkpoint boundary through the same validation
and bounded state rules as normal commits.

Examples:

- move actor to another zone
- restore/remove resource
- alter health/fatigue
- introduce/remove effect
- force an allowed environment event

Directly setting a dynamic environment value should require an explicit
administrative override type and audit record; normal interventions should use
forcing/events where possible.

### Tests

- intervention creates child checkpoint only on branch
- parent remains untouched
- invalid intervention is rejected atomically
- audit contains before/after and author/reason metadata

### Completion

"What if X were different here?" is representable without corrupting history.

---

## Slice BR-05 — Branch comparison

### Goal

Compare sibling timelines and identify divergence.

### Depends on

BR-02/BR-04.

### Shared code

**USE** normalized snapshots and round records.

### Packages

No new package initially.

### Method

Produce structured comparison:

- common ancestor checkpoint
- first divergent stochastic/intervention record
- actor-state diffs
- environment diffs
- different intents/outcomes/events
- current branch heads

Keep this renderer-neutral.

### Tests

- identical branches report no state divergence
- stochastic siblings identify first differing resolution
- intervention sibling identifies intervention as divergence source

### Completion

Users/tools can answer "why did these timelines diverge?"

---

## Slice BR-06 — CLI branch workflow

### Goal

Expose practical multiverse operations.

### Depends on

BR-01 through BR-05.

### Shared code

**USE** branch/run/checkpoint identifiers, branch services, comparison records,
and existing application-service boundaries. The CLI must not implement branch
semantics itself.

### Packages

Typer.

### Method

Commands approximately:

- `dss branch list RUN_ID`
- `dss branch fork CHECKPOINT_ID [--seed ...]`
- `dss branch reroll ROUND_OR_RESOLUTION_ID`
- `dss branch intervene CHECKPOINT_ID ...`
- `dss branch compare BRANCH_A BRANCH_B`
- `dss branch activate BRANCH_ID`

"Activate" changes a user/workflow pointer; it never deletes siblings.

### Tests

CLI/service integration with JSON output.

### Completion

Timeline branching can be operated entirely through the application service/CLI.

---

## Upgrade qualification

Prove:

- historical immutability
- sibling independence
- deterministic replay per branch seed
- scoped reroll isolation
- ancestry acyclicity
- intervention atomicity
- comparison identifies first causal divergence
