# Dynamic Story Scaffold — Implementation Plan

## Purpose

Dynamic Story Scaffold (DSS) is a bounded stochastic world simulation for generating coherent, stateful stories and cinematic scene observations.

The central rule is:

> Randomness perturbs trajectories; it does not arbitrarily replace state.

The simulation determines what is true. Actors perceive that world imperfectly, choose actions according to their character and capabilities, and create disturbances. The world responds within physical, ecological, narrative, and rate-of-change constraints. A downstream cinematic observer selects meaningful moments from the resulting state transitions for prose, image, animation, or other rendering.

DSS is not an image-prompt generator with state attached. The renderer is an observer of the simulation.

---

## Architectural principles

### 1. Definitions, state, and dynamics are separate

**Definitions** describe what can exist and what is possible.

Examples:

- biome
- environmental components
- character traits
- roles/classes
- abilities and spells
- terrain transitions
- bounds
- dynamics methods

**State** describes what is currently true.

Examples:

- current cloud cover
- current water level
- actor position
- current injury
- current dam integrity
- active effects
- actor beliefs

**Dynamics** describe how state may change.

Examples:

- maximum change per tick
- inertia
- stochastic jitter
- valid discrete transitions
- action consequences
- environmental forcing

No subsystem should directly overwrite state when an equivalent bounded state transition exists.

### 2. Actors create disturbances; the world creates consequences

The simulation should not invent spectacle merely because spectacle would be dramatic.

Actors:

- choose actions
- cast abilities
- move
- strike
- defend
- manipulate terrain
- react to perceived threats

Those actions produce forces, events, and attempted state changes.

The world then resolves them through:

- current conditions
- actor capability
- target resistance
- terrain
- uncertainty
- randomness
- bounds
- transition rules

### 3. Mechanics precede visual semantics

An ability definition describes what the ability does before describing how it might look.

For example, a hydrodynamic spell should first specify:

- target region
- force vector
- stability changes
- duration
- range
- costs

Visual semantics such as glowing fish, luminous currents, altered reflections, or nearly invisible pressure changes are optional observer-layer interpretations.

### 4. Character identity is separate from role/class

A character definition describes the individual:

- physical attributes
- motivations
- priorities
- fears
- attachments
- quirks
- knowledge
- temperament

A role definition describes learned or innate capabilities:

- abilities
- modifiers
- preferred engagement range
- tactical affordances
- resource use

Two characters with the same role should make different decisions when their motivations, perceptions, physical limits, or histories differ.

### 5. Randomness is layered and bounded

Different random processes should remain separate:

- action resolution uncertainty
- decision jitter
- environmental stochastic variation
- rare environmental events
- perception uncertainty
- initiative/timing variation

Every stochastic process should be seedable and replayable.

Randomness should normally affect a trajectory, not replace it.

### 6. Time matters

Continuous state changes must have rate limits.

Examples:

- cloud cover cannot jump from clear to storm-black in one tick
- water level cannot instantly rise several meters without a forcing event capable of causing it
- wind cannot jump to hurricane force without passing through intermediate state
- fatigue accumulates and recovers over time
- terrain damage progresses through physically plausible transitions

Discrete transitions require explicit prerequisites or events.

### 7. The simulation is renderer-independent

A completed simulation round should be usable by:

- image generation
- prose generation
- animation
- storyboard generation
- game UI
- replay/debug tools
- analytics

Rendering-specific concerns must not leak backward into world truth.


### 8. The simulation must never block on causal dependencies

The simulation should avoid logical "wait until X finishes" relationships inside
a round.

Instead:

- every phase reads a stable snapshot
- actors/systems emit proposals rather than mutating shared state
- dependencies and contested resources are declared explicitly
- conflicts are arbitrated by explicit rules that may include seeded randomness
- resolved changes are committed at a phase boundary
- a phase never recursively re-enters itself or an earlier phase

This is the primary protection against logical deadlocks, livelocks, circular
reactions, order-dependent state corruption, and replay divergence.

---

# Shared core library

Status: implemented foundation.

Concerns reused by multiple system layers live in
`dynamic_story_scaffold.core`. Feature modules should consume these contracts
rather than creating local equivalents.

Shared primitives currently include:

