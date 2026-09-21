# v0.9.0 — External / LLM Decision and Prose Providers

## Outcome

Allow external models to participate in perception interpretation or intent
selection while the deterministic/stochastic simulation engine retains
authority over validation, arbitration, resolution, and state mutation.

An external model may propose. It may not directly change world truth.

An optional local or external language model may also realize or revise prose,
but only inside a supplied fact/sub-prose packet. The deterministic compiler is
the fallback and the simulation remains authoritative.

## Packages

Use:

- official provider SDK for each provider
- **pydantic** for strict structured provider input/output schemas
- **tenacity** for bounded transient retries

For an OpenAI implementation, use the official **openai** Python SDK rather than
custom HTTP.

Do not introduce a generic multi-provider framework until at least two real
providers require the abstraction.

On Apple Silicon, evaluate **MLX-LM** first for local inference and LoRA/QLoRA
fine tuning because it already supplies those generic facilities. Do not add it
to production dependencies until a named model, memory/latency target, and the
v0.8 evaluation corpus demonstrate value over the deterministic compiler.

---

## Slice EP-01 — Provider-neutral decision request/response schema

### Goal

Define exactly what an external decision provider may see and return.

### Depends on

MVP provider interfaces and spatial/perception records.

### Shared code

**USE** Observation, ActionIntent, ScoredOption/score records, refs.

Provider transport schemas may use Pydantic; do not replace core domain
dataclasses wholesale.

### Packages

- pydantic

### Method

Input should contain actor-scoped information only:

- actor definition/state allowed to actor
- actor observations/beliefs
- legal candidate actions/abilities
- objectives/priorities/motivations encoded structurally
- recent actor-local history needed for choice

Do not send canonical hidden world state merely because the provider could use
it.

Output is constrained to:

- selected candidate/action ID or a proposal matching allowed schema
- target from allowed target set
- optional structured rationale
- optional confidence

Engine validates output against legal candidates before constructing
`ActionIntent`.

### Tests

Hidden facts absent from serialized request; invalid target/action rejected.

### Completion

External decision is a constrained proposal, not privileged engine access.

---

## Slice EP-02 — Provider adapter protocol and fake adapter

### Goal

Make external calls replaceable/testable.

### Depends on

EP-01.

### Shared code

Extend IntentProvider implementation family; keep transport errors separate from
domain outcomes.

### Packages

No new package beyond Pydantic.

### Method

Adapter exposes:

- capabilities/model identity
- decision call
- normalized error types

Implement deterministic fake adapter first.

External call happens outside DB transaction and against immutable request data.

### Tests

Timeout/error/fake response paths; no state mutation.

### Completion

Decision workflow is fully testable with no paid calls.

---

## Slice EP-03 — OpenAI intent provider

### Goal

Implement one real external decision provider.

### Depends on

EP-02.

### Shared code

**USE** the provider-neutral adapter protocol, Pydantic transport schema,
Observation/ActionIntent contracts, legal-candidate validation, and coordinator
fallback/terminal-status handling. Provider-specific types must not leak into
core domain records.

### Packages

- openai
- tenacity

### Method

Use official structured-output capability where available with a Pydantic schema.

Prompt/system context should emphasize:

- choose only from supplied legal actions/targets
- reason from actor knowledge, not omniscient truth
- return structured response only

Validate again locally even if provider claims schema compliance.

Retry only transient provider failures with bounded attempts/backoff.

Record:

- provider/model
- request schema/version
- returned structured choice
- usage metadata where available
- failure/fallback status

Do not persist secrets.

### Tests

SDK mocked; malformed/illegal model choice rejected; transient retry bounded.

### Completion

An actor can choose intent through OpenAI while engine legality remains local.

---

## Slice EP-04 — Failure and fallback policy

### Goal

Ensure provider outage cannot deadlock a round.

### Depends on

EP-03.

### Shared code

Use proposal terminal status and coordinator budgets.

### Packages

tenacity already selected.

### Method

Per provider call configure:

- timeout
- retry limit
- fallback policy

Fallback choices:

- local rules-based IntentProvider
- explicit no-action
- fail actor proposal while allowing round to continue

Never wait indefinitely and never hold canonical mutation/DB locks.

Record which fallback occurred.

### Tests

timeout, repeated transient error, permanent error, invalid response.

### Completion

External provider failure is a bounded recorded event, not a stuck simulation.

---

## Slice EP-05 — Comparative provider evaluation

### Goal

Compare local versus external intent choices without giving evaluation authority
to the provider.

### Depends on

branching/exploration.

### Shared code

Use sibling branches from same checkpoint.

### Packages

No new package.

### Method

Fork sibling branches where only intent-provider policy differs.

Compare:

- selected candidates
- score/rationale data
- subsequent simulation outcomes

Keep branch seeds controlled so differences can be attributed to provider policy
when desired.

### Tests

Provider-policy branch comparison preserves common ancestor and controlled
entropy.

### Completion

External decision quality can be studied without contaminating the canonical
timeline.

---

## Slice EP-06 — Constrained prose realization provider

### Goal

Allow an optional small local or external model to improve prose fluency while
preserving DSS facts, authored language, and provenance.

### Depends on

Provider protocol/failure policy, deterministic descriptive compiler, and
grounded prose evaluation.

### Shared code

**USE** DescriptionRequest/Result, fact claims, authored sub-prose, prose
profiles, avoidances, provider provenance, validation, and fallback policy.

### Packages

Use the official SDK for a hosted provider. For a local model, introduce one
well-supported runtime only after selecting and measuring a concrete model.
Fine tuning/training tooling stays optional and outside the production runtime.

### Method

Define a strict structured request containing allowed facts, required identity
language, optional sub-prose, style controls, and forbidden assertions. Require
structured response clauses or claim citations that can be validated. Reject or
fall back when the model adds unsupported action/state/appearance/visibility,
drops required invariants, times out, or emits invalid output. Record provider,
model, parameters, source request, validation, and fallback. Build an evaluation
corpus from deterministic compiler output plus human revisions before deciding
whether to fine tune a small local model.

### Tests

- fluent grounded variation is accepted with traceable claims
- hallucinated injury/object/action/appearance is rejected
- required authored identity and condition facts survive realization
- timeout/invalid output uses deterministic fallback without blocking mutation
- same recorded provider response replays; provider calls occur outside DB locks

### Completion

DSS can use model-assisted prose without ceding authority over truth or requiring
a model for normal operation.
