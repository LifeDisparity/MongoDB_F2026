# Hackathon roadmap

Planning envelope: two builders plus coding-agent support, roughly eight
productive hours. Estimates are timeboxes, not guarantees.

## 0:00-0:30

Freeze contracts, source scope, ownership and fixture.
Vendor portable production helpers.
Frontend starts from the contract fixture.

## 0:30-2:00

Import source evidence.
Build one real grounded model call.
Persist one investigation and claim.
Show canonical evidence in the UI.
Demonstrate restart recovery on the vertical slice.

Gate:
one real cited claim survives process restart.
If blocked, shrink data scope immediately.

## 2:00-3:30

Run P0/H0.
Implement decision-specific follow-up and source dependency transitions.
Integrate the stable graph and event replay.

Gate:
a real follow-up changes or resolves an experimental-scope decision.

## 3:30-5:00

Propose one candidate.
Run validation, record selection and freeze policy.
Integrate policy diff and real metric panel.

## 5:00-6:00

Final evaluation.
Canonical scientific run.
Actual process recovery and withdrawal E2E.

## 6:00-7:00

Replay/export integration.
Presentation-size visual polish.
Fix only demo-blocking failures.

## 7:00-8:00

Freeze.
Rehearse three-minute flow.
Record a truthful replay fallback.

## Critical path

contracts -> source grounding -> real investigation -> frozen baseline
-> evaluated candidate -> final report -> canonical replay.

## Scope cuts

Cut workflow editing, chat, 3D, broad GO coverage, extra models and additional
optimization candidates first.

Preserve grounded investigation, actual policy evaluation, restart recovery and
selective evidence-dependency updates.

No unit-test work.