- stable actor/entity/component/target references
- replayable semantic random streams
- semantic-zone and coordinate-capable positions
- time spans
- effects and stacking semantics
- weighted score breakdowns and generic scored options
- perception knowledge levels
- observations
- action intents
- typed actor updates
- action outcomes/resolutions
- world forcing/events grouped as disturbances
- immutable tick and round records
- provider protocols for perception, intent selection, and action resolution

Actor definitions also share a common `ActorDefinition` base, and runtime
characters/creatures share one normalized `ActorState`.

Important boundary:

> Resolution produces actor updates and world disturbances. It does not bypass
> actor/environment state transition rules.

Randomness is similarly isolated by semantic namespace. Consuming decision or
perception randomness cannot change environment evolution for the same run/branch entropy context.

See `docs/CORE_LIBRARY.md` for the contracts and invariants.

# Run seeds, checkpoints, and timeline branches

Randomness belongs primarily to a **simulation run**, not to the scene
definition.

The scene may contain an optional default seed for examples, tests, or a
deliberately reproducible authored scenario. When a run starts, that value is
copied into the run unless the caller supplies another seed. The active run then
owns the seed used to derive all semantic random streams.

A run's history is a **branchable directed acyclic graph**, not a destructive
linear log.

Conceptually:

```text
scene definition
      |
      v
run A (root seed)
      |
      +-- checkpoint R1 -- R2 -- R3 -- R4
                           |     |
                           |     +-- branch C from pre-R3 checkpoint
                           |
                           +-- branch B from post-R2 checkpoint
```

A branch contains:

- a stable branch ID
- parent branch/run ID
- parent checkpoint ID
- branch point semantics: before intent, before resolution, after round, or
  explicit intervention
- a branch entropy seed/salt
- optional intervention metadata
- only the history/state that diverges after the branch point

State before the fork is referenced, not copied unnecessarily.

## Branching semantics

A branch may be created to:

- reroll a disliked stochastic outcome
- choose a different actor intent
- inject a deliberate world-state intervention
- compare alternative strategies
- explore many stochastic futures from one checkpoint
- return to an earlier preferred timeline without destroying later branches

Changing randomness never edits an already committed historical round.
A reroll creates a sibling future from the checkpoint immediately before the
chosen decision/resolution.

Semantic random streams allow the scope of divergence to be controlled.

A full branch may change all future entropy by incorporating the branch seed into
every post-fork stream. A narrower reroll may later replace only one semantic
stream, for example:

`resolution / round-17 / blackjaw / tail-sweep`

Unrelated environment, perception, or actor streams need not change.

## Replay identity

A stochastic result is replayable from:

- scene-definition revision/hash
- checkpoint/state identity
- branch lineage
- root run seed
- branch entropy seed/salt
- semantic stream key
- provider/rules version
- recorded external inputs, if any

The system must therefore distinguish **replayable stochastic behavior** from
**deterministic behavior**. Outcomes may be random; provenance may not be
ambiguous.

## Persistence model

The durable history model should eventually represent:

- simulation run
- timeline branch
- checkpoint
- round
- intent/resolution/event/effect records
- branch intervention
- active-head selection

A branch should reference its parent checkpoint and store only divergent
history. Checkpoints may be materialized snapshots for fast resume while the
event/round records remain the audit trail.

This model provides timeline branching / multiverse simulation as a natural
consequence of seeded replay rather than as a separate simulation engine.

---

# Execution safety and interaction model

The combination of simultaneous actions, reactions, effects, environment
dynamics, persistence, and future external providers creates several classes of
system-interaction failure that must be handled explicitly.

## Risk assessment

