# Repository Agent Directives

These rules apply to implementation work in this repository unless the user
explicitly instructs otherwise.

## Git and GitHub workflow

Every feature or fix must use a feature branch.

1. **Start from the current integration branch.**
   - Normally this is `main`.
   - Update/inspect the integration branch before creating work.
2. **Create a feature branch before modifying code.**
   - Use a descriptive name such as `feature/<feature-name>` or
     `fix/<problem-name>`.
   - Do not implement directly on `main`.
3. **Implement the entire feature on that branch.**
   - Keep related code, tests, migrations, and documentation together.
   - Make incremental commits as useful.
   - Run local qualification during development.
4. **Do not open the pull request until the feature is complete and ready for
   qualification/review.**
   - CI is intentionally PR-open-only and costs money.
   - Do not use PR creation as a development checkpoint.
5. **Open a pull request from the feature branch to its intended integration
   branch.**
   - The PR should describe the completed feature, important architecture
     decisions, migrations/dependencies, and qualification performed.
6. **Merge the PR when it is ready to be merged.**
   - Required tests/qualification must be complete.
   - Do not continue feature development on the branch after merge.
7. **Delete the feature branch after the PR is merged.**
   - Remote branch deletion is part of completing the feature lifecycle.
   - Start the next feature from the newly integrated branch, not from the old
     feature branch.

### Important consequences

- One feature lifecycle = **branch → implementation → local qualification → PR
  → merge → branch deletion**.
- Do not stack new feature work on an unmerged feature branch unless the user
  explicitly requests a stacked workflow.
- Do not reuse a merged feature branch for subsequent work.
- If a feature reveals separate follow-up work, finish/merge the current feature
  first, then create a new branch for the follow-up.
- Documentation and migrations that are part of a feature travel with that
  feature branch.
- Direct commits to `main` require explicit user instruction.

## Tooling principle

Use mature existing packages and platform tooling for generic concerns. Custom
code should implement Dynamic Story Scaffold-specific behavior rather than
recreating general build, migration, graph, retry, CLI, persistence, or similar
infrastructure.
