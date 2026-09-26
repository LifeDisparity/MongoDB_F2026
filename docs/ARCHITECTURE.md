# Architecture

## Components

React/TypeScript/React Flow frontend
-> FastAPI application
-> LangGraph investigation workflow
-> MongoDB Atlas scientific records, event log and checkpoints.

Use one workflow per gene investigation and at most two concurrent workflows.
Keep build-agent parallelism separate from runtime model concurrency.

LangGraph checkpoints own execution progress. Do not build another queue,
lease manager or distributed scheduler for the MVP.

## Inner investigation

Read -> interpret -> identify decision-relevant uncertainty -> targeted retrieval
-> conditional scope review -> deterministic validation -> accepted commit.

Each follow-up names:
- unresolved question;
- claim/decision it can change;
- required evidence/tool;
- stopping condition;
- bounded budget.

A result may accept, narrow, reject, preserve or leave a claim unresolved.
Stop when the question is resolved, relevant evidence is exhausted, or the
budget is exhausted. Never spawn open-ended "research more" recursion.

Exact gene/alias/taxon/ontology lookup is deterministic.
Models interpret experimental evidence and select useful follow-up reads.

## Outer improvement

Run H0 on development cases.
Optimizer proposes one bounded policy patch linked to observed failure/cost IDs.
Validate it, execute it on validation cases and apply a frozen selection rule.
Persist the proposal, actual execution and promotion/rejection.
Freeze the selected policy, then report final-test results once.

Start with one candidate. Two maximum.
A rejected candidate is visible and does not count as successful improvement.

## Durable records

sources:
immutable source ID/version/hash, rights, title, URL and section metadata.

chunks:
immutable text chunks tied to source versions and exact offsets.

source_state:
run-scoped availability overlays, revisions and history.

evidence:
immutable source-version/span references and canonical quote hashes.

claims:
atomic scientific assertions, qualifiers, positive/conflicting evidence IDs,
status, revision and policy version.

investigations:
question, affected decision, workflow ID, pinned policy, budget and frontier.

policies:
immutable configuration/hash/parent and selection history.

evaluations:
manifest/model/policy hashes, split, raw counts, usage, failures and predictions.

events:
ordered accepted application events for replay.

Checkpoint collections:
library-owned workflow state and pending execution writes.

## Context

Checkpoint state should hold IDs, budgets and pending frontier.
Retrieve original evidence as needed.
Do not accumulate every source and message in one model conversation.
Summaries may assist navigation but cannot replace original evidence.

## Consistency

Give accepted operations stable idempotency keys.
Persist entity changes and corresponding events consistently.
A resumed node may repeat a provider call; accepted output must deduplicate.
Do not promise exactly-once model inference.

Use unique source/version IDs, evidence identities, accepted operation IDs and
run/event sequences. Index claim-to-evidence and evidence-to-source lookups.
Use revisions/CAS at the repository boundary.
Recheck source availability/version before accepting model output.

Run namespaces isolate P0, H0 and H1 scientific working state.
They may share immutable raw sources, not each other's derived answers.

## Evidence changes

source version -> evidence span -> atomic claim -> dossier.

Withdrawal preserves historical text/evidence.
Recompute only dependent claims.
Claims retaining independent usable support stay supported.
Retain usable conflicting evidence.
Loss of sole positive support means unsupported/review required, not false.
Restoring a source does not automatically certify a claim.

Do not build a general scientific theorem/inference engine.

## Retrieval

Start with exact identity lookup and section-aware retrieval.
Semantic retrieval is optional and bounded.
Exact version/permission checks remain authoritative after retrieval.
Atlas is fundamental through durable investigations and scientific dependencies
even before vector retrieval is added.
