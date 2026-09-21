# DSS post-MVP slice delivery and continuation prompt

Work in `/Users/k/Documents/Projects/dynamic-story-scafold` and follow the
repository's current `AGENTS.md` plus all applicable local instructions.

At the beginning of the task, save a complete durable copy of this prompt
outside the repository under
`/Users/k/.codex/durable-prompts/dynamic-story-scaffold/`. Keep that copy until
the continuation task has been created successfully or the entire tracker is
complete.

Synchronize and inspect `origin/main`, then read:

- `docs/releases/ROADMAP.md`
- `project/Plans/post-mvp-implementation-slices.md`
- `docs/implementation/README.md`
- the implementation document named by the first unchecked tracker item
- `docs/CORE_LIBRARY.md` and immediately relevant code/tests

Implement **only the first unchecked slice** in
`project/Plans/post-mvp-implementation-slices.md`. The tracker, not this prompt
or a previous task, determines the current slice. Preserve the release's
descriptive-prose outcome: user-authored sub-prose and compiled prose must stay
grounded in simulation truth, and renderer/provider wording must remain
downstream.

Use a fresh feature branch from current `main`. Implement the complete slice,
including focused tests, migrations, documentation, and installed behavior
required by its plan. Use RED/GREEN where behavior changes. Run the focused
tests while iterating, then the repository's full required local qualification,
package build, `./scripts/install.sh`, and installed-runtime checks when the
slice affects user-visible or installed behavior. Preserve unrelated work and
stage explicit paths.

Mark only that slice checked in the tracker as part of the same feature. Open a
pull request only after implementation and local qualification are complete.
The PR must describe the release/slice, architecture decisions, prose-language
impact, migrations/dependencies, and exact qualification performed. Wait for
all PR checks, mergeability, reviews, and policy status to reach stable terminal
success before merging. Merge the PR, verify its server-side merged state and
the updated `origin/main`, then return the primary checkout to clean current
`main` and delete the local/remote feature branch and temporary worktree.

If the completed item is a `REL-*` release gate, also verify that package and
installer versions match, build release artifacts from the merged commit,
create and push the annotated version tag, publish the GitHub release, and
verify the release target and assets. Do not tag an unmerged commit.

After merge and cleanup, re-read the tracker from updated `main`:

- If any unchecked slice remains, use the Codex `create_thread` MCP tool to
  create a **direct local task in the saved DSS project checkout** with the
  exact durable prompt copy as its prompt. Do not use a worktree for the
  continuation. Create the task only after the current PR is merged and cleanup
  is complete. Once task creation succeeds, delete the durable prompt copy and
  end this turn.
- If no unchecked slice remains, do not create another task. Delete the durable
  prompt copy, report that the post-MVP chain is complete, and end this turn.

Do not implement a later slice, start continuation early, reuse a merged branch,
or let generated prose invent events, appearances, state, visibility, or causal
relationships absent from its grounded inputs.
