# Existing package capabilities for the post-MVP plan

## Topic

Packages that substantially provide generic behavior needed by DSS releases
v0.2.0 through v0.9.0.

## Adopt

- **NetworkX**: dependency graphs, strongly connected components, topological
  operations, and path/topology algorithms. DSS supplies domain semantics.
- **Shapely**: optional 2D geometry, intersection, containment, and line-of-sight
  primitives when v0.3.0 reaches polygonal space.
- **Pydantic v2**: strict validation, serialization, and generated JSON Schema
  for authored configuration and provider transport boundaries. Do not replace
  stable core dataclasses wholesale.
- **Jinja2**: authored prose templating through `SandboxedEnvironment`,
  `StrictUndefined`, and template-variable inspection. DSS supplies the allowed
  fact context, filters, output limits, and provenance.
- **SQLAlchemy and Alembic**: repositories, transactions, persistence mapping,
  and schema migration.
- **Typer and platformdirs**: CLI construction and application-state paths.
- **OpenAI Python SDK**: OpenAI structured model and image generation/edit
  calls. Keep SDK types inside adapters.
- **Tenacity**: bounded retry/backoff for explicitly transient provider errors.
- **Pillow, NumPy, and scikit-image**: image decoding, normalized array work,
  FFT calculations, established gradients, and comparison metrics in v0.8.0.
- **Hypothesis**: replay, ordering, termination, invariant, and stateful property
  tests.

## Conditional

- **Polars** only after measured exploration-result volume justifies it.
- **MLX-LM** is a strong Apple Silicon candidate for local inference and LoRA
  fine tuning, but only after v0.8.0 produces a versioned evaluation corpus and
  a concrete model is benchmarked. It is an optional experiment/training extra,
  not a normal DSS runtime dependency.

## Do not substitute

- Generic deep/object diff packages cannot replace causal, branch-aware DSS
  comparison.
- Generic finite-state-machine or workflow packages cannot replace authoritative
  simulation mutation, semantic random streams, replay, and provenance.
- A generic multi-provider framework is premature before two real provider
  integrations demonstrate a shared contract.
- Embedding or language-model scores cannot establish factual grounding when
  DSS already has structured claims and source references.

## References

- Pydantic JSON Schema: <https://docs.pydantic.dev/latest/concepts/json_schema/>
- Jinja sandbox: <https://jinja.palletsprojects.com/en/stable/sandbox/>
- Jinja API and strict undefined values:
  <https://jinja.palletsprojects.com/en/stable/api/#jinja2.StrictUndefined>
- OpenAI image generation API:
  <https://platform.openai.com/docs/api-reference/responses-streaming/response/image_generation_call/in_progress>
- scikit-image metrics:
  <https://scikit-image.org/docs/stable/api/skimage.metrics.html>
- MLX-LM: <https://github.com/ml-explore/mlx-lm>
