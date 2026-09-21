# DSS product loop

## Origin and product test

DSS exists to automate the repeatable work inside an evolving role-playing
story that also produces progressive campaign images. The reference case is a
party of otter characters meeting alligators in a D&D-like encounter, with a
person playing or directing the campaign and asking for a new image after each
meaningful development.

The product succeeds when a user can repeatedly:

1. load or author a campaign, scene, characters, creatures, objects, and place;
2. inspect the current situation and legal choices in readable prose;
3. choose a player or GM action while rules or optional providers choose NPC
   actions;
4. advance exactly one bounded, replayable turn;
5. receive readable narration grounded in the resulting state and causality;
6. select a narratable instant and produce a continuity-aware image or
   keyframe description;
7. send that description and references to an image provider;
8. save the campaign checkpoint, prose, assets, and provenance; and
9. continue, fork, reroll, or revise without losing prior history.

This is the release-level acceptance path. A feature that improves simulation
depth but cannot eventually participate in this path is outside the product
throughline unless its separate purpose is explicit.

## What is scripted and what remains a decision

DSS should script state bookkeeping, legal-action enumeration, NPC proposals,
resolution, environmental response, replay, provenance, moment selection,
fact projection, prose assembly, provider request construction, asset storage,
and continuity retrieval.

The user retains authorship of campaign direction, player choices, corrections,
style, descriptive language, and the decision to accept, branch, reroll, or
render. Optional models may propose NPC actions or prose, but cannot establish
world truth or mutate state.

## Current reality

v0.1.0 proves the central deterministic simulation substrate: authored scene
data can be loaded, actors propose actions, conflicts resolve, state advances,
history persists, and a run replays. It does not yet provide the complete
product loop. In particular, it lacks a first-class player/GM turn request,
readable turn narration, moment selection, image generation, continuity-aware
campaign sessions, and a single command that joins those stages.

The post-MVP releases move toward the loop, but each release must now prove its
contribution with the cumulative acceptance ladder below.

## Cumulative acceptance ladder

| Release | Product-loop proof |
|---|---|
| v0.2.0 | A user chooses a legal action at a checkpoint, advances one branch turn, and can compare or reroll the result. |
| v0.3.0 | The offered choices and resulting description respect position, visibility, senses, and actor knowledge. |
| v0.4.0 | The turn can express contested movement, relationships, conditions, effects, and environmental consequences with authored descriptive fragments. |
| v0.5.0 | DSS selects a meaningful visible instant from that turn and emits a grounded concise passage. |
| v0.6.0 | One application workflow advances a directed turn, compiles full prose, and produces an image or ordered keyframe description with continuity references. |
| v0.7.0 | The workflow resumes as a durable campaign session with scene revisions, branches, prose, and assets preserved. |
| v0.8.0 | A user can compare alternate turns, passages, and assets with mechanical and human evaluation evidence. |
| v0.9.0 | Optional models can choose NPC actions or realize prose inside the same legal, factual, replayable boundaries. |

## Application orchestration boundary

The campaign/session application layer owns the user-facing sequence: present
choices, accept a player or GM command, ask providers for remaining proposals,
run one turn, select/describe/render, and persist the result. It composes shared
libraries and does not duplicate their rules.

Simulation remains authoritative for legality and mutation. Description remains
authoritative for fact projection and prose provenance. Rendering remains an
adapter boundary. Persistence stores their records without reimplementing any
of them.
