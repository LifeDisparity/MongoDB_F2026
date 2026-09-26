# E2E acceptance — no unit tests

The user explicitly requires E2E-only verification.
Do not add isolated unit/component test suites.

Run against the complete application:
browser -> API -> model/workflow -> Atlas -> events -> browser.
Use real process boundaries for recovery.
Use a real configured model for the canonical scientific run.
Offline fixtures can support development but must be labeled.

## E2E-1: scientific investigation

Open the Ten-a development question.
Record a decision-specific follow-up request.
Retrieve the relevant source section/caption.
Accept a correctly qualified claim.
Open its evidence in the UI.

Pass:
intervention/cell class/scope are correct and the canonical source supports them.
The log records the request and resulting decision.

## E2E-2: evaluated policy adaptation

Run H0, propose an allowed patch from development evidence, execute validation,
persist the comparison and apply the fixed selection rule.
Open the same result in the UI.

Pass:
a real model proposal changes actual context/routing;
the UI agrees with the stored evaluation;
promotion/rejection follows fixed criteria;
final-test labels did not enter optimization.

## E2E-3: process interruption

Commit one result while another step remains pending.
Terminate the actual worker process.
Start a fresh worker with the same investigation ID.
Reload the browser.

Pass:
accepted IDs, policy, remaining budget and pending frontier survive;
pending work continues;
no duplicate accepted claim/export row appears.

A provider call interrupted before acceptance may repeat. Report its usage.

## E2E-4: source withdrawal

Real showcase:
withdraw the Ten-a source from current run availability;
dependent claims reopen;
the separately sourced Lola branch remains unchanged.

Engineering fixture, explicitly labeled:
A is supported only by S1.
B is supported by S1 and S2.
C is supported only by S3.
Withdraw S1.

Pass:
A loses support.
B retains S2.
C is unchanged.
Historical source/evidence remains available for inspection.
Retained contradictions stay visible.
Restoring a source requires review rather than automatic certification.

## E2E-5: replay integrity

Replay the canonical ordered event log from empty UI state.
Compare claims, support, policy decisions and cursor to the recorded snapshot.
Reconnect after interruption and recover event gaps.

Pass:
replay and recorded state agree;
duplicates do not duplicate graph entities;
LIVE/REPLAY labels remain accurate.

## E2E-6: export

Export a dossier after withdrawal.
Open it independently.

Pass:
claims, qualifiers, source versions and support state match current Atlas state;
citations work;
restricted full paper text and secrets are absent.

## Evidence of execution

For each scenario record:
run ID, commit, dataset/model/policy hashes, actual duration, result,
screenshot or replay reference, and any failure.
Skipped checks are not passes.
