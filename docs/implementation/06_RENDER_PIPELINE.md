# Feature Upgrade — Prompt Compiler and Renderer Adapters

## Outcome

Compile a selected cinematic moment into a renderer-neutral request and deliver
that request through replaceable renderer adapters.

Rendering remains downstream. A renderer can fail, retry, or produce an
unattractive image without invalidating the simulation timeline.

## Packages

Use:

- existing persistence/CLI packages
- add **openai** only for an OpenAI image adapter; use the official SDK rather
  than custom HTTP
- add **tenacity** for bounded retries of explicitly transient provider errors
- stdlib pathlib/hashlib for local asset references and content hashes

Do not build a generic HTTP client wrapper around provider SDKs.

---

## Slice RP-01 — Style profile model

### Goal

Move visual art direction into explicit reusable configuration.

### Depends on

cinematic observer output.

### Shared code

Style configuration is render-domain code, not simulation core.

### Packages

No new package.

### Method

Define a style profile with renderer-neutral fields such as:

- aspect ratio
- realism/stylization target
- overall detail density
- high-spatial-frequency detail budget
- focal-region high-frequency emphasis
- secondary/background high-frequency attenuation
- background complexity
- microcontrast distribution
- particle/droplet edge density
- focal-hierarchy strength
- lighting language
- palette guidance
- magic visibility
- water-rendering guidance
- avoidance constraints

Create the established cinematic profile around **high-spatial-frequency signal
management**, not generic "noise reduction."

The profile should encode:

- meaningful fine detail concentrated around focal subjects/actions
- lower fine-detail density and microcontrast in secondary/background regions
- broad low/mid-frequency water masses rather than globally dense droplet/ripple
  edges
- restrained particles and specular micro-highlights away from the focal region
- simplified distant terrain/foliage
- nonuniform sharpness/detail: important regions may remain highly detailed
- few high-value accents
- strong silhouettes
- causal rather than decorative effects
- spatial breathing room

Do not describe all high-frequency content as noise. The failure mode is
**perceptual interference from excessive competing high-frequency signal**, even
when each detail is individually meaningful.

### Tests

Serialization/default inheritance/override behavior.

### Completion

Art direction is reusable data rather than prose embedded in rendering code.

---

## Slice RP-02 — Renderer-neutral RenderRequest

### Goal

Define the complete contract between observer and renderer adapter.

### Depends on

RP-01 and selected cinematic moment.

### Shared code

**CREATE** render-domain request/result records outside simulation core.

### Packages

No new package.

### Method

`RenderRequest` should contain structured data:

- selected moment/checkpoint references
- visible subjects and state
- causal actions/effects
- environment facts
- camera hints
- style profile
- continuity/reference asset IDs
- requested output properties
- negative/avoidance constraints
- render request ID

`RenderResult` should contain:

- request ID
- adapter/provider
- asset reference(s)
- provider generation ID when available
- provider/model metadata
- provider seed if exposed
- final parameters
- status/error metadata

No prompt string is the canonical render request. Prompt text is one compiled
representation.

### Tests

Request can be serialized without provider-specific objects; unknown simulation
facts cannot appear unless supplied by the selected moment/projection.

### Completion

Renderer adapters can consume one stable structured request.

---

## Slice RP-03 — Prompt compiler

### Goal

Compile structured render data into a clear provider-facing text prompt without
inventing events.

### Depends on

RP-02.

### Shared code

**USE** selected moment, visibility projection, style profile.

### Packages

No new package.

### Method

Construct prompt sections from structured facts:

1. scene/state anchor
2. primary action and physical causal interaction
3. subject appearance/state
4. environment
5. visible effects only
6. composition/camera
7. style
8. explicit avoidances

The compiler must distinguish:

- simulation truth
- visible truth
- stylistic direction

It may omit irrelevant truth. It may not add unsupported action.

Keep compiler deterministic for a given RenderRequest unless a specific
prompt-variation feature is later introduced.

### Tests

- physical contact described when present
- nonvisible effect omitted
- absent actor/action never invented
- high-spatial-frequency management profile emits focal/background detail constraints
- prompt compilation does not mutate request/history

