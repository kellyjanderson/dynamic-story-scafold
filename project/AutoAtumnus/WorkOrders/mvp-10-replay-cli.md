---
base: main
branch: feature/mvp-10-replay-cli
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
- mvp-09-persistence
id: mvp-10-replay-cli
legacy_source: project/WorkOrders/mvp-10-replay-cli.md
project: kellyjanderson/dynamic-story-scafold
scope:
  may_read:
  - '**'
  owns:
  - '**'
title: MVP-10 — Replay service and CLI inspection
---

# Codex-native execution overlay

This Work Order was converted from `project/WorkOrders/mvp-10-replay-cli.md`. This overlay overrides any
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

# MVP-10 — Replay service and CLI inspection

## Repository / branch / base branch

- Repository: `kellyjanderson/dynamic-story-scafold`
- Assigned branch: `feature/mvp-10-replay-cli`
- Base branch: `main`
- The Body of Work prepares this branch just-in-time from the current merged `main`.
- Follow `AGENTS.md`: implement only on this branch, open the PR only when this Work Order is complete, merge the PR when qualified, and do **not** delete the branch yourself.

## Dependencies

MVP-01 through MVP-09 must be merged.

## Context

Read these project documents before implementation:

- `AGENTS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/CORE_LIBRARY.md`
- `docs/implementation/README.md`
- `docs/implementation/01_MVP_SIMULATION_LOOP.md` — the MVP-10 slice is authoritative for this Work Order.

Existing shared types should be reused rather than duplicated. If implementation reveals a genuinely new cross-feature abstraction not declared here or in the plan, report the plan deviation explicitly.

## Goal

Expose the complete MVP through application services/CLI and prove that a persisted Hollow Bank round can be reproduced exactly from its stored checkpoint and entropy context.

## Required work

- Use application services; keep simulation policy and SQLAlchemy transaction logic out of Typer command functions.
- Add CLI surface approximately: `dss scene validate PATH`, `dss run start PATH [--seed N]`, `dss run advance RUN_OR_BRANCH_ID`, `dss run show ...`, `dss round show ROUND_ID`, `dss run replay ROUND_ID`. Refine naming only for Typer ergonomics.
- Support `--json` output for automation/orchestration.
- Replay service loads stored input checkpoint, run/root/branch entropy context, scene/rules identity, and round audit inputs needed to reproduce the same normalized output.
- Compare replayed output against stored output checkpoint and report mismatch clearly.
- JSON round output should expose IDs/lineage, root/branch entropy context, perceptions/intents, stochastic arbitration/resolution audit, state diff, and terminal statuses at a useful level without dumping opaque Python objects.
- Unknown/malformed IDs produce clear user errors, not tracebacks where avoidable.
- Do not add rendering, user-facing branch creation/reroll, or external LLM decision providers.

## Packages / shared-code policy

Use the packages named above and in the authoritative MVP slice. For generic infrastructure, prefer mature packages already selected by the plan. Do not build replacement graph, migration, CLI, retry, persistence, or task-runner infrastructure.

Keep durable values/interfaces in shared core; keep perception, intent, arbitration, resolution, persistence, and CLI **policy** in their feature modules.

## Focused RED/GREEN coverage

End-to-end integration:
- validate Hollow Bank scene;
- start persisted run through service/CLI;
- advance one complete round;
- inspect JSON output;
- replay stored round and match output checkpoint;
- unknown IDs and invalid scene paths fail clearly;
- repeat replay remains idempotent and does not advance branch.

Classify new tests semantically:
- `unit`: narrow isolated behavior;
- `integration`: cross-component/application behavior;
- `regression`: only tests preserving a previously fixed failure.

If pytest markers are used and not yet registered, add marker registration to `pyproject.toml`.

## Qualification

Use `unit` plus `integration`; before PR request `full`, `installed`, and `package` in addition to required controller targets. Open/merge final MVP PR and emit WORK_COMPLETE after merge. Automation cleans branch.

Do not open a PR merely to trigger CI while implementation is incomplete. GitHub CI runs only when the PR is opened, so PR creation is the final feature-qualification event.

## Completion

The merged MVP can start, advance, inspect, persist, and replay a complete Hollow Bank round from the CLI with no renderer.
