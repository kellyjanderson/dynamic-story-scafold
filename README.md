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

## Build, package, and install

The repository has one cross-platform development command surface:

```bash
python dev.py test
python dev.py package
python dev.py build
python dev.py install
```

- `test` runs the test suite.
- `package` creates a wheel and source distribution and records the build plus artifact hashes in SQLite.
- `build` runs tests, then performs the tracked package build.
- `install` packages the current checkout, installs the freshly built wheel into the current Python environment, then executes the application installer.

Installed command-line entry points are:

```bash
dss install
dss paths
dss db status
dss db migrate
dss build
dss builds list
```

`dss-install` is also provided as a dedicated installer entry point.

### Platform-aware application data

The SQLite database is application state, not package data, so it is never written into the Python package directory.

By default, the installer uses the normal per-user data location for the host operating system:

- **macOS:** `~/Library/Application Support/dynamic-story-scaffold/story-scaffold.sqlite3`
- **Linux / other XDG Unix:** `$XDG_DATA_HOME/dynamic-story-scaffold/story-scaffold.sqlite3`, normally `~/.local/share/dynamic-story-scaffold/story-scaffold.sqlite3`
- **Windows:** the user's local application-data directory, under `dynamic-story-scaffold\story-scaffold.sqlite3`

The exact path can always be inspected with:

```bash
dss paths
```

For CI, portable installs, or managed deployments, set `DYNAMIC_STORY_SCAFFOLD_DATA_DIR` to override the application-data directory. Individual management commands can also use `--database PATH`.

The installer is idempotent: it creates the database if absent, applies pending schema migrations, preserves existing data, and records the installation.

### Database-backed build management

Builds are tracked in the same application database. A successful tracked build records:

- package version
- Git commit and branch when available
- project root and output directory
- build status and timestamps
- wheel/sdist artifact type
- artifact path
- byte size
- SHA-256 digest

`dss builds list` shows recent build records.

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

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```
