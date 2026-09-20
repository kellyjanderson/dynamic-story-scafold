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