| Failure mode | Example | Required mitigation |
| --- | --- | --- |
| Circular dependency | Holtwarden waits to see where Currentcaller moves while Currentcaller waits for Holtwarden's interception | No blocking waits; resolve declared dependencies as a graph |
| Reaction recursion | attack → intercept → counter-intercept → new intercept | Finite reaction windows and a hard causal-depth budget |
| Livelock | actors repeatedly replan in response to one another without state progress | Replanning occurs only at the next decision window unless an explicit bounded reaction exists |
| Starvation | a low-priority actor is perpetually interrupted | Bounded deferral plus explicit fairness policy, optionally using seeded stochastic arbitration |
| Conflicting writes | two actions move the same actor or claim the same object | Explicit write/claim sets and rule-based or seeded stochastic arbitration |
| Order dependence | dictionary iteration changes which action wins | Stable ordering and semantic RNG streams; never depend on container iteration order |
| Event feedback loop | dam event creates an effect which emits the same dam event again in the same tick | Queued event generations, idempotency keys, causal-depth/event budgets |
| Oscillating state | one effect raises a value while another immediately lowers it and each retriggers the other | Aggregate forcing once, then evolve each dynamic component once per tick |
| Nested advancement | an effect callback calls `tick()` while the current tick is unresolved | The coordinator is non-reentrant; callbacks may only emit proposals |
| Partial-state reads | one actor perceives pre-commit state while another sees half-applied updates | Immutable phase snapshots and atomic phase commit |
| Retry duplication | a retried provider/action applies the same effect twice | Stable operation IDs and idempotent commit semantics |
| Database writer contention | multiple long SQLite write transactions overlap | One short write transaction per commit; never hold a DB transaction during simulation/provider work |
| External-provider stall | an LLM or renderer call never returns while state is locked | No state/DB locks across external calls; timeout/cancel/fallback outside the commit transaction |
| Causal explosion | AoE/reactions generate exponentially more events | Per-round event, reaction, and causal-node budgets with explicit overflow status |

## Single-writer coordinator

The simulation coordinator is the only component allowed to commit canonical
world state.

Feature providers may:

- read immutable snapshots
- return observations
- return intents
- return action-resolution proposals
- return actor updates
- return effects
- return world disturbances

They may not directly advance the simulation clock or mutate canonical world
state.

The initial engine should remain single-threaded at the commit layer even if
perception, scoring, or external-provider work is later evaluated concurrently.

This deliberately replaces lock coordination with **single-writer phase
barriers**.

## Snapshot → propose → arbitrate → commit

Every mutable phase follows the same transaction shape:

1. **Snapshot** — freeze the canonical state visible to the phase.
2. **Propose** — providers compute proposed actions/changes from that snapshot.
3. **Declare dependencies** — proposals expose targets, claims, read/write sets,
   reaction relationships, and timing.
4. **Arbitrate** — the coordinator resolves conflicts and cycles without
   mutating canonical state. Arbitration may be stochastic, but must use
   semantic seeded random streams so replay is reproducible.
5. **Commit** — accepted changes are applied exactly once.
6. **Record** — immutable history captures inputs, arbitration, outcomes, and
   committed changes.

No provider can observe a half-committed phase.

## Dependency graph and cycle handling

Action/reaction dependencies should be represented as a directed graph.

The coordinator should:

1. topologically resolve acyclic portions
2. detect strongly connected components
3. never "wait" for a strongly connected component to resolve itself
4. send each cyclic component to an explicit simultaneous-conflict policy

A cyclic group may be resolved by:

- simultaneous opposed checks
- initiative/timing comparison
- mutually compatible merge
- explicit cancellation
- seeded stochastic choice
- weighted random arbitration
- deterministic tie-break where randomness is not desired
- deferral to the next decision window

The chosen rule, random stream identity, and sampled value must be recorded in
the round history whenever stochastic arbitration is used.

Cycles are therefore **data to resolve**, not execution waits.

## Resource claims and write sets

Actions should eventually declare the state they intend to read, write, or
claim.

Examples:

- actor position
- posture
- inventory item
- exclusive terrain location
- held/grappled target
- environmental component
- shared resource

Writes fall into categories:

### Commutative/aggregatable writes

Examples:

- multiple forces on `terrain.dam_integrity`
- health/fatigue deltas
- compatible resource deltas

These are aggregated before bounded application.

### Exclusive writes

Examples:

- two actors both acquire the same unique object
- two incompatible destinations for one actor
- mutually exclusive posture/state changes

These require arbitration. Arbitration may be deterministic or stochastic
depending on the domain rule.

### Rule-governed writes

Effects use their declared stacking semantics:

- replace
- stack
- strongest
- refresh

Each dynamic environment component is evolved **once per tick** from the
aggregate forcing for that tick. An action cannot cause the same component to
advance its dynamics multiple times inside one tick.

## Event queue semantics

Events are not synchronously recursive callbacks.

Maintain explicit queues by generation:

