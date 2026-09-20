# MVP-09 — Minimal simulation persistence and idempotent round commit

## Repository / branch / base branch

- Repository: `kellyjanderson/dynamic-story-scafold`
- Assigned branch: `feature/mvp-09-persistence`
- Base branch: `main`
- The Body of Work prepares this branch just-in-time from the current merged `main`.
- Follow `AGENTS.md`: implement only on this branch, open the PR only when this Work Order is complete, merge the PR when qualified, and do **not** delete the branch yourself.

## Dependencies

MVP-01 through MVP-08 must be merged.

## Context

Read these project documents before implementation:

- `AGENTS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/CORE_LIBRARY.md`
- `docs/implementation/README.md`
- `docs/implementation/01_MVP_SIMULATION_LOOP.md` — the MVP-09 slice is authoritative for this Work Order.

Existing shared types should be reused rather than duplicated. If implementation reveals a genuinely new cross-feature abstraction not declared here or in the plan, report the plan deviation explicitly.

## Goal

Persist enough run/branch/checkpoint/round history to resume and replay while keeping SQLite out of runtime coordination.

## Required work

- Use SQLAlchemy 2.x and Alembic already selected by the project. Create persistence models, not duplicate domain classes.
- Add durable minimum entities: SimulationRun, TimelineBranch, Checkpoint, SimulationRound, plus an operation/idempotency table only if actually needed.
- Run owns root seed and scene identity; root branch belongs to run; checkpoint belongs to branch and references predecessor; round references input/output checkpoints; branch stores active head checkpoint.
- Persist snapshots/history as JSON/plain data, never pickle.
- Add an Alembic migration; never rewrite the initial migration already shipped.
- Compute perception/intent/resolution outside DB write transactions.
- Persist one completed round + output checkpoint + branch-head advancement in one short transaction.
- Use stable round/operation IDs and uniqueness so retry cannot duplicate a durable round.
- DB rows are not runtime locks.
- Persistence failure must not partially advance the durable branch head.
- Keep model structurally branch-capable; user-facing branch operations remain Upgrade 02.

## Packages / shared-code policy

Use the packages named above and in the authoritative MVP slice. For generic infrastructure, prefer mature packages already selected by the plan. Do not build replacement graph, migration, CLI, retry, persistence, or task-runner infrastructure.

Keep durable values/interfaces in shared core; keep perception, intent, arbitration, resolution, persistence, and CLI **policy** in their feature modules.

## Focused RED/GREEN coverage

Integration coverage:
- run/root branch/root checkpoint creation;
- successful round persistence atomically advances head;
- duplicate round commit is idempotent or cleanly rejected with no duplicate;
- simulated transaction failure does not partially advance branch;
- loading input checkpoint + audit supports replay;
- migration upgrades a fresh temp database.

Add regression markers only for actual bugs discovered/fixed.

Classify new tests semantically:
- `unit`: narrow isolated behavior;
- `integration`: cross-component/application behavior;
- `regression`: only tests preserving a previously fixed failure.

If pytest markers are used and not yet registered, add marker registration to `pyproject.toml`.

## Qualification

Use `unit` and `integration`; before PR also request `[[AUTOMATION_TEST:installed]]` and `[[AUTOMATION_TEST:full]]`. Controller-required targets must remain green. Then PR/merge/WORK_COMPLETE.

Do not open a PR merely to trigger CI while implementation is incomplete. GitHub CI runs only when the PR is opened, so PR creation is the final feature-qualification event.

## Completion

Merged persistence can durably store/resume one branch-capable run and idempotently commit rounds.
