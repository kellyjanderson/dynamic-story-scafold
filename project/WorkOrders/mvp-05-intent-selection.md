# MVP-05 — Action candidates and utility intent selection

## Repository / branch / base branch

- Repository: `kellyjanderson/dynamic-story-scafold`
- Assigned branch: `feature/mvp-05-intent-selection`
- Base branch: `main`
- The Body of Work prepares this branch just-in-time from the current merged `main`.
- Follow `AGENTS.md`: implement only on this branch, open the PR only when this Work Order is complete, merge the PR when qualified, and do **not** delete the branch yourself.

## Dependencies

MVP-01 through MVP-04 must be merged.

## Context

Read these project documents before implementation:

- `AGENTS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/CORE_LIBRARY.md`
- `docs/implementation/README.md`
- `docs/implementation/01_MVP_SIMULATION_LOOP.md` — the MVP-05 slice is authoritative for this Work Order.

Existing shared types should be reused rather than duplicated. If implementation reveals a genuinely new cross-feature abstraction not declared here or in the plan, report the plan deviation explicitly.

## Goal

Generate legal data-driven action candidates and choose an inspectably scored intent without hard-coding role names.

## Required work

- Use `ActionIntent`, `ScoreTerm`, `ScoreBreakdown`, `ScoredOption`, role/ability definitions, observations, and semantic RNG.
- Generate candidates from authored role abilities plus generic baseline actions such as move, defend, observe, and explicit no-action.
- Filter impossible candidates before scoring.
- Score with inspectable terms: objective relevance, motivation, priority, role affinity, positional suitability, expected effect, resource cost, risk, recent-action repetition, quirk modifiers, and bounded decision jitter where data supports them.
- Do not NLP-parse free-text priorities/quirks into brittle rules. If machine behavior needs structure, extend the Hollow Bank YAML/schema with explicit tags/metadata and preserve human-readable text.
- Selection may use maximum utility or seeded weighted choice among near-optimal candidates; record the entire candidate score set and selected policy/sample.
- No legal candidate must yield explicit no-action rather than provider failure.
- Do not hard-code Reedshadow/Shellbreaker/etc.; shared engine policy must remain generic.
- Do not use an LLM in the MVP intent provider.

## Packages / shared-code policy

Use the packages named above and in the authoritative MVP slice. For generic infrastructure, prefer mature packages already selected by the plan. Do not build replacement graph, migration, CLI, retry, persistence, or task-runner infrastructure.

Keep durable values/interfaces in shared core; keep perception, intent, arbitration, resolution, persistence, and CLI **policy** in their feature modules.

## Focused RED/GREEN coverage

Prove:
- actors with same role but different motivations/metadata can choose differently;
- same entropy replays candidate scoring/selection;
- score contributions remain inspectable;
- impossible abilities are excluded;
- intent generation cannot mutate state;
- no legal candidate produces explicit no-action;
- Hollow Bank actors all produce valid intents.

Classify new tests semantically:
- `unit`: narrow isolated behavior;
- `integration`: cross-component/application behavior;
- `regression`: only tests preserving a previously fixed failure.

If pytest markers are used and not yet registered, add marker registration to `pyproject.toml`.

## Qualification

Use `unit` for scoring/candidate rules and `integration` for perception→intent flow. Final required targets, PR, merge, WORK_COMPLETE.

Do not open a PR merely to trigger CI while implementation is incomplete. GitHub CI runs only when the PR is opened, so PR creation is the final feature-qualification event.

## Completion

Merged rules-based intent provider produces valid data-driven intents for every MVP actor.
