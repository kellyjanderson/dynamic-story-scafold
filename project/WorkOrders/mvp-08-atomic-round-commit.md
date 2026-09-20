# MVP-08 — Aggregate, validate, and atomically commit a round

## Repository / branch / base branch

- Repository: `kellyjanderson/dynamic-story-scafold`
- Assigned branch: `feature/mvp-08-atomic-round-commit`
- Base branch: `main`
- The Body of Work prepares this branch just-in-time from the current merged `main`.
- Follow `AGENTS.md`: implement only on this branch, open the PR only when this Work Order is complete, merge the PR when qualified, and do **not** delete the branch yourself.

## Dependencies

MVP-01 through MVP-07 must be merged.

## Context

Read these project documents before implementation:

- `AGENTS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/CORE_LIBRARY.md`
- `docs/implementation/README.md`
- `docs/implementation/01_MVP_SIMULATION_LOOP.md` — the MVP-08 slice is authoritative for this Work Order.

Existing shared types should be reused rather than duplicated. If implementation reveals a genuinely new cross-feature abstraction not declared here or in the plan, report the plan deviation explicitly.

## Goal

Convert accepted round consequences into exactly one coherent next canonical state with no partial mutation or last-writer-wins behavior.

## Required work

- Use existing actor-update, effect, disturbance, component-ref, coordinator, claim, and snapshot contracts.
- Before canonical mutation, validate all accepted updates, confirm exclusive conflicts are arbitrated, centralize effect stacking, aggregate commutative actor/resource deltas, and aggregate environmental forcing by component.
- Construct a detached candidate next state from the current canonical state/snapshot.
- Apply accepted actor updates/effects and aggregate environment disturbances to that candidate.
- Evolve each dynamic environment component exactly once per tick from aggregate forcing/events.
- If any validation/application step fails, discard candidate and leave canonical state unchanged.
- Replace/commit canonical state only after candidate validates completely.
- Round audit must reference state-before/state-after checkpoint IDs or stable hashes plus intermediate arbitration/resolution records.
- Input/proposal order must not change the committed normalized state for identical entropy/context.

## Packages / shared-code policy

Use the packages named above and in the authoritative MVP slice. For generic infrastructure, prefer mature packages already selected by the plan. Do not build replacement graph, migration, CLI, retry, persistence, or task-runner infrastructure.

Keep durable values/interfaces in shared core; keep perception, intent, arbitration, resolution, persistence, and CLI **policy** in their feature modules.

## Focused RED/GREEN coverage

Prove:
- two forces to same component aggregate before one dynamics evolution;
- health/fatigue bounds hold;
- incompatible exclusive writes cannot silently overwrite;
- failed candidate commit leaves old state byte/structure equivalent;
- shuffled accepted-proposal order yields same next state;
- same input + entropy reproduces equivalent normalized snapshot;
- one full Hollow Bank round reaches a coherent next state.

Classify new tests semantically:
- `unit`: narrow isolated behavior;
- `integration`: cross-component/application behavior;
- `regression`: only tests preserving a previously fixed failure.

If pytest markers are used and not yet registered, add marker registration to `pyproject.toml`.

## Qualification

This is a broad integration slice: use `unit`, `integration`, and `full` locally. Required targets plus branch-diff-check must be green before PR. Merge then WORK_COMPLETE.

Do not open a PR merely to trigger CI while implementation is incomplete. GitHub CI runs only when the PR is opened, so PR creation is the final feature-qualification event.

## Completion

Merged coordinator advances a complete round through one validated atomic canonical commit.