- events emitted by the current resolution phase
- events eligible for the current bounded reaction window
- events deferred to the next phase/tick

Each event should eventually have:

- stable event/operation ID
- source
- target
- causal parent
- causal depth
- generation/tick
- payload

The engine must enforce configurable limits for:

- maximum reaction depth
- maximum causal depth
- maximum events per round
- maximum resolutions per round

Exceeding a budget produces a recorded overflow/deferred result rather than
continuing indefinitely.

## Reaction windows

Reactions are explicit bounded phases, not arbitrary callbacks.

Rules:

- a primary intent may open one or more defined reaction windows
- eligible reactors propose reactions from the same stable snapshot plus the
  triggering intent/event
- reactions have explicit timing/priority; equal or overlapping cases may use
  seeded stochastic arbitration
- reactions may alter/cancel/redirect proposals
- a reaction may not recursively invoke the coordinator
- reaction-to-reaction chains consume a finite causal budget
- once a reaction window closes, later consequences are scheduled for a future
  window or tick

This prevents infinite intercept/counter-intercept loops.

## Progress and starvation guarantees

Every round must make monotonic scheduler progress even if world state does not
change.

The coordinator must guarantee that:

- each phase has a finite work budget
- every proposal reaches a terminal status: accepted, rejected, canceled,
  deferred, failed, or overflowed
- no proposal remains "waiting"
- deferred proposals carry a bounded deferral count
- fairness rules prevent permanent starvation where fairness is semantically
  appropriate; those rules may include weighted seeded randomness

A round may legitimately produce no physical change, but its scheduler must
always terminate.

## Idempotency and retries

Simulation commit operations must be idempotent.

Provider calls, persistence writes, and renderer calls may eventually be
retried, but a retry must not duplicate:

- damage
- resource consumption
- effects
- events
- build/history rows
- rendered-asset links

Use stable IDs for run, round, intent, resolution, event, effect, and commit
operations where persistence/retry requires them.

## Persistence transaction boundaries

SQLite is a single-writer database and should be treated accordingly.

Rules:

- simulation computation occurs outside write transactions
- external provider calls occur outside write transactions
- renderer calls occur outside write transactions
- one coordinator commit persists the completed round/state/history in a short
  transaction
- database rows never act as runtime locks between simulation components
- if the persistence commit fails, canonical in-memory advancement is not
  considered durable and recovery/retry uses the same operation IDs

If multi-process execution is introduced later, coordination should use an
established queue/database mechanism rather than ad-hoc SQLite locking.

## Stable execution order and stochastic replay

Execution order must be stable, but **outcomes do not need to be deterministic**.

A contradiction, tie, opposed action, resource claim, or cyclic dependency may
be resolved with randomness when that produces better simulation behavior.

The requirement is:

> Same initial state + same proposals + same run/branch entropy context = same sampled outcome.

Never derive semantic outcomes from accidental execution order such as:

- dict iteration
- set iteration
- database row order without `ORDER BY`
- coroutine completion order
- wall-clock timing

When randomness is part of arbitration, use a semantic random stream keyed from
the run seed and the conflict identity, for example:

`arbitration / round / conflict-id`

The round record should retain enough information to explain and replay the
choice:

- arbitration rule
- candidate set
- weights/modifiers
- random stream key
- sampled value
- selected outcome

This allows genuinely stochastic simulation while preserving replayability and
debuggability.

## Failure isolation

A failed subsystem should not leave the round partially committed.

Examples:

- perception provider failure → recorded provider failure/fallback
- intent provider failure → safe fallback intent or explicit no-action
- action resolver failure → failed resolution
- persistence failure → no durable round commit
- renderer failure → simulation remains valid; rendering can retry separately

Rendering is always downstream and can never hold simulation progress hostage.

---

# System layers

## Layer 1 — Scene definition

YAML is the primary authoring format.

A scene definition should contain:

- scene setting
- environment potentials
- terrain
- ecology
- roles/classes
- abilities/spells
- character definitions
- non-player creatures
- objectives
- simulation timing
- optional default seed configuration; actual entropy is owned by a simulation run

The YAML should specify named dynamics methods rather than arbitrary executable code.

### Scene setting

Defines relatively stable context:

- biome
- season
- time of day
- scale
- location type
- broad objectives
- tags
- initial narrative situation

