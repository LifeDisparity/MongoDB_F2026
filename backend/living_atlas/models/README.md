# Structured model adapter

`StructuredModelAdapter.from_env()` uses one explicitly configured `MODEL_ID`
and server-side `OPENAI_API_KEY`. Missing either gives `available == False` and
an explicit `model_not_configured` result. There is no model fallback, fixture
response or invented price. The adapter does not log prompts, keys, responses
or provider error bodies. Keep SDK/HTTP debug logging disabled in production.
`adapter.status()` returns only `{configured, model_id, error_code}` without a
provider request, suitable for the server health endpoint.

```python
adapter = StructuredModelAdapter.from_env()
budget = adapter.new_budget()
result = await adapter.generate(
    StructuredRequest(request_id="investigation-1:read-1",
                      instructions=scientific_rules, input_text=context_packet),
    ScientificDecision,  # a Pydantic BaseModel with explicit named fields
    budget,
    checkpoint=persist_attempt_and_budget,  # async (AttemptRecord, ModelBudget)
)
# Persist result.model_dump(mode="json") before accepting any scientific output.
# Scientific evidence/scope validation remains mandatory after schema validation.
await adapter.close()
```

`ModelResult` holds parsed output or a safe explicit failure, per-attempt actual
usage, requested/resolved model IDs, response/request IDs, hashes, elapsed time,
and the updated budget. `total_cost` is null with `cost_status: not_priced`.
Cost-based promotion must not run until an independently pinned pricing/billing
process provides complete actual costs. Token counts are not monetary cost.

## Immutable server settings

| Environment variable | Default |
|---|---|
| `MODEL_ID` | Required; no default |
| `OPENAI_API_KEY` | Required; server only |
| `RUN_TOKEN_BUDGET` | 150000 |
| `RUN_MAX_MODEL_CALLS` | 24 |
| `MODEL_MAX_OUTPUT_TOKENS` | 2048 |
| `MODEL_MAX_INPUT_BYTES` | 120000 |
| `MODEL_MAX_ATTEMPTS` | 2 (maximum 3) |
| `MODEL_TIMEOUT_SECONDS` | 60 |
| `MODEL_DEADLINE_SECONDS` | 120 |

The caller cannot override model identity or these limits in a request. The
same frozen settings must serve P0/H0/H1. Scientific policy configuration must
not construct adapters or reset budgets. One workflow owns a budget; do not
concurrently call the adapter with copies of the same budget. Concurrency and
LangGraph checkpoint ownership belong to the workflow layer.

## Accounting and interruption

The adapter first calls the official input-token-count endpoint with the exact
instructions, input and strict output schema. It reserves that input count plus
the maximum output before each generation. SDK automatic retries are disabled;
at most the configured attempts occur inside an overall deadline.

The checkpoint callback receives `stage: reserved` **before** generation and
`stage: settled` afterward. Persist reservations atomically before returning
from the callback. If persistence fails, inference does not start. If the
process dies or is cancelled after reservation, keep the pending usage unknown;
the reservation prevents a fresh worker from spending that budget again.
Reconcile with provider records when possible. The adapter does not promise
exactly-once inference or provide a scheduler.

Usage reported by the provider is retained even when output is refused,
incomplete or fails Pydantic validation. Timeout/connection/server errors can
leave usage unknown; their full reservations remain spent for admission and
`unknown_usage_calls` remains nonzero. Retrying is bounded and retains every
attempt. `known_usage_tokens` is only the sum of known generation usage for
this request; `ModelBudget.known_tokens` covers the whole investigation.
Preflight requests have their own count and are not reported as generated
tokens. Missing usage is never reported as zero measured cost.

HTTP retryable errors are bounded; refusals, invalid output, incomplete output,
authentication failures and unsupported model/schema errors do not trigger an
automatic alternate prompt or model. Raw provider messages never enter result
records. A failed final checkpoint propagates to the workflow, preventing it
from treating output as durably accepted.

Strict structured output uses `responses.create(text.format=json_schema)` and
then validates with Pydantic, preserving access to provider usage on invalid
outputs. Schemas require named object fields; unrestricted dictionaries are
not supported. Defaults become required schema fields, matching strict output
rules. This module was inspected against OpenAI SDK 3.19.2.

Official references: [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[exact input token counting](https://developers.openai.com/api/docs/guides/token-counting).

No unit tests are supplied. Build/import checks do not establish a real-model
E2E pass. Canonical acceptance requires a configured model, real source
investigation, durable usage records, and the browser/Atlas flow in `docs/E2E.md`.
