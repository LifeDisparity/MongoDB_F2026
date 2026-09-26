# Implementation board

| Package | Owner | Status |
|---|---|---|
| F01–F04 foundation, contracts, environment | Integrator | in progress |
| D01–D07, D10 source ingestion and tools | Data | starting |
| R01–R12 ledger, API, execution, recovery | Runtime | pending contracts |
| U01–U14 interface, genome, graph, replay | UI | pending contracts |
| D08–D09, H01–H08 harness/evaluation | next available lane | queued |
| Q01–Q12 operational/browser E2E and critique | integrator/next lane | queued |

Source status at start: supplements, coordinates, sequences and annotations are not yet verified. No evaluation or improvement result exists. Real model access is not configured in the initial environment. A local MongoDB replica set is available; connectivity/transactions remain to be checked.

Limit concurrency to root + three subagents. Only root changes contracts or dependency manifests. Each completion report identifies paths, working behavior, actual acceptance evidence, limitations and next dependency.
