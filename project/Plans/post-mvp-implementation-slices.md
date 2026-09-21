# DSS post-MVP implementation slices

This is the authoritative ordered completion tracker for releases v0.2.0
through v0.9.0. Implement exactly the first unchecked item. A checked item means
its feature PR is merged into `main`; for a `REL-*` item it also means the tag
and GitHub release were verified.

Use [`project/Prompts/implement-next-post-mvp-slice.md`](../Prompts/implement-next-post-mvp-slice.md)
for the self-chaining task. Slice definitions are authoritative in the linked
implementation documents.

## `REL-*` release-slice contract

Every release item has the following implementation contract:

### Goal

Ship the completed version as an installed, documented, tagged DSS release.

### Depends on

Every feature slice listed earlier in the same version section is checked and
merged.

### Shared code

Use existing package metadata, `scripts/install.sh`, maintenance setup,
application CLI, release notes, and GitHub release process. Do not create a
second version source.

### Packages

No new dependency solely for releasing.

### Method

Update `pyproject.toml` and the installer to the section's semantic version;
extend the installer/package version-drift test; write release notes describing
implemented user-visible behavior and honest exclusions; run the full suite,
clean package build, isolated pipx install, maintenance setup, and installed CLI
smoke/replay appropriate to the release. Run the cumulative product-loop proof
for that release from `docs/PRODUCT_LOOP.md`. Merge the release PR first. Tag that
exact merged commit with an annotated `vX.Y.Z` tag, publish the GitHub release
with its artifacts, and verify tag target, asset digests, and clean `main`.

### Tests

Package and installer versions match; distributions contain the intended
version; isolated install and runtime qualification pass; release tag and assets
resolve to the merged commit; the release's cumulative product-loop proof passes
through installed commands and fake providers where paid calls are optional.

### Completion

The GitHub release is published from current `main`, the tracker item is merged
checked, and local/remote release branches are cleaned up.

## v0.2.0 — Possible futures

- [ ] BR-01 — Branch service and lineage invariants
- [ ] BR-02 — Full-future reroll
- [ ] BR-03 — Scoped stochastic reroll
- [ ] BR-04 — Explicit state intervention branches
- [ ] BR-05 — Player/GM directed turn
- [ ] BR-06 — Branch comparison
- [ ] BR-07 — CLI branch and directed-turn workflow
- [ ] BR-08 — Branch-grounded descriptive comparison
- [ ] REL-0.2.0 — Qualify, version, tag, and publish v0.2.0

Plan: [`docs/implementation/02_TIMELINE_BRANCHING.md`](../../docs/implementation/02_TIMELINE_BRANCHING.md).

## v0.3.0 — Situated perception

- [ ] SP-01 — Explicit scene topology
- [ ] SP-02 — Coordinate-capable positions and movement ranges
- [ ] SP-03 — 2D geometry, obstacles, cover, and line of sight
- [ ] SP-04 — Sensory profiles
- [ ] SP-05 — Actor knowledge and memory
- [ ] SP-06 — Spatial action eligibility and path-aware intent context
- [ ] SP-07 — Spatial and sensory descriptive projection
- [ ] REL-0.3.0 — Qualify, version, tag, and publish v0.3.0

Plan: [`docs/implementation/03_SPATIAL_PERCEPTION.md`](../../docs/implementation/03_SPATIAL_PERCEPTION.md).

## v0.4.0 — Visible consequences

- [ ] IX-01 — Formal resource/read/write claim model
- [ ] IX-02 — Timing and initiative policy
- [ ] IX-03 — Movement and occupancy conflicts
- [ ] IX-04 — Holds, grapples, and relational state
- [ ] IX-05 — Area/group targeting
- [ ] IX-06 — Persistent effect scheduler
- [ ] IX-07 — Advanced environment coupling
- [ ] IX-08 — Adversarial interaction qualification
- [ ] IX-09 — Authored sub-prose and condition composition
- [ ] REL-0.4.0 — Qualify, version, tag, and publish v0.4.0