### Environment potentials

Environment elements are collections of dynamic components.

Initial categories:

- weather
- hydrology
- terrain
- ecology
- illumination
- visibility

Each continuous component may define:

- initial value
- legal bounds
- units
- dynamics method
- maximum delta per tick
- inertia
- jitter
- drift
- method-specific parameters

Each discrete component may define:

- legal states
- initial state
- allowed transitions
- prerequisite events
- transition probabilities where appropriate

### Character definitions

Character definitions should include:

- stable ID
- display name
- species
- physical traits
- motivations
- priorities
- quirks
- relationships
- initial knowledge
- initial state
- assigned role/class

### Role/class definitions

Roles should include:

- combat or story function
- preferred operating range
- modifiers
- abilities
- resources
- constraints

### Ability definitions

Abilities should describe:

- kind
- targeting
- range
- cost
- duration
- prerequisites
- mechanical effects
- modifiers
- generated world forcing/events
- optional visual semantics

---

# Layer 2 — Runtime world state

The runtime state is the canonical truth of the simulation.

It should track:

## Environment state

- current values
- velocity/trend for inertial values
- active environmental effects
- pending events
- terrain integrity
- ecological state

## Actor state

- position
- orientation
- posture
- velocity
- health/injury
- fatigue
- resources
- active effects
- inventory
- current action
- previous action
- relationship state
- emotional/behavioral state where useful

## Spatial state

The first implementation may use lightweight spatial semantics, but the architecture must permit upgrading to explicit coordinates.

Eventually support:

- 2D or 3D position
- regions/zones
- adjacency
- line of sight
- reach
- movement paths
- cover
- terrain occupancy
- water depth
- elevation

## Simulation history

Each tick/round should produce an immutable record sufficient for:

- replay
- debugging
- deterministic regeneration
- cinematic moment selection
- audit of why an outcome occurred

---

# Layer 3 — Perception and knowledge

Actors must not make decisions from omniscient world state.

Each actor receives a perception derived from:

- actual world state
- sensory capabilities
- position
- visibility
- environmental noise
- prior knowledge
- attention
- current conditions
- uncertainty

Perception state should distinguish:

- known facts
- inferred facts
- suspected facts
- unknown facts
- confidence

Actors may therefore make reasonable decisions based on incorrect or incomplete information.

Initial perception capabilities should support:

- visible actors/terrain
- approximate distance/range
- visible injuries/effects
- audible events
- water-pressure or scent-like domain-specific senses
- known ally state

Later extensions may add richer species-specific sensing.

---

# Layer 4 — Intent generation

Each actor chooses an intent based on:

- perceived world
- objectives
- priorities
- motivations
- quirks
- role abilities
- current resources
- risk
- recent outcomes
- relationships
- tactical opportunities

Intent generation should not directly mutate world state.

An intent should describe:

- actor
- selected action/ability
- target
- desired outcome
- movement
- resource commitment
- risk tolerance
- contingencies where appropriate

## Decision model

Start with a weighted utility model rather than hard-coded class behavior.

Candidate actions receive scores from:

- objective relevance
- role affinity
- character priority
- motivation
- positional suitability
- risk
- cost
- expected effect
- quirk modifiers
- controlled decision jitter

The highest-scoring plausible action becomes the intent.

The architecture should permit a later LLM-backed decision provider without changing the simulation contract.

---

# Layer 5 — Action resolution

Actions should resolve as attempted changes against the current world.

Initial resolution should support:

- deterministic modifiers
- seeded random rolls
- difficulty/resistance
- opposed actions
- partial success
- strong success
- critical outcomes where appropriate

A resolution result should contain:

- action attempted
- roll/random sample
- modifiers
- degree of success
- direct actor effects
- generated forcing
- generated events
- generated follow-up opportunities
- temporal interval in which the action occurs

The resolver must not directly bypass world bounds.

For example:

An impact may generate:

- terrain integrity forcing
- actor impulse
- discrete `dam_stressed` event

The environment system then determines the actual bounded state change.

---

# Layer 6 — Simultaneous round/tick resolution

Combat and dynamic scenes should not behave as strictly serialized board-game
turns unless the scene explicitly requests that mode.

The round coordinator must implement the single-writer, phase-barrier execution
model described in **Execution safety and interaction model**.

