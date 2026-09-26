# Bootstrap implementation status

## Production source supplied

LA-03:
Pinned AGR evidence_spans.py and tool_result_bounds.py, unchanged, with license
and upstream provenance. Git blob identities verified by bootstrap.

LA-12:
Pure source-availability dependency transition core. Preserves immutable
sources/evidence, run-scoped overlays, support history, idempotency and
conflicting evidence. Returns changes for the Atlas repository to commit.

LA-15:
Independent scheduled-row normalization, local exact anatomy recall,
fixed-decision scoring, bounded policy patches and validation-only selection.

## Explicitly not complete

No running FastAPI application yet.
No real model adapter connected.
No MongoDB repository integration or checkpointed workflow demonstrated.
No frontend.
No completed scientific benchmark or measured policy improvement.
No real process-recovery or browser E2E run.

These tickets remain open until full application integration.

## Verification policy

No unit-test files are supplied.
The bootstrap performs Python syntax parsing only.
All behavioral acceptance is E2E through the complete application.

## First integration work

1. Freeze shared contracts.
2. Build source -> model -> accepted evidence -> Atlas -> browser vertical slice.
3. Connect dependency transitions at the repository transaction boundary.
4. Connect evaluation primitives to trusted experiment records.
5. Execute the E2E acceptance scenarios.
