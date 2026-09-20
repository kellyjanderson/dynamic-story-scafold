# MVP-04 — Baseline perception provider

## Repository / branch / base branch

- Repository: `kellyjanderson/dynamic-story-scafold`
- Assigned branch: `feature/mvp-04-baseline-perception`
- Base branch: `main`
- The Body of Work prepares this branch just-in-time from the current merged `main`.
- Follow `AGENTS.md`: implement only on this branch, open the PR only when this Work Order is complete, merge the PR when qualified, and do **not** delete the branch yourself.

## Dependencies

MVP-01 through MVP-03 must be merged.

## Context

Read these project documents before implementation:

- `AGENTS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/CORE_LIBRARY.md`
- `docs/implementation/README.md`
- `docs/implementation/01_MVP_SIMULATION_LOOP.md` — the MVP-04 slice is authoritative for this Work Order.

Existing shared types should be reused rather than duplicated. If implementation reveals a genuinely new cross-feature abstraction not declared here or in the plan, report the plan deviation explicitly.

## Goal

Implement a rules-based, non-omniscient perception provider sufficient for the semantic-zone MVP.

## Required work

- Use existing `PerceptionProvider`, `Observation`, `KnowledgeLevel`, `EntityRef`, `Position`, snapshots, and `RandomStreams`. Do not create competing observation/perception record types.
- Perception runs from one stable round snapshot.
- Baseline observations include self state, actors visible under simple same/adjacent-zone rules, obvious posture/injury, relevant environment facts, and recent audible/explicit events.
- Use machine-readable `Observation.fact` keys and structured `Observation.value`; prose belongs downstream.
- Represent uncertainty/confidence through semantic streams such as `perception / round-id / observer-id / subject-id / fact-key`.
- Hidden/unavailable information must be absent or UNKNOWN rather than leaked from canonical truth.
- Do not implement full geometric LOS, renderer descriptions, actor-memory persistence, or species-name special cases. Later spatial/sensory upgrades own those concerns.
- Provider must be pure with respect to canonical state.

## Packages / shared-code policy

Use the packages named above and in the authoritative MVP slice. For generic infrastructure, prefer mature packages already selected by the plan. Do not build replacement graph, migration, CLI, retry, persistence, or task-runner infrastructure.

Keep durable values/interfaces in shared core; keep perception, intent, arbitration, resolution, persistence, and CLI **policy** in their feature modules.

## Focused RED/GREEN coverage

Prove:
- two actors can receive different observations from the same snapshot;
- hidden/unavailable facts do not leak;
- same entropy replays uncertainty;
- unrelated RNG stream consumption does not change perception;
- provider cannot mutate canonical state/snapshot source;
- every Hollow Bank actor receives a valid observation tuple.

Classify new tests semantically:
- `unit`: narrow isolated behavior;
- `integration`: cross-component/application behavior;
- `regression`: only tests preserving a previously fixed failure.

If pytest markers are used and not yet registered, add marker registration to `pyproject.toml`.

## Qualification

Iterate with `unit`; classify coordinator+perception round coverage as `integration`. Final required targets then PR/merge/WORK_COMPLETE.

Do not open a PR merely to trigger CI while implementation is incomplete. GitHub CI runs only when the PR is opened, so PR creation is the final feature-qualification event.

## Completion

Merged baseline provider supplies actor-scoped, replayable, non-omniscient observations for Hollow Bank.
