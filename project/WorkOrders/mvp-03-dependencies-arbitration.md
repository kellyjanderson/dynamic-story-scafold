# MVP-03 — Claims, dependency graph, and bounded arbitration

## Repository / branch / base branch

- Repository: `kellyjanderson/dynamic-story-scafold`
- Assigned branch: `feature/mvp-03-dependencies-arbitration`
- Base branch: `main`
- The Body of Work prepares this branch just-in-time from the current merged `main`.
- Follow `AGENTS.md`: implement only on this branch, open the PR only when this Work Order is complete, merge the PR when qualified, and do **not** delete the branch yourself.

## Dependencies

MVP-01 and MVP-02 must be merged.

## Context

Read these project documents before implementation:

- `AGENTS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/CORE_LIBRARY.md`
- `docs/implementation/README.md`
- `docs/implementation/01_MVP_SIMULATION_LOOP.md` — the MVP-03 slice is authoritative for this Work Order.

Existing shared types should be reused rather than duplicated. If implementation reveals a genuinely new cross-feature abstraction not declared here or in the plan, report the plan deviation explicitly.

## Goal

Give the coordinator an explicit finite dependency/conflict model so cycles become data to arbitrate rather than waits or recursive control flow.

## Required work

- Add `networkx` as a runtime dependency for graph operations. Add `Hypothesis` to the Hatch development environment for property testing. Do not implement graph algorithms by hand.
- Extend proposal/action records with stable proposal/operation ID, typed read set, write set, exclusive claims, dependency references, causal parent, and causal depth.
- Use typed refs/subresource keys; avoid ambiguous dotted strings at subsystem boundaries.
- Build a directed dependency graph per round. Use NetworkX topological operations for acyclic regions and strongly connected components for cycles.
- SCCs are not errors. Route cyclic components into an explicit arbitration policy.
- Arbitration input: stable conflict ID, candidates, immutable snapshot, rule/context, and semantic RNG stream.
- Arbitration output: selected/terminal outcomes plus an inspectable audit record including stochastic rule, weights/modifiers, semantic stream key, sampled value, and chosen result when randomness is used.
- Key stochastic arbitration from semantic identity, e.g. `arbitration / round-id / conflict-id`.
- Define write classes: aggregatable, exclusive, rule-governed. Do not let Python collection iteration order decide outcomes.
- Different seeds may legitimately choose different valid results; same state/proposals/entropy must replay.

## Packages / shared-code policy

Use the packages named above and in the authoritative MVP slice. For generic infrastructure, prefer mature packages already selected by the plan. Do not build replacement graph, migration, CLI, retry, persistence, or task-runner infrastructure.

Keep durable values/interfaces in shared core; keep perception, intent, arbitration, resolution, persistence, and CLI **policy** in their feature modules.

## Focused RED/GREEN coverage

Coverage must include:
- acyclic graph resolves in declared dependency order;
- two-node and three-node cycles terminate;
- same seed replays stochastic SCC arbitration;
- different seed may choose a different valid candidate;
- shuffled proposal input order gives same result for same entropy;
- conflicting exclusive claims cannot both be accepted;
- compatible aggregatable claims remain eligible together;
- Hypothesis generates bounded dependency graphs and proves termination/no waiting proposals.

Classify new tests semantically:
- `unit`: narrow isolated behavior;
- `integration`: cross-component/application behavior;
- `regression`: only tests preserving a previously fixed failure.

If pytest markers are used and not yet registered, add marker registration to `pyproject.toml`.

## Qualification

Use `unit` frequently; use `integration` for coordinator + graph arbitration. Final required targets plus `[[AUTOMATION_TEST:full]]` if property tests materially alter broad behavior. Then PR/merge/WORK_COMPLETE.

Do not open a PR merely to trigger CI while implementation is incomplete. GitHub CI runs only when the PR is opened, so PR creation is the final feature-qualification event.

## Completion

Merged coordinator can reduce any finite bounded proposal graph to finite terminal outcomes without blocking or accidental order dependence.
