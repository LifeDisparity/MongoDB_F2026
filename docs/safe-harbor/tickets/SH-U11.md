<!-- claim-start -->
<!-- claim-owner: UNCLAIMED -->
## AVAILABLE — UNCLAIMED
**Owner:** UNCLAIMED
**GitHub operator:** unassigned
**Branch:** unassigned — branch from `codex/safe-harbor`
**Reserved paths:** none; proposed scope listed below
**Updated:** 2026-09-26T18:29:45.963349+00:00
Available to claim. Dependencies still govern acceptance; check adjacent path owners first.
<!-- claim-end -->

# SH-U11 — Add cinematic genome-follow cues

**Lane:** UI
**Dependencies:** [SH-U05](https://github.com/LifeDisparity/MongoDB_F2026/blob/codex/safe-harbor/docs/safe-harbor/tickets/SH-U05.md), [SH-U10](https://github.com/LifeDisparity/MongoDB_F2026/blob/codex/safe-harbor/docs/safe-harbor/tickets/SH-U10.md)
**Proposed file scope:** `frontend/src/safe-harbor/cues.ts`

## Work

Create a separate cue file keyed to actual event sequences: focus chromosome, zoom locus, show bases, highlight a result, then reveal the relevant graph branch.

## Acceptance criteria

Playback is smooth and synchronized with real events. Pausing or disabling camera follow leaves the application usable. Cues cannot change scientific state.

## Required handoff

- Changed paths and commit/PR.
- What now works.
- Actual acceptance evidence.
- Remaining limitations.
- Next dependent ticket and owner.

## Shared boundaries

**NO UNIT TESTS. NO COMPONENT TESTS. E2E ONLY.** Build/type/syntax/schema/data-integrity checks are allowed. Use real coordinates, sequence, annotations and source tables. No fabricated biology, model runs or improvements. Distinguish mock, deterministic operational, real model and recorded replay.

Only the integrator edits shared contracts, root dependency manifests/locks and startup composition. Scientific tools return bounded typed data; runtime owns database writes; frontend derives no biological verdicts. At most two runtime workers, 24 nodes, three replans and one transient retry. Harness changes cannot alter criteria/evaluator/input data/model/budget/permissions.

Read [contribution and claim protocol](https://github.com/LifeDisparity/MongoDB_F2026/blob/codex/safe-harbor/docs/safe-harbor/CONTRIBUTING.md), [specification](https://github.com/LifeDisparity/MongoDB_F2026/blob/codex/safe-harbor/docs/safe-harbor/SPECIFICATION.md), [contracts](https://github.com/LifeDisparity/MongoDB_F2026/blob/codex/safe-harbor/docs/safe-harbor/CONTRACTS.md), and [ticket board](https://github.com/LifeDisparity/MongoDB_F2026/blob/codex/safe-harbor/docs/safe-harbor/TICKETS.md). Safe Harbor supersedes the old LA-* plan; do not assume inherited modules or old PRs satisfy this ticket.

Claim command: `python3 scripts/safe_harbor_ticket.py claim SH-U11 --owner YOUR_MODEL --branch YOUR_BRANCH --paths YOUR_PATHS`
