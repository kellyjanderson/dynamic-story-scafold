# Dynamic Story Scaffold

Dynamic Story Scaffold is a Python foundation for **bounded stochastic story-world simulation**.

The core rule is:

> Randomness perturbs trajectories; it does not arbitrarily replace state.

The renderer, prose generator, or cinematic director is downstream. The simulator owns what is true, what can change, and how quickly it may change.

## Current scope

This first implementation provides:

- YAML-authored scene definitions.
- Scene setting and objectives.
- Environment elements made of independently dynamic components.
- Continuous bounds plus per-tick maximum change.
- Seeded jitter and replayable stochastic evolution.
- Named dynamics methods selected from YAML.
- Explicit discrete state transitions driven by events.
- Character identity separated from role/class.
- Character physical attributes, priorities, motivations, quirks, and initial state.
- Role abilities, modifiers, spell mechanics, and optional visual semantics.
- Creature definitions and behavior hints.
- A mutable runtime world state.
- External forcing so later actor/action systems can disturb the world without bypassing its bounds.

The next layer should add perception, intent selection, action resolution, actor-state changes, and cinematic moment selection.

## Source, build, installation, and runtime contexts

DSS deliberately separates four execution contexts.

### 1. Repository/development context

The Git checkout contains source, tests, documentation, migration sources, and
repository tooling. Hatch/Hatchling owns development environments and builds.

```bash
hatch run test
hatch run package
hatch run build
```

- `test` runs the repository test suite.
- `package` creates wheel/sdist artifacts and writes `dist/build-manifest.json`.
- `build` runs tests and then packages.

Repository/build tooling must **not** invoke the application CLI to build,
install, migrate, or qualify DSS.

Build provenance is a distribution artifact, not application state. The build
manifest records package version, Git commit/branch, artifact sizes, and SHA-256
digests without touching the runtime database.

### 2. Package installation context

Install a built wheel with a package manager or eventual OS installer. For
example:

```bash
python -m pip install dist/dynamic_story_scaffold-*.whl
```

Package installation creates the executable entry points but does not silently
initialize or migrate user application state.

### 3. Installer / technical-support maintenance context

The installed package provides a separate maintenance executable:

```bash
dss-maintain setup
dss-maintain db status
dss-maintain db migrate
```

`dss-maintain setup` is the normal post-install/upgrade setup operation. It
creates or upgrades application state and records the installed package.

`dss-maintain db migrate` is an explicit installer/support operation. Normal
runtime execution never runs Alembic migrations.

### 4. Runtime application context

The user-facing application CLI is only:

```bash
dss
```

Normal commands include:

```bash
dss paths
dss scene validate ...
dss run start ...
dss run advance ...
dss run show ...
dss round show ...
dss run replay ...
```

The runtime application assumes setup has already been completed. If its
database is missing or stale, it stops with a maintenance instruction instead
of creating or migrating state.

### Platform-aware application data

Mutable application state is never stored in or inferred from the Git checkout.
`platformdirs` selects the normal per-user location:

- **macOS:** `~/Library/Application Support/dynamic-story-scaffold/story-scaffold.sqlite3`
- **Linux / XDG Unix:** `$XDG_DATA_HOME/dynamic-story-scaffold/story-scaffold.sqlite3`
- **Windows:** the user's local application-data directory under
  `dynamic-story-scaffold\\story-scaffold.sqlite3`

Inspect the runtime location with:

```bash
dss paths
```

For CI, portable installs, or managed deployments,
`DYNAMIC_STORY_SCAFFOLD_DATA_DIR` overrides the application-data directory.

The source checkout, distribution artifacts, installed executables, and mutable
runtime state are separate contexts by design.

## Scene YAML

See `examples/hollow_bank.yaml` for a complete scene.

A dynamic environment element looks like this:

```yaml
environment:
  weather:
    components:
      wind_speed:
        initial: 2.5
        bounds: [0.0, 35.0]
        units: m/s
        dynamics:
          method: bounded_inertial
          max_delta: 1.25
          jitter: 0.35
          inertia: 0.86
          max_velocity: 1.0
```

