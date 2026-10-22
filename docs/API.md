# AXIOM Local API

The local daemon publishes its OpenAPI contract at `/api/openapi.json`, with
interactive documentation at `/api/docs` and `/api/redoc`. `GET /api/meta`
reports the API contract version separately from the AXIOM application version.
Clients should send a unique `X-Request-ID` header; the server validates and
echoes it on success and failure responses. If the value is missing or malformed,
the server generates a safe identifier. The browser client includes that ID in
visible request errors, and the CLI daemon readiness probe sends one as well.

## Compatibility policy

- The current contract is `v1`; existing resource paths remain under `/api`.
- Additive, backward-compatible fields and endpoints may be added within v1.
- Existing field meanings, validation guarantees, and side-effect boundaries do
  not change within v1.
- Breaking changes require a parallel `/api/v2` contract. The v1 contract remains
  available during a documented migration window; removal requires a later major
  application release and a release note.
- Clients should ignore unknown response fields and must not assume that an
  optional field is present unless the OpenAPI schema marks it required.
- API version does not replace per-resource `schema_version` fields used for
  persisted workspace data.

## AXIOM Engine and training

- `GET /api/engine/status` reports direct local inference readiness.
- `POST /api/engine/generate` runs inference from an existing local Transformers model directory and optionally a local PEFT adapter.
- `GET /api/fine-tuning/runtime` reports compatible local LoRA training dependencies.
- `POST /api/fine-tuning/jobs` starts one bounded local LoRA training job.

Engine and fine-tuning model loads are local-only; they do not download weights or execute remote model code. See [AXIOM Engine](Local-Engine.md) and [Local fine-tuning](Local-Fine-Tuning.md) for limits and supported inputs.

The API binds to loopback by default through `axiom gui`. Network binding is an
explicit operator choice; see the local-daemon security guidance before exposing
it beyond the machine.
