# MVP-07 — Bounded reactions, events, and effects

## Repository / branch / base branch

- Repository: `kellyjanderson/dynamic-story-scafold`
- Assigned branch: `feature/mvp-07-reactions-events-effects`
- Base branch: `main`
- The Body of Work prepares this branch just-in-time from the current merged `main`.
- Follow `AGENTS.md`: implement only on this branch, open the PR only when this Work Order is complete, merge the PR when qualified, and do **not** delete the branch yourself.

## Dependencies

MVP-01 through MVP-06 must be merged.

## Context

Read these project documents before implementation:

- `AGENTS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/CORE_LIBRARY.md`
- `docs/implementation/README.md`
- `docs/implementation/01_MVP_SIMULATION_LOOP.md` — the MVP-07 slice is authoritative for this Work Order.

Existing shared types should be reused rather than duplicated. If implementation reveals a genuinely new cross-feature abstraction not declared here or in the plan, report the plan deviation explicitly.

## Goal

Support interception and effect/event chains through explicit bounded queues/windows so causal interaction cannot recurse or explode indefinitely.

## Required work

- Use/extend `Effect`, `EffectStacking`, `WorldEvent`, stable operation IDs, causal metadata, and coordinator work budgets.
- Implement explicit reaction windows; never recursively call coordinator/resolver.
- Primary accepted proposals may open declared reaction windows. Eligible reactors propose from the stable snapshot plus trigger.
- Reactions are arbitrated using existing dependency/conflict machinery and may cancel/redirect/modify proposals.
- Generated events/effects enter explicit generation queues.
- Enforce configurable hard limits for reaction depth, causal depth, events per round, resolutions per round, and deferrals.
- Budget exhaustion must produce recorded overflow/deferred terminal results, not silent dropping or timeout.
- Centralize effect stacking by target + effect identity/kind under REPLACE/STACK/STRONGEST/REFRESH.
- Duplicate operation IDs must not commit twice.
- Do not add background timers; effect scheduling uses simulation time.

## Packages / shared-code policy

Use the packages named above and in the authoritative MVP slice. For generic infrastructure, prefer mature packages already selected by the plan. Do not build replacement graph, migration, CLI, retry, persistence, or task-runner infrastructure.

Keep durable values/interfaces in shared core; keep perception, intent, arbitration, resolution, persistence, and CLI **policy** in their feature modules.

## Focused RED/GREEN coverage

Include explicit regressions:
- Hold-the-Line style interception;
- intercept → counter-intercept cycle;
- event A → effect B → event A loop;
- self-refreshing effect;
- causal/event budget exhaustion;
- duplicate operation ID;
- Hypothesis bounded reaction/event structures always terminate and leave no waiting proposals.

Classify new tests semantically:
- `unit`: narrow isolated behavior;
- `integration`: cross-component/application behavior;
- `regression`: only tests preserving a previously fixed failure.

If pytest markers are used and not yet registered, add marker registration to `pyproject.toml`.

## Qualification

Use `unit` and focused tests while implementing; request `integration` for coordinator/reaction flow and `full` before PR. Required targets green at final HEAD; PR/merge/WORK_COMPLETE.

Do not open a PR merely to trigger CI while implementation is incomplete. GitHub CI runs only when the PR is opened, so PR creation is the final feature-qualification event.

## Completion

Merged reaction/event/effect runtime always terminates within configured work budgets and produces auditable terminal outcomes.