The YAML specifies:

- **element**: e.g. weather, water, terrain, ecology
- **component**: e.g. wind speed or water level
- **initial**: initial truth
- **bounds**: absolute legal range
- **dynamics.method**: named Python evolution algorithm
- **max_delta**: maximum state change in one simulation tick
- **jitter**: stochastic perturbation
- **inertia**: resistance to sudden changes
- method-specific parameters such as `target`, `response`, or `max_velocity`

A scene may also define explicit discrete transitions:

```yaml
dam_state:
  kind: discrete
  initial: intact
  states: [intact, strained, leaking, breached, collapsed]
  transitions:
    intact:
      - to: strained
        event: dam_stressed
```

This prevents a dam from spontaneously jumping from intact to collapsed unless later action-resolution code emits the sequence of events that permits it.

## Dynamics methods

Built-in methods:

### `fixed`

Never changes.

### `bounded_random_walk`

Applies:

```text
delta = drift + external_forcing + gaussian_jitter
```

Then clamps the delta by `max_delta` and the resulting value by absolute bounds.

### `bounded_inertial`

Maintains a velocity/trend:

```text
impulse = drift + external_forcing + gaussian_jitter
velocity = inertia * previous_velocity + (1 - inertia) * impulse
```

Velocity may be limited with `max_velocity`; the final change is still limited by `max_delta`.

This is appropriate for values such as cloud cover, wind, water level, and flow speed where continuity matters.

### `bounded_target`

Moves gradually toward a target:

```text
delta = (target - value) * response + drift + forcing + jitter
```

It remains subject to `max_delta` and absolute bounds.

This is useful for slow relaxation toward an environmental equilibrium.

## External forcing

Actors and discrete events should influence the environment through forcing rather than setting state directly.

```python
from dynamic_story_scaffold import Simulation, load_scene

scene = load_scene("examples/hollow_bank.yaml")
simulation = Simulation(scene)

result = simulation.tick(
    forcing={
        "terrain.dam_integrity": -0.5,
        "water.turbidity": 0.2,
    },
    events=["dam_stressed"],
)
```

Even extreme forcing cannot make a continuous component change faster than its configured `max_delta`.

That is the mechanism that prevents changes such as a clear sky becoming an 80 mph thunderstorm in a single tick.

## Characters and roles

Identity and class/role are deliberately separate.

A character defines who the actor is:

```yaml
- id: reedshadow_merrit
  name: Merrit
  species: river_otter
  role: Reedshadow
  physical:
    strength: 0.72
    agility: 0.91
  priorities:
    - protect juveniles
  motivations:
    protect_holt: 0.95
  quirks:
    - prefers underwater approaches
```

The role defines learned capabilities:

```yaml
Reedshadow:
  combat_role: skirmisher
  preferred_range: close
  modifiers:
    stealth: 4
  abilities:
    - name: Submerged Flank
      kind: maneuver
      mechanics:
        approach: submerged
        positional_advantage: 0.35
```

Two characters with the same role can therefore make different decisions once the intent-selection layer combines abilities with motivations, priorities, quirks, perceptions, and circumstances.

## Spell definitions

Spell mechanics are defined before visual appearance.

```yaml
- name: Crosscurrent
  kind: spell
  mechanics:
    domain: hydrodynamic_control
    targeting: flow_region
    force_vector: 0.35
    ally_stability: 0.20
    enemy_stability: -0.15
  visual_semantics:
    - coherent water motion
    - flow direction may oppose gravity
    - luminous fish forms optional
```

A later cinematic layer may choose not to render overt magic at all if the physical consequence communicates the action better.

## Development

Hatch owns the repository development environment.

```bash
hatch run test
hatch run build
```

Do not use the repository environment as the installed application. Installed
package qualification must install the wheel into a separate environment and
use `dss-maintain` before exercising `dss`.
