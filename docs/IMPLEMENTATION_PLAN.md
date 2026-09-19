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
- environmental noise
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

---

# Shared core library

Status: implemented foundation.

Concerns reused by multiple system layers live in
`dynamic_story_scaffold.core`. Feature modules should consume these contracts
rather than creating local equivalents.

Shared primitives currently include:

- stable actor/entity/component/target references
- semantic deterministic random streams
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
perception randomness cannot change environment evolution for the same run seed.

See `docs/CORE_LIBRARY.md` for the contracts and invariants.

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
- random seed configuration

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

Combat and dynamic scenes should not behave as strictly serialized board-game turns unless the scene explicitly requests that mode.

A round should conceptually proceed as:

1. advance slow environmental processes
2. compute actor perceptions
3. generate actor intents
4. determine action timing/initiative
5. resolve interactions and conflicts
6. generate forces/events
7. apply bounded world dynamics
8. update actor state
9. update perceptions/beliefs/history
10. identify meaningful moments in the interval

This allows actions to interfere with one another.

Examples:

- defender intercepts an attack aimed at a caster
- water-control spell alters another actor's footing
- an alligator roll changes the geometry of several simultaneous attacks
- collapsing terrain interrupts multiple intents

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

The low-noise cinematic style established during prototyping should become a reusable profile:

- broad water shapes
- restrained droplets
- low micro-contrast outside focal areas
- softened backgrounds
- few bright accents
- clear silhouettes
- effects tied to causal interactions
- strong spatial separation

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

- edge/detail density
- saliency
- actor detection
- scene-state/render consistency
- prompt/image alignment

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
- build history
- projects/campaigns
- scene definitions
- simulation runs
- seeds
- round/tick records
- actor state snapshots
- intents
- resolutions
- selected cinematic moments
- renderer requests
- generated assets
- human feedback

Large binary assets should be referenced rather than stored directly in SQLite.

---

# Packaging and project tooling

Generic tooling should remain delegated to mature packages.

Current choices:

- Hatch/Hatchling — environment/task/build/package management
- pytest — testing
- Typer — CLI
- SQLAlchemy — persistence
- Alembic — migrations
- platformdirs — application-data paths
- GitPython — Git metadata
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

# Implementation phases

## Phase 0 — Project infrastructure

Status: implemented.

Includes:

- Python package
- Hatch build/task configuration
- platform-aware installer
- SQLite database
- SQLAlchemy models
- Alembic migrations
- Typer CLI
- build artifact history
- sparse PR-only CI

## Phase 1 — Scene definition and bounded environment

Status: implemented foundation.

Includes:

- YAML scene loader
- setting
- environment components
- continuous bounds
- max delta
- jitter
- inertia
- named dynamics methods
- discrete transitions
- characters
- roles
- abilities
- creatures
- seeded simulation

Remaining hardening:

- richer validation/error messages
- cross-reference validation
- schema versioning for scene YAML
- optional formal JSON Schema export

## Phase 2 — Actor runtime state

Implement:

- normalized actor position/posture
- health/injury/fatigue
- resources
- inventory
- active effects
- current/previous action
- relationship state
- actor-state history

Acceptance criteria:

- actor runtime state derives cleanly from YAML definitions
- snapshots are serializable
- no role-specific special casing is required

## Phase 3 — Perception

Implement:

- perception model
- visibility/range
- uncertainty
- known/suspected/unknown facts
- species/role sensory modifiers
- actor-specific perception snapshots

Acceptance criteria:

- actors can hold different beliefs about the same world
- decisions consume perception, not canonical world state

## Phase 4 — Intent generation

Implement:

- action candidate generation
- utility scoring
- priorities/motivation weighting
- role/ability affordances
- risk/cost scoring
- behavioral jitter
- intent records

Acceptance criteria:

- two characters with the same role may choose different actions
- fixed seeds reproduce choices
- generated intents do not mutate world state

## Phase 5 — Action resolution

Implement:

- action checks
- modifiers
- target resistance
- degrees of success
- opposed actions
- generated forcing/events
- action timing

Acceptance criteria:

- action resolution is replayable from seed + state + intents
- direct results cannot bypass state bounds
- resolution record explains why the result occurred

## Phase 6 — Interaction and simultaneous rounds

Implement:

- timing ordering
- reactions/intercepts
- action conflicts
- movement interactions
- interruption
- round transaction/history

Acceptance criteria:

- defensive interception works
- actions may alter later actions in the same interval
- resolved round produces one coherent next state

## Phase 7 — Effects framework

Implement:

- runtime effects
- durations
- targets
- stacking
- expiration
- environmental effects
- group/AoE effects

Acceptance criteria:

- Currentcaller/Bubble Augur style abilities require no engine special cases
- invisible/informational effects are supported

## Phase 8 — Spatial model

Implement incrementally:

1. semantic zones
2. positions and distances
3. adjacency/reach
4. line of sight/cover
5. terrain geometry interfaces

Do not build a general physics engine unless simulation requirements demand it.

## Phase 9 — Cinematic observer

Implement:

- candidate moments
- importance scoring
- causality scoring
- novelty
- subject selection
- visibility suppression
- camera hints

Acceptance criteria:

- selected frame comes from resolved events
- observer cannot change simulation truth
- successive frames materially differ because state differs

## Phase 10 — Prompt/render request compiler

Implement renderer-neutral:

- visible actor descriptions
- actions at selected instant
- causal effects
- environment
- camera
- style profile
- negative/avoidance constraints
- continuity anchors

Acceptance criteria:

- compiler does not invent outcomes
- low-noise style profile reproduces established art direction

## Phase 11 — Renderer adapters

Implement only thin adapters around existing APIs/libraries.

Initial requirements:

- generate image
- continue/edit from prior frame where supported
- retain generation metadata
- store asset reference
- surface failure cleanly

## Phase 12 — Campaign/run persistence

Persist:

- source YAML
- compiled scene definition
- initial seed
- every tick/round
- perceptions
- intents
- rolls
- resolutions
- world snapshots
- cinematic selections
- renderer requests/assets

Acceptance criteria:

- a completed run can be replayed deterministically without rendering
- an individual round can be inspected and regenerated

## Phase 13 — CLI/workflow

Add DSS-specific commands, using Typer rather than custom parsing.

Likely surface:

- create/import scene
- validate scene
- start run
- advance tick/round
- inspect state
- inspect actor perception
- replay
- select cinematic moment
- render selected moment

The CLI should call the same application services used by future UI/API surfaces.

## Phase 14 — Evaluation and art-direction feedback

Add structured feedback records and optional analyzers.

Do not block simulation work on automated aesthetic scoring.

---

# Near-term implementation order

The active feature branch should implement the next vertical slice:

1. actor runtime state
2. actor perception
3. action/ability candidate generation
4. utility-based intent selection
5. seeded action resolution
6. forcing/event output
7. apply results through existing bounded world dynamics
8. persist round records
9. tests using the Hollow Bank example

Only after that vertical slice is coherent should DSS add the cinematic observer.

The first end-to-end milestone is:

> Load Hollow Bank YAML → initialize state → each actor perceives the scene → each actor chooses an action → actions resolve with seeded randomness → world state advances within bounds → full round history is inspectable and replayable.

That milestone proves the simulation architecture independently of image generation.

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
