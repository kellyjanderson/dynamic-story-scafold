# v0.3.0 — Spatial and Perception Fidelity

## Outcome

Replace the MVP's coarse semantic-zone perception with a richer but still
bounded spatial/sensory model.

This upgrade improves what actors can know and where actions can occur. It does
not change the coordinator's mutation/arbitration ownership.

Descriptive language becomes situated in this release. Authored environmental,
place, and sensory sub-prose is eligible only when supported by topology,
distance, visibility, sensory access, and the selected point of view.

## Packages

Use:

- existing **networkx** for semantic zone/topology graphs
- add **shapely** only when 2D polygon/segment geometry is introduced for
  containment, intersection, and line-of-sight obstruction
- existing Hypothesis for spatial invariants/property tests

Do not build custom computational geometry that Shapely already provides.

Do not introduce a 3D physics engine.

---

## Slice SP-01 — Explicit scene topology

### Goal

Turn zone names into an authored topology rather than opaque strings.

### Depends on

MVP state/Position model.

### Shared code

**EXTEND** spatial shared values only with durable topology references.

Feature policy belongs in a spatial service/module.

### Packages

- networkx

### Method

Add authored spatial zones with:

- stable zone ID
- optional kind/tags
- adjacency
- traversal cost/category
- environmental attributes such as water depth/elevation when relevant
- optional containment hierarchy

Build an in-memory graph from scene definitions.

Use the graph for:

- adjacency
- shortest semantic path
- neighborhood queries
- reachable-within-N steps

Keep topology data immutable during a round snapshot.

### Expected files

- schema/loader additions
- `spatial/topology.py` or equivalent
- example YAML update
- tests

### Tests

- invalid adjacency references fail scene validation
- disconnected zones are allowed but reported correctly
- shortest path/reachability independent of YAML mapping order
- Hollow Bank topology expresses bank/log/shallow/channel relationships

### Completion

Semantic positions have real connectivity semantics.

### Do not

- infer adjacency from names
- add geometric collision yet

---

## Slice SP-02 — Coordinate-capable positions and movement ranges

### Goal

Support continuous coordinates alongside semantic zones.

### Depends on

SP-01.

### Shared code

**USE/EXTEND** `Position`; do not create a parallel vector type unless actual
vector operations require one.

### Packages

- stdlib `math`

### Method

Define scene coordinate convention explicitly:

- units
- axis meaning
- optional zone-local versus scene-global coordinates

Add helpers for:

- distance
- range category
- movement budget
- zone membership when authored directly

An actor may have a semantic zone with coordinates. The zone remains useful for
coarse behavior; coordinates refine distance/reach.

Movement proposals specify destination and cost; they do not mutate position.

### Tests

- distances and range thresholds
- movement cannot exceed movement budget without an explicit ability/modifier
- coordinate state serializes/replays
- semantic-only scenes continue to work

### Completion

Action eligibility can use real distance without requiring full geometry.

---

## Slice SP-03 — 2D geometry, obstacles, cover, and line of sight

### Goal

Add practical visibility/cover geometry for scenes that provide it.

### Depends on

SP-02.

### Shared code

**USE** positions/refs; geometry shapes are spatial-feature data, not generic
core records.

### Packages

- **shapely**

### Method

Represent optional scene geometry as Shapely-compatible primitives:

- walkable/water polygons
- obstacle polygons
- occluding segments/polygons
- cover regions

Use Shapely for:

- point containment
- segment intersection
- nearest distance
- simple line-of-sight obstruction

Do not rasterize the whole world and do not implement collision physics.

Geometry is optional. Semantic-zone fallback remains valid.

### Tests

- obstacle blocks sight
- partial geometry absent → fallback behavior
- actors on opposite sides of an occluder do not receive direct visual facts
- geometry serialization uses authored plain data, not pickled Shapely objects

### Completion

Baseline visual perception can depend on actual occlusion where geometry exists.

---

## Slice SP-04 — Sensory profiles

### Goal

Generalize perception beyond vision without hard-coding species into the engine.

### Depends on

SP-01 to SP-03.

### Shared code

