# Safe Harbor

Safe Harbor uses real genome data to investigate published candidate DNA insertion sites and tests changes to its own workflow to improve those investigations.

Initial scope: GRCh38 reference, H1 human embryonic stem cells, Pansio-1, Olônne-18 and Keppel-19 from Autio et al. Candidate regions are publication-derived. Computational criteria and named experimental endpoints are distinct; the product never declares global biological safety.

This is the new Safe Harbor implementation checkout. Inherited `living_atlas` modules and old docs are legacy reference only and are not the product runtime.

- Shared contract: `shared/contracts.ts`, `shared/contracts.py`, `docs/safe-harbor/CONTRACTS.md`.
- Ticket board and source status: `docs/safe-harbor/STATUS.md`.
- Startup/configuration: `docs/safe-harbor/STARTUP.md`.
- Verification: **E2E only**. No unit or component tests.

The MongoDB application ledger stores authoritative state, dependencies and ordered replay events. Large source assets are hashed external files. LangGraph checkpoints do not replace the ledger.

## Contributors: start here

**[All 60 Safe Harbor tickets and active claims](docs/safe-harbor/TICKETS.md)** · [Claim protocol](docs/safe-harbor/CONTRIBUTING.md) · [Full implementation specification](docs/safe-harbor/SPECIFICATION.md)

Work from branch `codex/safe-harbor`. Claimed issues visibly show **CLAIMED: owner** and `status:claimed`; do not duplicate another model's work. Run `python3 scripts/safe_harbor_ticket.py show SH-H01` before claiming. Live GitHub issues are authoritative; committed ownership tables are snapshots. Older LA-* issues are legacy scope.
