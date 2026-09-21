---
base: main
branch: feature/mvp-06-action-resolution
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
- mvp-05-intent-selection
id: mvp-06-action-resolution
legacy_source: project/WorkOrders/mvp-06-action-resolution.md
project: kellyjanderson/dynamic-story-scafold
scope:
  may_read:
  - '**'
  owns:
  - '**'
title: MVP-06 — Action resolution and typed consequences
---

# Codex-native execution overlay

This Work Order was converted from `project/WorkOrders/mvp-06-action-resolution.md`. This overlay overrides any
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

# MVP-06 — Action resolution and typed consequences

## Repository / branch / base branch

- Repository: `kellyjanderson/dynamic-story-scafold`
- Assigned branch: `feature/mvp-06-action-resolution`
- Base branch: `main`
- The Body of Work prepares this branch just-in-time from the current merged `main`.
- Follow `AGENTS.md`: implement only on this branch, open the PR only when this Work Order is complete, merge the PR when qualified, and do **not** delete the branch yourself.

## Dependencies

MVP-01 through MVP-05 must be merged.

## Context

Read these project documents before implementation:

- `AGENTS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/CORE_LIBRARY.md`
- `docs/implementation/README.md`
- `docs/implementation/01_MVP_SIMULATION_LOOP.md` — the MVP-06 slice is authoritative for this Work Order.

Existing shared types should be reused rather than duplicated. If implementation reveals a genuinely new cross-feature abstraction not declared here or in the plan, report the plan deviation explicitly.

## Goal

Resolve accepted intents into auditable typed consequences without directly mutating canonical world state.

## Required work

- Use `ActionResolution`, `ActorUpdate`, `DisturbanceSet`, `WorldForcing`, `WorldEvent`, `Effect`, `Outcome`, `TimeSpan`, and semantic RNG.
- Resolver consumes immutable snapshot + accepted intent and returns proposals only.
- Implement a small generic check model sufficient for MVP authored abilities: base capability/modifier, situational modifiers, target resistance/difficulty, seeded sample, degree of success.
- Use semantic stream `resolution / round-id / actor-id / intent-id` or an equally stable key.
- Record sample, modifiers, difficulty/opposition, result degree, and explanation/audit data.
- Map outcomes to data-defined consequences where practical.
- Environmental consequences must be forcing/events, never direct component assignment.
- Actor consequences must be typed `ActorUpdate` objects.
- Mechanics remain independent of visual semantics. No real-world physics engine.

## Packages / shared-code policy

Use the packages named above and in the authoritative MVP slice. For generic infrastructure, prefer mature packages already selected by the plan. Do not build replacement graph, migration, CLI, retry, persistence, or task-runner infrastructure.

Keep durable values/interfaces in shared core; keep perception, intent, arbitration, resolution, persistence, and CLI **policy** in their feature modules.

## Focused RED/GREEN coverage

Prove:
- successful physical action yields typed actor consequences;
- terrain-impact action yields forcing/event and never direct terrain mutation;
- same entropy replays the sampled resolution;
- different seeds may alter stochastic outcome legitimately;
- failed resolution leaves no hidden state mutation;
- audit data can reconstruct why the outcome occurred.

Classify new tests semantically:
- `unit`: narrow isolated behavior;
- `integration`: cross-component/application behavior;
- `regression`: only tests preserving a previously fixed failure.

If pytest markers are used and not yet registered, add marker registration to `pyproject.toml`.

## Qualification

Use `unit` for resolver math and `integration` for intent→resolution. Final required targets; run `full` before PR if shared records/interfaces change. Merge and WORK_COMPLETE.

Do not open a PR merely to trigger CI while implementation is incomplete. GitHub CI runs only when the PR is opened, so PR creation is the final feature-qualification event.

## Completion

Merged resolver handles every MVP intent and emits only typed actor/effect/environment proposals.
