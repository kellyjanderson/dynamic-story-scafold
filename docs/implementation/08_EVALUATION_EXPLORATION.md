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
- high-spatial-frequency interference / competing detail
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

## Slice EV-06 — Spatial-frequency distribution analysis

### Goal

Measure whether rendered fine detail is concentrated where it supports focal
hierarchy or spread across the frame strongly enough to create perceptual
interference.

This is **not** a generic image-noise detector.

### Depends on

rendered assets, style profiles, and asset provenance.

### Shared code

**USE** render asset references, style-profile frequency/detail settings, and
selected-moment/camera metadata where available.

Keep measured image-analysis data in the evaluation subsystem. Do not feed it
directly into canonical simulation state.

### Packages

Add only for this slice:

- **numpy** for FFT/frequency-band energy calculations
- **Pillow** for image loading/normalization
- **scikit-image** for established edge/gradient measurements such as Sobel
  response rather than implementing image filters manually

### Method

Analyze rendered images at several complementary levels:

1. **Spatial-frequency energy**
   - convert to a defined luminance representation
   - compute 2D FFT magnitude
   - summarize energy in low/mid/high radial frequency bands
   - normalize for image dimensions so comparisons across output sizes remain
     meaningful

2. **Local edge/detail density**
   - compute an established gradient/edge response
   - summarize by tiles/regions rather than only one global number
   - report concentration versus uniform distribution of fine detail

3. **Microcontrast distribution**
   - measure local luminance variance/gradient energy at small scales
   - distinguish a focal cluster of high-frequency detail from frame-wide high
     microcontrast

4. **Focal-versus-secondary comparison**
   - when the render request or later detection tooling provides focal
     regions/masks, compare high-frequency energy inside versus outside those
     regions
   - otherwise report tiled/global distributions without inventing focal masks

The output should be descriptive metrics, not a binary "noisy/clean" verdict.

A technically clean image with meaningful fur, droplets, foliage, bark, and
reflections may still be perceptually noisy when those high-frequency signals
compete uniformly across the frame.

Store analyzer/version/parameters with results so measurements remain
comparable.

### Tests

Use synthetic fixtures with controlled frequency content:

- broad smooth shapes with low high-frequency energy
- fine checker/detail concentrated in one focal region
- the same fine detail spread uniformly across the frame
- identical signal plus random pixel noise to demonstrate that random noise and
  structured high-frequency signal are distinguishable cases
- resized versions produce comparable normalized band summaries within
  tolerance

Assert that the analyzer reports distributions/metrics and does not assign an
aesthetic pass/fail judgment.

### Completion

Evaluation can quantify the specific high-spatial-frequency competition problem
observed during prototyping without conflating it with random image noise.

---

## Slice EV-07 — Feedback-assisted comparison reports

### Goal

Combine branch/render differences with human feedback for review.

### Depends on

EV-01, EV-05, EV-06, and cinematic/render pipeline.

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
- spatial-frequency/detail-distribution metrics where available

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
