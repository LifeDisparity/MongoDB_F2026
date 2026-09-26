# Contracts v1

All JSON uses snake_case.
IDs are opaque strings; timestamps are UTC ISO8601.
Shared contracts have one integrator owner.
Schema version is 1.

## SourceSnapshot

source_id, source_version, title, original_url, pmcid?, content_sha256,
license_id?, license_url?, distribution_status, sections.

Immutable. Changed source text means a new version.

## SourceAvailability

run_id, source_id, source_version, available, revision, availability_history.

This is a mutable run-scoped overlay. Do not alter the original source record.

## Evidence

evidence_id, source_id, source_version, chunk_id, span_id,
start_offset, end_offset, quote_sha256.

The server reconstructs the quote.
Models select returned span IDs; model-authored quote text is never canonical.

## Claim

claim_id, run_id, revision, gene_id, relation, object_id?, object_label,
qualifiers, evidence_ids, conflicting_evidence_ids,
usable_evidence_ids, usable_conflicting_evidence_ids,
status, policy_version.

relation:
expressed_in | perturbation_observation | involved_in

status:
candidate | supported | conflicting | needs_review | unsupported

qualifiers:
stage_id?, stage_label?, cell_class?, assay?, intervention?,
polarity, scope_notes

polarity:
observed | not_observed | uncertain

Negative observations remain tied to experimental conditions.

## Decision

decision_id, investigation_id, question, selected_action, reason_summary,
decision_target, decision_it_can_change, evidence_ids,
stopping_condition, budget.

Store concise action summaries, not hidden chain-of-thought.

## Policy

policy_version, parent_policy_version?, configuration, configuration_sha256,
proposed_by, development_failure_ids, evaluation_id?, selection_status.

Mutable sections:
context_policy.mode = ranked_passages | experimental_context
review_policy.mode = on_conflict | on_scope_ambiguity | always
review_policy.retrieve_controls = boolean

Deterministic validation always runs.
Budgets/model/provenance/evaluator are not mutable fields.

## Evaluation

Persist:
evaluation_id, run_id, arm, split, manifest_sha256, model_id, policy_sha256,
case_ids, raw decision counts, fixed support audit counts, reference counts,
usage, failures, integrity outcomes, prediction_sha256.

P0 = competent fixed pipeline.
H0 = frozen persistent harness.
H1 = revised persistent harness.

The initial internal evaluator uses manifest_hash/model/policy_hash and
correct_count/decision_count/supported_count/support_count. Translate those
explicitly at the API boundary if the wire model uses different names.

## RunEvent

schema_version, run_id, sequence, event_id, operation_id, occurred_at,
type, payload.

Types:
investigation.created
decision.recorded
evidence.upserted
claim.upserted
source.availability_changed
worker.resumed
policy.proposed
evaluation.completed
policy.promoted
policy.rejected
run.completed

Entity upserts contain complete entity payloads.
The repository supplies global run IDs and sequences to domain events.

## API

POST /runs
GET /runs/{id}/snapshot
GET /runs/{id}/events?after={sequence}&limit={n}
GET /runs/{id}/evidence/{evidence_id}
GET /runs/{id}/evaluations
GET /runs/{id}/export
POST /runs/{id}/resume
POST /runs/{id}/demo-events/source-withdrawal

Snapshot includes last_sequence.
Use a consistent snapshot and event watermark.
Frontend deduplicates delivery and fetches gaps before advancing.
Start with one-second polling; streaming is optional.

Error envelope:
code, message, retryable, details?

## Tool surface

search_evidence(gene_id, query, section_types)
read_chunk(chunk_id, source_version, cursor)
resolve_gene(mention, taxon)
resolve_term(mention, ontology)
record_evidence(span_ids, source_version)
propose_claim(subject, relation, object, qualifiers, evidence_ids)
request_investigation(question, decision_target, stopping_condition)

## Fixture labeling

Synthetic integration fixtures must be labeled.
Canonical demonstration events must come from real recorded execution.
Fixture scores never become measured performance.
