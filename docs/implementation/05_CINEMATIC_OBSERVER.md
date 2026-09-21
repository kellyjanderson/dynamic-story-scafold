# v0.5.0 — Cinematic Observer and Narratable Moments

## Outcome

Select a meaningful renderable instant from completed simulation history without
changing what happened.

The observer is a downstream reader. It cannot create actions, modify outcomes,
or repair inconvenient simulation state.

This release turns selected visible truth into a concise, inspectable prose
account. It is the first user-facing descriptive output: useful as a story
passage or as grounded input to later image/keyframe generation.

## Packages

Use existing:

- networkx if causal ancestry queries benefit from the action/event graph
- no computer-vision dependency in this upgrade

---

## Slice CO-01 — Cinematic moment domain model

### Goal

Define renderer-neutral candidate/selected moment records.

### Depends on

completed round records and shared scoring.

### Shared code

**USE** refs, TimeSpan, ScoreBreakdown, ScoredOption.

**CREATE** cinematic-specific records outside generic core unless another layer
truly needs them.

### Packages

No new package.

### Method

A moment record should reference existing simulation facts:

- timestamp/interval
- primary subjects
- secondary subjects
- source resolutions/events
- visible effects
- environmental consequences
- candidate camera hints
- continuity links

Do not copy entire world state into every moment; reference a checkpoint plus
the relevant deltas/subjects.

### Tests

- moment cannot reference unknown resolution/entity
- serialization/replay
- creating a moment cannot mutate simulation state

### Completion

Resolved history can be represented as candidate visual moments.

---

## Slice CO-02 — Candidate extraction

### Goal

Generate possible moments from a completed round.

### Depends on

CO-01.

### Shared code

**USE** round/action/event/effect audit data.

### Packages

No new package.

### Method

Candidate sources:

- successful/failed high-impact resolution
- physical contact/interception
- environmental state transition
- actor injury/rescue
- major reaction
- information reveal
- group/AoE consequence

Candidate extraction is rule-based and causal. It does not invent a new event to
make the frame better.

Multiple resolutions may belong to one candidate if they are causally/spatially
coherent.

### Tests

- Shellbreaker impact candidate references actual impact
- Holtwarden intercept candidate references actual interception
- subtle support action can exist without becoming primary candidate
- no candidate contains events absent from history

### Completion

Every interesting Hollow Bank round yields a bounded candidate set.

---

## Slice CO-03 — Inspectable cinematic scoring

### Goal

Rank candidates without an opaque "AI chose this" step.

### Depends on

CO-02.

### Shared code

**USE** ScoreTerm/ScoreBreakdown/ScoredOption.

### Packages

No new package.

### Method

Initial terms:

- causal clarity
- narrative importance
- tension
- visible interaction
- subject separation
- continuity relevance
- novelty versus recent selected moments
- character/role readability
- environmental readability
- competing-detail/clutter penalty
- estimated focal-versus-background detail separation

Weights belong to a cinematic/style policy, not core.

Seeded stochastic selection among near-equal candidates is allowed. Record
candidate scores and sampled choice.

### Tests

- score contribution inspection
- same seed/policy replays selection
- near-tie stochastic selection can differ under different branch entropy
- competing-detail penalty does not rewrite or suppress required simulation truth

### Completion

One selected moment has an auditable reason for selection.

---

## Slice CO-04 — Visibility projection

### Goal

Determine which true simulation facts are actually visible in the chosen frame.

### Depends on

spatial/perception upgrade and CO-03.

### Shared code

**USE** spatial visibility queries, but do not use an actor's subjective
perception as camera truth unless the camera is explicitly actor-perspective.

### Packages

Shapely as already selected for 2D occlusion.

### Method

Project world truth into camera-visible facts:

- in-frame actors
- occluded actors
- visible physical contact
- visible effects
- terrain/environment
- nonvisual effects omitted or represented only when visual semantics permit

Suppression is allowed. Fabrication is not.

### Tests

- invisible pressure effect need not render
- occluded actor not described as visibly acting
- physical contact retained when selected moment depends on it

### Completion

The observer outputs a coherent visible-state subset.

---

## Slice CO-05 — Camera hints and composition constraints

### Goal

Produce renderer-neutral camera/composition guidance.

### Depends on

CO-04.

### Shared code

Cinematic-specific, not core.

### Packages

No new package.

### Method

Hints may include:

- shot scale
- camera position/azimuth/elevation
- primary focal subjects
- depth ordering
- desired spatial breathing room
- motion direction
- aspect ratio constraints

Do not solve exact photogrammetry. The renderer adapter remains responsible for
provider-specific prompt syntax.

### Tests

- close-combat moment requests readable physical engagement
- group shot preserves subject separation
- camera hints do not change actor/world state

### Completion

Selected moment contains enough renderer-neutral visual direction for prompt
compilation.

---

## Slice CO-06 — Continuity and novelty memory

### Goal

Avoid repeatedly selecting visually identical moments when the simulation
offers alternatives.

### Depends on

CO-03/CO-05.

### Shared code

Use selected-moment history; do not modify actor memory.

### Packages

No new package initially.

### Method

Track compact descriptors of previous selected moments:

- primary subjects
- action category
- camera category
- zone
- dominant effect/environment event

Apply novelty penalty during scoring.

Continuity constraints can favor preserving established spatial relationships
when the state has not changed.

### Tests

- repeated equivalent candidate receives novelty penalty
- genuinely changed state can still select same actor/action category
- continuity memory has no influence on simulation resolution

### Completion

Successive selected frames respond to state progression rather than producing
near-duplicates.

---

## Slice CO-07 — Grounded moment brief and concise prose

### Goal

Produce a source-backed moment brief and concise descriptive passage for one
selected cinematic moment.

### Depends on

CO-01 through CO-06 and the available authored sub-prose/spatial projection.

### Shared code

**USE** selected moment, checkpoint/delta references, visible projection, camera
hints, continuity links, and authored sub-prose packets. Prose remains an
observer artifact, never canonical state.

### Packages

No new package.

### Method

Create a structured moment brief separating: established simulation facts,
visible facts, authored language fragments, composition guidance, omissions,
and avoidances. Deterministically compose concise natural prose in complete
sentences. Prefer causal action and concrete sensory detail. Do not use terse
keyword lists or image-generator prompt syntax. Retain claim-level source
references so each sentence can be audited.

### Tests

- every factual clause maps to a brief claim/source
- invisible/nonvisual facts are omitted unless the chosen perspective supports
  a sensory description
- authored identity wording remains consistent across successive moments
- absent injury, arrival, object, effect, or action is never introduced
- output is readable as prose, not a comma-separated tag list

### Completion

A stored round can yield an auditable concise passage describing one real
moment.

---

## Upgrade qualification

For several stored Hollow Bank rounds, demonstrate that selected moments:

- are traceable to actual causal records
- emphasize real engagement
- suppress secondary competing detail without inventing facts
- replay under same observer seed/policy
- vary appropriately as simulation state changes