A round should conceptually proceed as:

1. snapshot canonical state for the round
2. advance scheduled slow environmental processes that belong before decisions
3. compute all actor perceptions from the same stable snapshot
4. generate actor intents without mutating world state
5. normalize intents and declare targets/dependencies/read-write/claim sets
6. determine deterministic timing/initiative
7. open bounded reaction windows
8. build the action/reaction dependency graph
9. resolve acyclic dependencies
10. detect strongly connected components and resolve them with an explicit
    simultaneous-conflict policy
11. collect proposed actor updates, effects, forcing, and events
12. arbitrate exclusive writes and aggregate commutative writes
13. evolve each dynamic environment component once from aggregate forcing
14. apply accepted actor/effect/environment changes in one canonical commit
15. persist immutable round history in one short database transaction
16. identify meaningful moments in the completed interval

No step may synchronously invoke another round/tick or re-enter an earlier
phase.

If new information would cause an actor to reconsider outside an explicit
reaction window, the reconsideration is scheduled for the next decision window.

### Conflict-resolution requirements

The coordinator must define deterministic policies for:

- multiple actors targeting the same exclusive resource
- incompatible movement destinations
- simultaneous movement through constrained spaces
- grapple/hold ownership
- mutually exclusive posture/state transitions
- canceled or invalidated intents
- opposed actions
- equal initiative/timing
- reactions that target other reactions
- which of these cases use deterministic rules versus seeded stochastic
  arbitration

Every proposal reaches a terminal scheduler status.

### Causal budgets

A round must enforce configurable ceilings for:

- reaction depth
- causal depth
- generated events
- generated resolutions
- retries
- deferrals

Budget exhaustion records an overflow/deferred result and terminates the chain;
it never loops until a timeout.

### Acceptance criteria

- defensive interception works without recursive coordinator calls
- circular action dependencies terminate under an explicit bounded policy;
  that policy may be stochastic
- reaction chains cannot exceed their configured depth
- actions may alter later actions in the same interval through declared
  dependency/reaction rules
- two writes to the same exclusive state cannot silently last-write-win
- aggregate forcing evolves a dynamic component only once per tick
- provider completion order does not affect results
- every round terminates with no waiting proposals
- stochastic arbitration is allowed and recorded
- fixed seed + initial state + provider outputs reproduce the same round
- a resolved round produces one coherent next state and one immutable audit
  record

---

# Layer 7 — Environmental response

Environmental systems evolve independently but may receive forcing from actor actions and events.

Initial dynamic domains:

## Weather

- cloud cover
- precipitation
- wind
- fog
- temperature

## Hydrology

- water level
- current speed
- current direction
- turbidity
- surface roughness
- debris load

## Terrain

- structural integrity
- footing stability
- obstruction
- breach state
- collapse state

## Ecology

Examples:

- fish scatter
- frogs quiet
- birds flee
- beavers respond to threats
- scavengers arrive
- insects gather around light

Ecological elements need not be rendered merely because they exist.

---

# Layer 8 — Effects and abilities

Effects need a common runtime representation.

Effects may target:

- actor
- group
- creature
- terrain
- region
- flow field
- environmental component

Effects should support:

- source
- target
- magnitude
- duration
- stacking rules
- expiration
- conditions
- generated forcing
- generated events

Spell/ability categories should not be hard-coded to human fantasy conventions.

Otter-centric abilities are a design test for the abstraction:

- pressure sensing
- current manipulation
- scent communication
- bubble lattices
- silt interpretation
- schooling/fish interaction
- cache/tool use
- social-touch coordination

The framework must support such abilities without special-case engine code.

---

# Layer 9 — Cinematic observer

The cinematic observer does not decide what happens.

It receives the resolved interval and selects an instant to render.

A candidate moment may contain:

- timestamp within the interval
- primary subjects
- secondary subjects
- visible causal interaction
- emotional tension
- movement
- environmental consequence
- relevant active effects

Candidates should be scored for:

- causal clarity
- narrative importance
- tension
- visual separation
- continuity relevance
- class/character readability
- novelty relative to previous frames

The highest-scoring moment becomes the render frame.

The observer may suppress valid simulation details that would clutter the image.

Example:

A Bubble Augur may have acted successfully while its effect is nearly invisible in the selected frame.

---

