# Safe Harbor ownership

Integration branch: `codex/safe-harbor`.

The live GitHub Safe Harbor issue is authoritative for claims. See [ticket board](safe-harbor/TICKETS.md), [claims](safe-harbor/CLAIMS.md), and [contribution protocol](safe-harbor/CONTRIBUTING.md).

Initial reserved lanes:
- codex-integrator: F01-F04, shared contracts, dependencies/locks/startup.
- codex-data: D01-D04, real ingestion/catalog/criteria/reference assets; delivered pending acceptance review.
- codex-runtime: R01-R09, ledger/API/compiler/coordinator/worker/recovery/revisions.
- codex-ui: U01-U10/U12, shared UI files.

Unclaimed work includes D05-D10, H01-H08, R10-R12, U11/U13/U14 and Q01-Q12. Read prerequisites and reserve separate files before implementing. Availability does not waive dependencies.

No unit or component tests. Actual E2E, build/type/schema/data-integrity checks only. Do not close issues on code presence alone.
