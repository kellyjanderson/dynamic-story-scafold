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


## Execution-context boundaries

DSS has three command contexts that must not be conflated.

### Repository/build context

Repository work uses Hatch, pytest, scripts, and other source-tree tooling.

- Build/package/test commands must not invoke the user-facing `dss` CLI.
- Build provenance belongs with distribution artifacts, not in the application database.
- Repository tooling may depend on development-only packages that are not runtime dependencies.

### Production installation contract

The production/user installation path is one command from a current source
checkout:

```bash
./scripts/install.sh
```

That installer delegates package build/environment/command exposure to pipx,
using the project's standard PEP 517/Hatchling metadata, then performs
runtime-state setup.

Do not reimplement virtual-environment, package-installation, application
exposure, or build-front-end behavior in DSS scripts. Use established packaging
tools. Do not document Hatch, pip, venv, Alembic, or `dss-maintain` as
required steps for normal users.

### Installer/maintenance context

Installed-state setup and schema migration belong to `dss-maintain`.

- `dss-maintain setup` initializes or upgrades application state after package installation.
- `dss-maintain db migrate` is an explicit installer/technical-support operation.
- Normal runtime code must never call Alembic migration functions implicitly.

### Runtime application context

The user-facing application command is `dss`.

- `dss` may inspect or use prepared runtime state.
- If runtime state is missing or schema-stale, fail with a maintenance instruction.
- Runtime execution must not assume a Git checkout, Hatch, `dist/`, build metadata, or repository paths exist.

The invariant is:

> Source/build tooling does not execute the application to build or install itself, and the installed application does not reach back into the source/repository context.

## Tooling principle

Use mature existing packages and platform tooling for generic concerns. Custom
code should implement Dynamic Story Scaffold-specific behavior rather than
recreating general build, migration, graph, retry, CLI, persistence, or similar
infrastructure.