# Layer 10 — Visual direction and prompt compilation

The prompt compiler converts the selected cinematic moment into renderer instructions.

It should consume:

- selected moment
- visible world state
- visible actors
- visible effects
- camera specification
- style profile
- continuity references

It should not invent new actions or outcomes.

## Style profiles

Style is configuration rather than world state.

Initial style controls should include:

- aspect ratio
- realism/stylization
- detail density
- background complexity
- particle density
- focal hierarchy strength
- lighting language
- color palette
- magic visibility
- water rendering style

The cinematic style established during prototyping should become a reusable
**high-spatial-frequency management** profile.

The concern is not necessarily random image noise. Fine details may all be valid
signal individually—fur strands, droplets, bark texture, foliage edges, ripples,
reflections—but excessive high-spatial-frequency signal distributed across the
frame creates perceptual interference. The human visual system then experiences
the image as noisy/cluttered because too many fine-scale signals compete with
the focal hierarchy.

The profile should therefore:

- preserve high-spatial-frequency detail around important subjects and causal
  interactions
- attenuate fine detail and microcontrast in secondary/background regions
- retain broad low/mid-frequency shapes for scene readability
- avoid globally uniform sharpness/detail density
- use edge/detail density as an attentional budget rather than maximizing it
- render water as broad sheets/arcs/masses where appropriate rather than a
  frame-wide field of droplets and ripple edges
- restrain particles and specular micro-highlights outside focal regions
- soften/simplify distant terrain and foliage
- keep few high-value contrast accents
- preserve clear silhouettes and spatial separation
- tie overt visual effects to real causal interactions

---

# Layer 11 — Renderer integration

Renderer adapters should be replaceable.

A renderer interface should accept a renderer-neutral render request and return:

- asset reference
- renderer metadata
- seed where available
- generation parameters
- status/errors

Initial adapters may target image-generation APIs.

Future adapters may target:

- local diffusion models
- video generation
- 3D staging
- prose
- storyboard layouts

Renderer-specific APIs should remain outside the simulation core.

---

# Layer 12 — Evaluation and feedback

Human art direction remains authoritative.

The system should nevertheless capture feedback as structured information where practical.

Examples:

- too visually noisy
- poor action engagement
- weak focal hierarchy
- spell effect appears decorative rather than causal
- actor missing
- continuity error
- incorrect anatomy
- action does not match resolved state

Later automated checks may use:

- spatial-frequency energy distribution by image region
- edge/detail density by focal versus secondary/background regions
- microcontrast distribution
- saliency
- actor detection
- scene-state/render consistency
- prompt/image alignment

These checks should distinguish **excessive competing signal** from random
sensor/generation noise. A highly detailed image can be technically clean while
still producing perceptual noise because high-frequency signal is spread too
uniformly across the frame.

Automated evaluation should assist human taste, not replace it.

---

# Persistence

SQLite is the initial application database.

Use:

- SQLAlchemy for persistence
- Alembic for migrations
- platformdirs for OS-specific storage location

The database should eventually persist:

- installations
- projects/campaigns
- scene definitions
- simulation runs
- root run seeds
- timeline branches and branch entropy seeds
- checkpoints and active branch heads
- round/tick records
- actor state snapshots
- intents
- resolutions
- selected cinematic moments
- renderer requests
- generated assets
- human feedback

Large binary assets should be referenced rather than stored directly in SQLite.


Round persistence is part of the coordinator commit boundary:

- compute perceptions/intents/resolutions outside the database write transaction
- persist the completed round/state/history together in one short transaction
- never hold a SQLite write transaction while calling an external provider or
  renderer
- use stable operation IDs so a failed/retried commit cannot duplicate a round,
  event, effect, or asset association
- all ordered replay queries must use explicit ordering

---

# Packaging and project tooling

Generic tooling should remain delegated to mature packages.

Execution contexts are intentionally separate:

1. **repository/build** — Hatch, pytest, source-tree scripts, distribution artifacts;
2. **installer/maintenance** — `dss-maintain`, including application-state setup
   and explicit schema migration for installation/technical support;
3. **runtime application** — `dss`, which consumes already-prepared application
   state and never runs migrations.

Repository/build tooling must not invoke `dss` to build, install, migrate, or
qualify itself. Runtime code must not assume a Git checkout, Hatch environment, `dist/`
directory, or build metadata exists.

