# Feature Upgrade — Evaluation, Feedback, and Large-Scale Exploration

## Outcome

Add structured human feedback, automated invariant checks, and controlled
multi-branch exploration.

Automated evaluation assists debugging/art direction. It does not become an
authority that rewrites simulation truth or human aesthetic judgment.

## Packages

Use:

- Hypothesis for invariant/property tests
- stdlib `concurrent.futures` for local parallel branch exploration when safe
- optionally add **polars** only when exploration result volume justifies a
  dataframe dependency; do not add it for a handful of runs

Do not introduce distributed infrastructure until actual workload requires it.

---

## Slice EV-01 — Structured feedback model

### Goal

Persist actionable user/art-director feedback against simulation or render
artifacts.

### Depends on

persistence/render asset IDs.

### Shared code

Feedback is its own domain; references existing run/branch/round/moment/asset IDs.

### Packages

SQLAlchemy/Alembic for persistence.

### Method

Feedback record:

- target type/ID
- category
- severity/importance
- freeform note
- optional structured dimensions
- author/source
- timestamp

Initial categories:

- simulation inconsistency
- action engagement
- continuity
- visual clutter
- focal hierarchy
- magic causality
- anatomy
- missing/extra actor
- renderer artifact

Do not translate feedback automatically into simulation mutations.

### Tests

Feedback can target multiple artifact types and remains historical.

### Completion

Human criticism becomes queryable data.

---

## Slice EV-02 — Simulation consistency validator

### Goal

Detect violations that can be checked mechanically.

### Depends on

full provenance.

### Shared code

Use snapshots/records/refs.

### Packages

No new package.

### Method

Checks include:

- referenced entities exist
- accepted operations committed exactly once
- component changes respect bounds/max delta
- actor health/fatigue valid
- branch ancestry valid
- round input/output checkpoint chain valid
- no proposal left nonterminal
- causal/event depth within recorded budgets
- replay matches stored output when requested

Return findings; do not auto-repair historical state.

### Tests

Fixtures with intentional corruption/invariant violations.

### Completion

A run can be audited independently of visual output.

---

## Slice EV-03 — Render consistency validator

### Goal

Compare RenderRequest/selected moment metadata against simulation truth.

### Depends on

render pipeline.

### Shared code

Use structured RenderRequest; avoid parsing final prompt when structured facts
are available.

### Packages

No CV dependency initially.

### Method

Check that:

- all described actors existed/visible in projection
- described action comes from selected causal records
- described effects are allowed visible semantics
- continuity references belong to expected lineage
- prompt compiler did not introduce unsupported facts

This validates data/prompt consistency, not whether pixels obeyed the prompt.

### Tests

Intentionally fabricated prompt/request facts are detected.

### Completion

Textual/render-request hallucination is mechanically detectable.

---

## Slice EV-04 — Multiverse batch exploration

### Goal

Explore many seeded futures from one checkpoint.

### Depends on

timeline branching.

### Shared code

Use branch service and semantic run entropy.

### Packages

- stdlib concurrent.futures

### Method

Given:

- checkpoint
- number of branches
- branch seed-generation rule
- horizon in rounds

create N child branches and advance them independently.

Parallel workers operate on detached state; durable commits remain short
transactions.

Never share a mutable `WorldState` between workers.

Record experiment/batch ID and branch seed assignment.

### Tests

- serial and parallel execution produce same per-branch results
- worker completion order irrelevant
- failure of one branch does not corrupt siblings
- requested branch count/horizon enforced

### Completion

DSS can sample many plausible futures from one moment.

---

## Slice EV-05 — Outcome summaries

### Goal

Summarize branch sets without inventing a single "correct" future.

### Depends on

EV-04.

### Shared code

Use state/round records.

### Packages

No new package initially; add Polars only after measured need.

### Method

Compute descriptive summaries such as:

- terminal actor health/state distribution
- environment-state distribution
- objective outcomes
- common action choices
- frequency of events/effects
- first-divergence categories

Keep raw counts and sample size.

Do not interpret frequency as normative desirability.

### Tests

Known fixture branch set yields expected counts/distributions.

### Completion

Users can inspect how sensitive a scenario is to stochastic choices.

---

## Slice EV-06 — Feedback-assisted comparison reports

### Goal

Combine branch/render differences with human feedback for review.

### Depends on

EV-01/EV-05 and cinematic/render pipeline.

### Shared code

Reporting layer only.

### Packages

No new package.

### Method

Generate structured report data:

- branch lineage
- causal divergence
- outcome summary
- selected moment differences
- render assets
- feedback grouped by category

Do not automatically train/change weights in this slice.

### Tests

Report references correct branch/artifact IDs and does not collapse sibling
histories.

### Completion

A reviewer can compare simulation futures and their visual results with attached
feedback.

---

## Upgrade qualification

Prove that exploration remains replayable, parallel completion order cannot
change semantic results, and validators never mutate or silently repair
historical records.
