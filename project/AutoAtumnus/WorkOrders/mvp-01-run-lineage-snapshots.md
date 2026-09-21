---
base: main
branch: feature/mvp-01-run-lineage-snapshots
capabilities:
  mcp:
    optional:
    - codex_app
    - github
completion:
  delivery: pull_request
  merge: agent
  required_checks:
  - unit
  - integration
  - branch-diff-check
dependencies: []
id: mvp-01-run-lineage-snapshots
legacy_source: project/WorkOrders/mvp-01-run-lineage-snapshots.md
project: kellyjanderson/dynamic-story-scafold
scope:
  may_read:
  - '**'
  owns:
  - '**'
title: MVP-01 — Run identity, lineage, and immutable snapshots
---

# Codex-native execution overlay

This Work Order was converted from `project/WorkOrders/mvp-01-run-lineage-snapshots.md`. This overlay overrides any
browser-era lifecycle language retained below for traceability.

- Work directly with the repository using Codex tools; do not emit CGCA marker
  strings or wait for browser automation.
- Run the required checks yourself and preserve commands/results as completion
  evidence.
- Own the authorized feature-branch, commit, pull-request, merge, checkout, and
  branch-cleanup lifecycle required by the repository.
- Return the Auto-Atumnus structured completion result. Any error or missing
  capability enters agent repair; it is not a reason to stop the Body.

## Auto-Atumnus completion report

Return outcome, summary, repository branch/HEAD/PR/merge evidence, every
required validation command and result, artifacts, deferred work, and any
remaining error through the adapter's structured result channel.

# Migrated Work Order

# MVP-01 — Run identity, lineage, and immutable snapshots

## Repository / branch / base branch

- Repository: `kellyjanderson/dynamic-story-scafold`
- Assigned branch: `feature/mvp-01-run-lineage-snapshots`
- Base branch: `main`
- The Body of Work prepares this branch just-in-time from the current merged `main`.
- Follow `AGENTS.md`: implement only on this branch, open the PR only when this Work Order is complete, merge the PR when qualified, and do **not** delete the branch yourself.

## Dependencies

None beyond the shared-core foundation already merged into `main`.

## Context

Read these project documents before implementation:

- `AGENTS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/CORE_LIBRARY.md`
- `docs/implementation/README.md`
- `docs/implementation/01_MVP_SIMULATION_LOOP.md` — the MVP-01 slice is authoritative for this Work Order.

Existing shared types should be reused rather than duplicated. If implementation reveals a genuinely new cross-feature abstraction not declared here or in the plan, report the plan deviation explicitly.

## Goal

Introduce the minimum run/branch/checkpoint identity model and detached serializable world snapshots so every later round is replayable and branch-capable without implementing user-facing branch operations yet.

## Required work

- Read `AGENTS.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/CORE_LIBRARY.md`, and slice MVP-01 in `docs/implementation/01_MVP_SIMULATION_LOOP.md` before editing.
- Add durable shared identifiers for run, branch, checkpoint, and round. Prefer small frozen dataclasses/newtypes using stdlib `uuid`; do not invent a generic ID framework.
- Add an immutable run-context record containing run ID, root branch ID, chosen root seed, scene identity/revision information available at this stage, and initial checkpoint identity.
- Treat `scene.simulation.seed` only as an optional default. Explicit run seed overrides it; missing seed generates and exposes one.
- Add a detached `WorldSnapshot` representation suitable for provider input, persistence, hashing, and replay. It must contain plain serializable Python data and must not alias nested mutable state in canonical `WorldState`.
- Add conversion helpers between current `WorldState` and snapshot data without pickling.
- Preserve existing shared-core contracts and avoid introducing branch-operations, reroll commands, or campaign persistence.
- If test markers are introduced, register `integration` and `regression` in pytest configuration rather than leaving unknown-marker warnings.

## Packages / shared-code policy

Use the packages named above and in the authoritative MVP slice. For generic infrastructure, prefer mature packages already selected by the plan. Do not build replacement graph, migration, CLI, retry, persistence, or task-runner infrastructure.

Keep durable values/interfaces in shared core; keep perception, intent, arbitration, resolution, persistence, and CLI **policy** in their feature modules.

## Focused RED/GREEN coverage

Focused RED/GREEN coverage must prove:
- explicit run seed overrides scene default;
- scene default becomes run seed when no explicit seed is supplied;
- absent default/explicit seed produces a generated seed that can replay semantic streams;
- mutating a snapshot or nested snapshot collection cannot mutate canonical state;
- snapshot serialization/deserialization preserves normalized actor/environment state;
- root run/branch/checkpoint identities remain stable for the run.

Keep these primarily unit tests. Add an integration-marked test only if behavior crosses a real application/persistence boundary.

Classify new tests semantically:
- `unit`: narrow isolated behavior;
- `integration`: cross-component/application behavior;
- `regression`: only tests preserving a previously fixed failure.

If pytest markers are used and not yet registered, add marker registration to `pyproject.toml`.

## Qualification

During implementation request `the relevant project-native check` as needed. Before PR/merge, ensure controller-required `unit`, `integration`, and `branch-diff-check` are green at the final feature HEAD. Open and merge the PR according to `AGENTS.md`. Do not delete the feature branch; automation owns post-merge deletion.

Do not open a PR merely to trigger CI while implementation is incomplete. GitHub CI runs only when the PR is opened, so PR creation is the final feature-qualification event.

## Completion

The feature is merged into `main`; a run can be instantiated with an immutable, serializable root checkpoint and explicit replay seed/lineage, and the worker then emits `the structured completion result`.