Current choices:

- Hatch/Hatchling — environment/task/build/package management
- pytest — testing
- Typer — CLI
- SQLAlchemy — persistence
- Alembic — migrations
- platformdirs — application-data paths
- GitPython — repository/build metadata only; development dependency, not runtime
- PyYAML — scene input

Before implementing generic tooling in DSS, first determine whether a mature package already provides it.

Custom DSS code should be reserved for DSS-specific semantics.

---

# CI policy

CI costs money and must remain deliberately sparse.

Policy:

- CI runs only when a new pull request is opened.
- Branch pushes do not trigger CI.
- Pushes to main do not trigger CI.
- Routine development validation should use local/Hatch commands.
- A PR is opened only when the feature is ready for qualification.

The PR qualification job should cover the minimum useful integration surface for that feature.

---

# Implementation roadmap

The architecture overview is intentionally separated from executable
implementation plans. When an orchestrator is used, it should assign work from
the documents under `docs/implementation/`; the same slices are also designed
to be executed through chained implementation prompts.

Implementation order:

1. **MVP — complete bounded simulation loop**
   - `docs/implementation/01_MVP_SIMULATION_LOOP.md`
2. **Timeline branching / multiverse operations**
   - `docs/implementation/02_TIMELINE_BRANCHING.md`
3. **Spatial and perception fidelity**
   - `docs/implementation/03_SPATIAL_PERCEPTION.md`
4. **Advanced interactions, reactions, and effects**
   - `docs/implementation/04_INTERACTIONS_EFFECTS.md`
5. **Cinematic observer**
   - `docs/implementation/05_CINEMATIC_OBSERVER.md`
6. **Prompt compiler and renderer adapters**
   - `docs/implementation/06_RENDER_PIPELINE.md`
7. **Durable campaigns, workflow, and CLI**
   - `docs/implementation/07_PERSISTENCE_WORKFLOW.md`
8. **Evaluation, feedback, and large-scale exploration**
   - `docs/implementation/08_EVALUATION_EXPLORATION.md`
9. **External / LLM decision providers**
   - `docs/implementation/09_EXTERNAL_DECISION_PROVIDERS.md`

See `docs/implementation/README.md` for orchestration rules, slice boundaries,
and handoff requirements.

The MVP remains renderer-independent. Its completion criterion is a fully
inspectable, replayable, branch-capable simulation round from Hollow Bank.
Rendering begins only after that simulation contract is stable.

---

# Interaction-safety test matrix

The simulator needs adversarial tests specifically aimed at interaction bugs.

Required cases include:

- two actors waiting on one another's proposed outcomes
- two defenders attempting to intercept the same attack
- intercept → counter-intercept reaction cycle
- two actors claiming the same unique object
- incompatible simultaneous destinations for one actor
- multiple forces targeting the same environment component
- event A → effect B → event A feedback cycle
- effect refresh/replace self-cycle
- repeated provider retry with the same operation ID
- external provider timeout with no held DB transaction
- persistence failure after resolution but before durable commit
- deterministic replay with intentionally shuffled provider completion order
- starvation scenario with repeated higher-priority reactions
- event-budget and causal-depth exhaustion
- no-op/livelock round where actors repeatedly prefer incompatible actions

Tests should assert both **correct outcome** and **termination within bounded work**.

---

# Non-goals for the current milestone

Do not build yet:

- a custom physics engine
- a custom build system
- a custom migration framework
- a custom CLI parser
- a custom task runner
- a renderer-specific simulation core
- automatic aesthetic judgment
- a GUI
- a web service
- a generalized LLM orchestration framework

Add those only when a concrete DSS requirement cannot be met cleanly by existing tooling or the current abstractions.

---

# Reference scenario

The Hollow Bank river-otter/alligator encounter remains the primary integration scenario because it stresses the desired architecture:

- multiple actors with distinct motivations
- familiar and unfamiliar role systems
- close combat
- ranged/support behavior
- subtle and overt magic
- hydrodynamic environmental interaction
- damageable terrain
- ecology
- group defense objectives
- highly dynamic spatial relationships
- persistent round-to-round state
- cinematic observation

The engine must remain general; Hollow Bank is a test dataset, not the architecture.