### Completion

A RenderRequest can produce inspectable provider-facing prompt text.

---

## Slice RP-04 — Renderer adapter protocol and fake adapter

### Goal

Create the adapter boundary and fully test it before any paid API integration.

### Depends on

RP-02/RP-03.

### Shared code

Renderer protocol belongs to render subsystem.

### Packages

No new package.

### Method

Protocol operations:

- capability description
- render request
- optional edit/continuation request where supported

Implement a fake/recording adapter that returns deterministic fixture assets or
metadata.

Application service chooses adapter; prompt compiler does not.

### Tests

- fake adapter receives expected request
- provider failure maps to RenderResult/error state
- simulation state unaffected by renderer failure
- retrying same render request does not create duplicate asset associations

### Completion

Rendering workflow is testable without network/cost.

---

## Slice RP-05 — OpenAI image adapter

### Goal

Add one real image provider using its official API.

### Depends on

RP-04.

### Shared code

**USE** adapter protocol. Provider-specific request mapping stays inside adapter.

### Packages

- official **openai** Python SDK
- **tenacity** for bounded retry of transient failures only

### Method

Credentials come from environment/config, never scene YAML/database plaintext
unless a later secrets mechanism is explicitly designed.

Map RenderRequest to supported OpenAI image-generation/edit parameters.

Retry only errors classified as transient. Do not retry policy/request-invalid
errors blindly.

Record actual provider/model/options returned.

External call occurs outside DB write transactions.

### Tests

- unit tests mock SDK boundary
- integration test optional/skipped without credentials
- transient retry bounded
- permanent error surfaced once
- no DB transaction held during mocked long provider call

### Completion

A selected moment can be rendered through the official SDK.

---

## Slice RP-06 — Asset store and provenance

### Goal

Retain generated assets without storing large binaries in SQLite.

### Depends on

real/fake adapters and persistence upgrade foundations.

### Shared code

Asset references are render/persistence domain.

### Packages

- platformdirs
- pathlib/hashlib

### Method

Store assets under application data using content-addressed or stable
run/branch/request directories.

Database stores:

- logical asset ID
- path/URI
- hash
- MIME/type
- dimensions where known
- render request/provider metadata
- branch/checkpoint/moment relation

Write file first to temporary path, verify/hash, atomically rename, then persist
reference in short transaction.

### Tests

- duplicate content handled safely
- partial file write never becomes durable asset reference
- asset can be traced to branch/checkpoint/render request

### Completion

Rendered output has durable provenance without bloating SQLite.

---

## Slice RP-07 — Continuation/reference-image workflow

### Goal

Use prior selected/rendered frames as continuity inputs where the provider
supports it.

### Depends on

RP-06.

### Shared code

Use asset references; do not put provider image objects into simulation records.

### Packages

Provider SDK only.

### Method

Observer/compiler chooses which continuity references are relevant.
Adapter maps them into provider-supported edit/reference inputs.

Reference use is explicit in RenderRequest and persisted.

No renderer output is allowed to update canonical actor appearance/state unless
a separate authored intervention explicitly does so.

### Tests

- reference provenance recorded
- provider without reference support fails capability validation cleanly
- simulation state cannot be altered from generated image metadata

### Completion

Successive frames can use prior assets for continuity without contaminating
simulation truth.

---

## Slice RP-08 — Render CLI/application workflow

### Goal

Expose selection→compile→render→asset inspection.

### Depends on

RP-01 through RP-07 plus the application-service/persistence boundaries.

### Shared code

**USE** selected-moment IDs, RenderRequest/RenderResult, renderer registry,
asset references, and application services. CLI code must not compile prompts or
call provider SDKs directly.

### Packages

Typer.

### Method

Commands approximately:

- `dss moment select ROUND_ID`
- `dss render request MOMENT_ID --style STYLE`
- `dss render run REQUEST_ID --adapter NAME`
- `dss asset show ASSET_ID`

Keep application services separate from CLI.

### Tests

Full fake-adapter workflow; optional provider integration test.

### Completion

A completed timeline can produce a traceable image asset without modifying its
simulation history.
