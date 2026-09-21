---
base: main
branch: feature/mvp-02-round-coordinator
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
dependencies:
- mvp-01-run-lineage-snapshots
id: mvp-02-round-coordinator
legacy_source: project/WorkOrders/mvp-02-round-coordinator.md
project: kellyjanderson/dynamic-story-scafold
scope:
  may_read:
  - '**'
  owns:
  - '**'
title: MVP-02 — Round coordinator skeleton and phase state machine
---

# Codex-native execution overlay

This Work Order was converted from `project/WorkOrders/mvp-02-round-coordinator.md`. This overlay overrides any
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

# MVP-02 — Round coordinator skeleton and phase state machine

## Repository / branch / base branch

- Repository: `kellyjanderson/dynamic-story-scafold`
- Assigned branch: `feature/mvp-02-round-coordinator`
- Base branch: `main`
- The Body of Work prepares this branch just-in-time from the current merged `main`.
- Follow `AGENTS.md`: implement only on this branch, open the PR only when this Work Order is complete, merge the PR when qualified, and do **not** delete the branch yourself.

## Dependencies

MVP-01 must already be merged into `main`.

## Context

Read these project documents before implementation:

- `AGENTS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/CORE_LIBRARY.md`
- `docs/implementation/README.md`
- `docs/implementation/01_MVP_SIMULATION_LOOP.md` — the MVP-02 slice is authoritative for this Work Order.

Existing shared types should be reused rather than duplicated. If implementation reveals a genuinely new cross-feature abstraction not declared here or in the plan, report the plan deviation explicitly.

## Goal

Create the single-writer round coordinator and explicit phase state machine before any real perception or action policy is added.

## Required work

- Read the repository directives and MVP-02 slice.
- Implement a coordinator whose canonical phase order is snapshot → perceive → intent → normalize proposals → reaction/arbitration → resolve → collect consequences → commit → record.
- Add durable shared execution values only when they are cross-feature contracts: phase enum, proposal terminal-status enum, causal/work-budget value object, and round execution/audit metadata.
- Keep coordinator policy outside `dynamic_story_scaffold.core`.
- Add a hard non-reentrancy guard: attempting to advance a round while one is active must fail immediately with a clear domain error.
- Providers receive immutable snapshots from MVP-01, never mutable `WorldState`.
- Every proposal entering coordination must end in exactly one terminal status: accepted, rejected, canceled, deferred, failed, or overflowed. No waiting state may survive round exit.
- A no-op/empty-provider round must terminate through all phases and produce an auditable record.
- Exceptions before commit must leave canonical state unchanged.
- Do not add concurrency, real perception policy, or action mechanics in this Work Order.

## Packages / shared-code policy

Use the packages named above and in the authoritative MVP slice. For generic infrastructure, prefer mature packages already selected by the plan. Do not build replacement graph, migration, CLI, retry, persistence, or task-runner infrastructure.

Keep durable values/interfaces in shared core; keep perception, intent, arbitration, resolution, persistence, and CLI **policy** in their feature modules.

## Focused RED/GREEN coverage

RED/GREEN coverage:
- recorded phase order;
- recursive advance rejected;
- provider/phase exception before commit leaves canonical state untouched;
- every submitted placeholder proposal receives terminal status;
- no-op round terminates and advances simulation time only according to the explicit coordinator policy;
- coordinator never hands mutable canonical state to provider fixtures.

Classify new tests semantically:
- `unit`: narrow isolated behavior;
- `integration`: cross-component/application behavior;
- `regression`: only tests preserving a previously fixed failure.

If pytest markers are used and not yet registered, add marker registration to `pyproject.toml`.

## Qualification

Use `unit` while iterating. Add integration-marked coverage for coordinator + current simulation state if it crosses module boundaries. Final required targets: `unit`, `integration`, `branch-diff-check`. Then PR, merge, WORK_COMPLETE; automation deletes the branch.

Do not open a PR merely to trigger CI while implementation is incomplete. GitHub CI runs only when the PR is opened, so PR creation is the final feature-qualification event.

## Completion

A merged coordinator can execute an auditable no-op round safely with immutable phase input and no partial mutation.