Plan: [`docs/implementation/04_INTERACTIONS_EFFECTS.md`](../../docs/implementation/04_INTERACTIONS_EFFECTS.md).

## v0.5.0 — Narratable moments

- [ ] CO-01 — Cinematic moment domain model
- [ ] CO-02 — Candidate extraction
- [ ] CO-03 — Inspectable cinematic scoring
- [ ] CO-04 — Visibility projection
- [ ] CO-05 — Camera hints and composition constraints
- [ ] CO-06 — Continuity and novelty memory
- [ ] CO-07 — Grounded moment brief and concise prose
- [ ] REL-0.5.0 — Qualify, version, tag, and publish v0.5.0

Plan: [`docs/implementation/05_CINEMATIC_OBSERVER.md`](../../docs/implementation/05_CINEMATIC_OBSERVER.md).

## v0.6.0 — Descriptive prose and rendering

- [ ] RP-01 — Prose and visual style profile model
- [ ] RP-02 — DescriptionRequest and renderer-neutral RenderRequest
- [ ] RP-03 — Descriptive prose compiler
- [ ] RP-04 — Renderer adapter protocol and fake adapter
- [ ] RP-05 — OpenAI image adapter
- [ ] RP-06 — Asset store and provenance
- [ ] RP-07 — Continuation/reference-image workflow
- [ ] RP-08 — Prose/render CLI and application workflow
- [ ] RP-09 — Keyframe description sequence contract
- [ ] RP-10 — Directed turn to image/keyframe workflow
- [ ] REL-0.6.0 — Qualify, version, tag, and publish v0.6.0

Plan: [`docs/implementation/06_RENDER_PIPELINE.md`](../../docs/implementation/06_RENDER_PIPELINE.md).

## v0.7.0 — Durable story projects

- [ ] PW-01 — Project/campaign and scene revision model
- [ ] PW-02 — Full simulation provenance
- [ ] PW-03 — Repository/service boundary
- [ ] PW-04 — Crash recovery and incomplete operations
- [ ] PW-05 — Application-data layout
- [ ] PW-06 — Import/export bundle
- [ ] PW-07 — Workflow-oriented CLI
- [ ] PW-08 — Durable prose library and description provenance
- [ ] PW-09 — Resumable campaign play session
- [ ] REL-0.7.0 — Qualify, version, tag, and publish v0.7.0

Plan: [`docs/implementation/07_PERSISTENCE_WORKFLOW.md`](../../docs/implementation/07_PERSISTENCE_WORKFLOW.md).

## v0.8.0 — Description evaluation and exploration

- [ ] EV-01 — Structured feedback model
- [ ] EV-02 — Simulation consistency validator
- [ ] EV-03 — Render consistency validator
- [ ] EV-04 — Multiverse batch exploration
- [ ] EV-05 — Outcome summaries
- [ ] EV-06 — Spatial-frequency distribution analysis
- [ ] EV-07 — Feedback-assisted comparison reports
- [ ] EV-08 — Grounded prose evaluation
- [ ] REL-0.8.0 — Qualify, version, tag, and publish v0.8.0

Plan: [`docs/implementation/08_EVALUATION_EXPLORATION.md`](../../docs/implementation/08_EVALUATION_EXPLORATION.md).

## v0.9.0 — Constrained model assistance

- [ ] EP-01 — Provider-neutral decision request/response schema
- [ ] EP-02 — Provider adapter protocol and fake adapter
- [ ] EP-03 — OpenAI intent provider
- [ ] EP-04 — Failure and fallback policy
- [ ] EP-05 — Comparative provider evaluation
- [ ] EP-06 — Constrained prose realization provider
- [ ] REL-0.9.0 — Qualify, version, tag, and publish v0.9.0

Plan: [`docs/implementation/09_EXTERNAL_DECISION_PROVIDERS.md`](../../docs/implementation/09_EXTERNAL_DECISION_PROVIDERS.md).