**USE** `Observation`, `KnowledgeLevel`, semantic RNG streams.

Add shared types only if the concept is cross-provider and durable, such as a
sensor-channel identifier.

### Packages

No new package.

### Method

Author sensor capabilities as data/tags/modifiers:

- visual
- auditory
- pressure/vibration
- scent
- tactile/contact
- role/magic-specific channels

A perception rule declares which channel can observe which fact class and what
environment factors degrade it.

Examples:

- turbidity reduces visual confidence underwater
- pressure sensing may reveal motion without identity
- sound may reveal event direction/zone but not exact posture

Do not write `if species == "river_otter"` in generic perception code.

### Tests

- same event produces different facts through different channels
- pressure observation can reveal motion without leaking identity
- environmental modifiers affect confidence
- authored custom sensory channel works without engine changes

### Completion

The Bubble Augur scenario can be represented as data-driven sensory capability,
not special code.

---

## Slice SP-05 — Actor knowledge and memory

### Goal

Distinguish current perception from what an actor remembers/believes.

### Depends on

SP-04.

### Shared code

**EXTEND** actor runtime state or add a dedicated knowledge-state object.
Do not overload canonical world truth with beliefs.

### Packages

No new package.

### Method

Maintain actor-specific belief records containing:

- subject/fact key
- last observed value
- certainty/confidence
- observation timestamp
- source channel
- optional decay/expiry policy

When current perception does not include a fact, decision logic may use remembered
knowledge at reduced confidence.

Belief update is a controlled actor-state update at commit, not mutation during
perception.

Contradictory observations should be reconciled by explicit policy:

- newer evidence
- more reliable channel
- weighted confidence
- retain ambiguity when unresolved

### Tests

- actors remember previously seen target
- confidence decays according to rule
- contradictory channels do not silently overwrite without audit
- actor beliefs can disagree while canonical world state stays singular

### Completion

Intent selection can reason from imperfect knowledge over time.

---

## Slice SP-06 — Spatial action eligibility and path-aware intent context

### Goal

Expose spatial facts to generic candidate/action rules.

### Depends on

SP-05.

### Shared code

**USE** action/intention contracts. Do not put tactical policy in spatial core.

### Packages

networkx/Shapely already selected.

### Method

Provide query services such as:

- distance/range
- same/adjacent zone
- reachable
- line of sight
- cover level
- path cost
- accessible water/terrain tags

Ability prerequisites reference these query concepts declaratively.

Replace MVP placeholder prerequisites such as `accessible_water` with explicit
query evaluation.

### Tests

- close/melee ability invalid at long distance
- submerged flank requires reachable water route
- cover changes expected-effect/risk inputs without mutating intent engine
- no geometry scene continues using zone rules

### Completion

Spatial eligibility is reusable by perception, intent, reaction, and cinematic
layers.

---

## Slice SP-07 — Spatial and sensory descriptive projection

### Goal

Project spatial truth into a structured set of description-ready place and
sensory facts.

### Depends on

SP-01 through SP-06.

### Shared code

**USE** positions, topology, visibility, sensory observations, knowledge levels,
and stable entity/component references. Do not place prose policy in geometry.

### Packages

No new package.

### Method

Allow scene zones, environmental elements, and sensory profiles to provide
optional human-authored sub-prose keyed by stable IDs and applicability. Build a
projection service for omniscient and actor-perspective descriptions. It emits
facts/sub-prose with source references, distance/occlusion context, and sensory
channel. An actor-perspective projection cannot include facts the actor cannot
perceive or know.

### Tests

- an occluded visual detail is omitted while an audible detail remains eligible
- actor perspective does not leak omniscient position/state
- distance and scale select the appropriate authored detail
- scenes without sub-prose still produce valid structured projections

### Completion

Downstream prose can describe where subjects are and what is perceptible without
inventing spatial or sensory access.

---

## Upgrade qualification

Use Hollow Bank scenarios that deliberately separate:

- visible vs pressure-detected targets
- occluded allies
- land/water paths
- near/far engagement ranges

Property-test that spatial queries are stable under actor dictionary ordering
and that provider reads never mutate snapshots.
