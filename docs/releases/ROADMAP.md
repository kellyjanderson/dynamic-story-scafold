# DSS post-MVP release roadmap

DSS grows from a bounded simulator into a system that can describe its own
world coherently. Each release adds one simulation capability and one layer of
descriptive language. The prose is intended to stand on its own in a story and
to be suitable input to ChatGPT or another image/keyframe generator. It is not
a bag of image-model keywords.

The authoritative slice tracker is
[`project/Plans/post-mvp-implementation-slices.md`](../../project/Plans/post-mvp-implementation-slices.md).
The implementation detail for each release remains in the linked plan.

## v0.2.0 — Possible futures

**Simulation outcome:** users can fork, reroll, intervene, compare, and activate
timeline branches without destroying alternatives.

**Prose outcome:** descriptions retain their source branch/checkpoint identity.
Branch comparison can explain the first causal divergence and its visible or
narratively relevant consequences in readable prose.

Plan: [`02_TIMELINE_BRANCHING.md`](../implementation/02_TIMELINE_BRANCHING.md).

## v0.3.0 — Situated perception

**Simulation outcome:** explicit topology, distance, cover, line of sight,
sensory profiles, and actor knowledge replace coarse zone-only assumptions.

**Prose outcome:** authored place and sensory sub-prose is selected from actual
position, visibility, occlusion, scale, and point of view. Descriptions can say
what can be seen, heard, or felt without leaking omniscient facts into an
actor-perspective passage.

Plan: [`03_SPATIAL_PERCEPTION.md`](../implementation/03_SPATIAL_PERCEPTION.md).

## v0.4.0 — Visible consequences

**Simulation outcome:** richer simultaneous interactions, relational state,
movement conflict, persistent conditions/effects, and environmental coupling.

**Prose outcome:** characters, objects, environments, effects, and conditions
can carry user-authored descriptive sub-prose. Runtime conditions compose and
remove their visible, material, and sensory consequences without rewriting a
subject's stable identity.

Plan: [`04_INTERACTIONS_EFFECTS.md`](../implementation/04_INTERACTIONS_EFFECTS.md).

## v0.5.0 — Narratable moments

**Simulation outcome:** the cinematic observer selects a meaningful, visible,
causally grounded instant from completed history.

**Prose outcome:** DSS produces an inspectable moment brief and a concise
descriptive passage from the selected instant. The passage distinguishes
established fact, visible projection, authored wording, and omission.

Plan: [`05_CINEMATIC_OBSERVER.md`](../implementation/05_CINEMATIC_OBSERVER.md).

## v0.6.0 — Descriptive prose and rendering

**Simulation outcome:** selected moments flow through stable description and
renderer adapter contracts with asset provenance.

**Prose outcome:** a deterministic compiler composes full, coherent prose from
the user's sub-prose, current visible state, action causality, continuity,
camera/composition guidance, and style. The canonical artifact is structured
facts plus prose; provider-specific image prompts are derived representations.
The same prose can be used in a story or passed to ChatGPT for an image.

Plan: [`06_RENDER_PIPELINE.md`](../implementation/06_RENDER_PIPELINE.md).

## v0.7.0 — Durable story projects

**Simulation outcome:** campaigns, scene revisions, branches, moments, prose,
and rendered assets survive across sessions and support import/export.

**Prose outcome:** reusable prose libraries, entity identity descriptions,
condition variants, compiled passages, continuity references, and their exact
source revisions are durable project data.

Plan: [`07_PERSISTENCE_WORKFLOW.md`](../implementation/07_PERSISTENCE_WORKFLOW.md).

## v0.8.0 — Description evaluation and exploration

**Simulation outcome:** structured feedback, invariant checking, and controlled
multi-branch exploration support comparison without changing history.

**Prose outcome:** DSS checks factual grounding, continuity, coverage,
readability, and usefulness for story/image generation. Human feedback compares
passages and their resulting assets; automated scores never rewrite truth.

Plan: [`08_EVALUATION_EXPLORATION.md`](../implementation/08_EVALUATION_EXPLORATION.md).

## v0.9.0 — Constrained model assistance

**Simulation outcome:** external models may propose perceptions or intents while
the simulation retains authority over validation, arbitration, and mutation.

**Prose outcome:** an optional local or external language model may realize or
revise prose inside an explicit fact packet and authored-language boundary.
Every output is validated against source facts and can fall back to the
deterministic compiler. Fine tuning a small local model becomes an evidence-led
option, not a prerequisite.

Plan: [`09_EXTERNAL_DECISION_PROVIDERS.md`](../implementation/09_EXTERNAL_DECISION_PROVIDERS.md).

## Version release gate

Every version ends with a release slice that:

1. completes all slices in that version;
2. runs local, package, isolated-install, and installed-runtime qualification;
3. updates the package and installer to the same semantic version;
4. adds user-facing release notes;
5. merges the release PR before creating the annotated Git tag;
6. publishes a GitHub release and verifies its assets and target commit.
