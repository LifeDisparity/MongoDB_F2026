# Safe Harbor — tickets and active claims

**60 bounded work packages. NO UNIT TESTS. NO COMPONENT TESTS. E2E ONLY.**

Start from [codex/safe-harbor](https://github.com/LifeDisparity/MongoDB_F2026/tree/codex/safe-harbor). Read the [specification](https://github.com/LifeDisparity/MongoDB_F2026/blob/codex/safe-harbor/docs/safe-harbor/SPECIFICATION.md), [contracts](https://github.com/LifeDisparity/MongoDB_F2026/blob/codex/safe-harbor/docs/safe-harbor/CONTRACTS.md), and [claim protocol](https://github.com/LifeDisparity/MongoDB_F2026/blob/codex/safe-harbor/docs/safe-harbor/CONTRIBUTING.md).

**The live ticket's title, claim block, labels and assignee are authoritative.** This table is the initial ownership snapshot (2026-09-26T18:29:45.681685+00:00). [Current claimed tickets](https://github.com/LifeDisparity/MongoDB_F2026/issues?q=is%3Aopen+label%3Asafe-harbor+label%3Astatus%3Aclaimed) · [Available tickets](https://github.com/LifeDisparity/MongoDB_F2026/issues?q=is%3Aopen+label%3Asafe-harbor+label%3Astatus%3Aavailable).

Claim before editing: `python3 scripts/safe_harbor_ticket.py claim SH-H01 --owner YOUR_MODEL --branch YOUR_BRANCH --paths backend/safe_harbor/harness/`. A claim adds **CLAIMED: owner** to the title, records branch/paths/time in the body and assigns the GitHub operator. Never take a claimed ticket or overlap another owner's paths. Availability does not waive dependencies.

Active lanes: codex-integrator F01–F04; codex-data D01–D04 (delivered, acceptance review pending); codex-runtime R01–R09; codex-ui U01–U10/U12 (shared UI files reserved). Foundation claims remain open until actual acceptance. Runtime R10–R12 and all harness/evaluation packages are available with interface coordination. Data D05–D07 tools are the next vertical-slice need; D08–D09 need an independent evaluator. U11/cues, U13/presentation, U14/E2E must coordinate App integration with codex-ui.

Old LA-* issues and PRs remain intact for prior contributors; they are legacy scope, not the Safe Harbor queue. Do not assume their acceptance transfers. H01 interface requested by runtime: `safe_harbor.harness.get_harness(hash=None)` and `list_harnesses()`.

| Ticket | Work | Ownership | Dependencies |
|---|---|---|---|
| [SH-F01](tickets/SH-F01.md) | Establish the working repository and short operating documents | **CLAIMED — codex-integrator** | none |
| [SH-F02](tickets/SH-F02.md) | Freeze schema version 1 and publish fixtures | **CLAIMED — codex-integrator** | [F01](tickets/SH-F01.md) |
| [SH-F03](tickets/SH-F03.md) | Assign ownership and integration order | **CLAIMED — codex-integrator** | [F02](tickets/SH-F02.md) |
| [SH-F04](tickets/SH-F04.md) | Prove the runtime environment | **CLAIMED — codex-integrator** | [F01](tickets/SH-F01.md) |
| [SH-D01](tickets/SH-D01.md) | Freeze scientific criteria and result semantics | **CLAIMED — codex-data** | [F02](tickets/SH-F02.md) |
| [SH-D02](tickets/SH-D02.md) | Ingest the compact experimental source pack | **CLAIMED — codex-data** | [F04](tickets/SH-F04.md) |
| [SH-D03](tickets/SH-D03.md) | Import and normalize candidate regions | **CLAIMED — codex-data** | [D02](tickets/SH-D02.md) |
| [SH-D04](tickets/SH-D04.md) | Freeze reference windows and annotation coverage | **CLAIMED — codex-data** | [D03](tickets/SH-D03.md) |
| [SH-D05](tickets/SH-D05.md) | Implement deterministic genomic calculations | AVAILABLE — unclaimed | [D01](tickets/SH-D01.md), [D04](tickets/SH-D04.md) |
| [SH-D06](tickets/SH-D06.md) | Implement expression/control/proximity calculations | AVAILABLE — unclaimed | [D02](tickets/SH-D02.md), [D04](tickets/SH-D04.md), [D05](tickets/SH-D05.md) |
| [SH-D07](tickets/SH-D07.md) | Publish bounded worker tools | AVAILABLE — unclaimed | [D05](tickets/SH-D05.md), [D06](tickets/SH-D06.md), [F02](tickets/SH-F02.md) |
| [SH-D08](tickets/SH-D08.md) | Independently establish reference answers | AVAILABLE — unclaimed | [D05](tickets/SH-D05.md), [D06](tickets/SH-D06.md) |
| [SH-D09](tickets/SH-D09.md) | Freeze cases, grouping and evaluation splits | AVAILABLE — unclaimed | [D08](tickets/SH-D08.md) |
| [SH-D10](tickets/SH-D10.md) | Package provenance, attribution and optional tracks | AVAILABLE — unclaimed | [D02](tickets/SH-D02.md), [D03](tickets/SH-D03.md), [D04](tickets/SH-D04.md) |
| [SH-R01](tickets/SH-R01.md) | Create MongoDB collections and indexes | **CLAIMED — codex-runtime** | [F02](tickets/SH-F02.md), [F04](tickets/SH-F04.md) |
| [SH-R02](tickets/SH-R02.md) | Implement transactional result acceptance | **CLAIMED — codex-runtime** | [R01](tickets/SH-R01.md) |
| [SH-R03](tickets/SH-R03.md) | Implement API, snapshots and ordered polling | **CLAIMED — codex-runtime** | [R02](tickets/SH-R02.md) |
| [SH-R04](tickets/SH-R04.md) | Build the typed DAG compiler | **CLAIMED — codex-runtime** | [F02](tickets/SH-F02.md), [D07](tickets/SH-D07.md) |
| [SH-R05](tickets/SH-R05.md) | Implement bounded scheduling and deduplication | **CLAIMED — codex-runtime** | [R02](tickets/SH-R02.md), [R04](tickets/SH-R04.md) |
| [SH-R06](tickets/SH-R06.md) | Build genuine and deterministic execution adapters | **CLAIMED — codex-runtime** | [R05](tickets/SH-R05.md), [D07](tickets/SH-D07.md) |
| [SH-R07](tickets/SH-R07.md) | Implement durable budget accounting | **CLAIMED — codex-runtime** | [R02](tickets/SH-R02.md), [R06](tickets/SH-R06.md) |
| [SH-R08](tickets/SH-R08.md) | Implement checkpoints and fresh-process recovery | **CLAIMED — codex-runtime** | [R05](tickets/SH-R05.md), [R06](tickets/SH-R06.md), [R07](tickets/SH-R07.md) |
| [SH-R09](tickets/SH-R09.md) | Implement evidence revisions and selective invalidation | **CLAIMED — codex-runtime** | [R02](tickets/SH-R02.md), [R04](tickets/SH-R04.md), [R08](tickets/SH-R08.md) |
| [SH-R10](tickets/SH-R10.md) | Assemble bounded context packets | AVAILABLE — unclaimed | [R06](tickets/SH-R06.md), [D07](tickets/SH-D07.md) |
| [SH-R11](tickets/SH-R11.md) | Produce versioned assessments and shortlists | AVAILABLE — unclaimed | [R10](tickets/SH-R10.md), [D01](tickets/SH-D01.md) |
| [SH-R12](tickets/SH-R12.md) | Export complete, replayable investigations | AVAILABLE — unclaimed | [R03](tickets/SH-R03.md), [R09](tickets/SH-R09.md), [R11](tickets/SH-R11.md) |
| [SH-H01](tickets/SH-H01.md) | Define executable harness specifications | AVAILABLE — unclaimed | [F02](tickets/SH-F02.md), [R04](tickets/SH-R04.md) |
| [SH-H02](tickets/SH-H02.md) | Compile bounded structural changes | AVAILABLE — unclaimed | [H01](tickets/SH-H01.md), [R10](tickets/SH-R10.md) |
| [SH-H03](tickets/SH-H03.md) | Implement the competent fixed-agent baseline | AVAILABLE — unclaimed | [R06](tickets/SH-R06.md), [R11](tickets/SH-R11.md), [D09](tickets/SH-D09.md) |
| [SH-H04](tickets/SH-H04.md) | Implement the all-checks-plus-synthesis baseline | AVAILABLE — unclaimed | [H03](tickets/SH-H03.md) |
| [SH-H05](tickets/SH-H05.md) | Build isolated experiment execution and scoring | AVAILABLE — unclaimed | [H03](tickets/SH-H03.md), [H04](tickets/SH-H04.md), [D09](tickets/SH-D09.md) |
| [SH-H06](tickets/SH-H06.md) | Generate a real automatic harness proposal | AVAILABLE — unclaimed | [H02](tickets/SH-H02.md), [H05](tickets/SH-H05.md) |
| [SH-H07](tickets/SH-H07.md) | Apply promotion rules and reuse the selected version | AVAILABLE — unclaimed | [H06](tickets/SH-H06.md) |
| [SH-H08](tickets/SH-H08.md) | Publish transparent comparison results | AVAILABLE — unclaimed | [H07](tickets/SH-H07.md), [R12](tickets/SH-R12.md) |
| [SH-U01](tickets/SH-U01.md) | Build the application shell and mode indicators | **CLAIMED — codex-ui** | [F02](tickets/SH-F02.md) |
| [SH-U02](tickets/SH-U02.md) | Build the coordinate-correct genome overview | **CLAIMED — codex-ui** | [D03](tickets/SH-D03.md), [D04](tickets/SH-D04.md) |
| [SH-U03](tickets/SH-U03.md) | Integrate the locus browser | **CLAIMED — codex-ui** | [D04](tickets/SH-D04.md), [D05](tickets/SH-D05.md) |
| [SH-U04](tickets/SH-U04.md) | Build the reference-base strip | **CLAIMED — codex-ui** | [D04](tickets/SH-D04.md) |
| [SH-U05](tickets/SH-U05.md) | Connect overview, chromosome, locus and sequence zoom | **CLAIMED — codex-ui** | [U02](tickets/SH-U02.md), [U03](tickets/SH-U03.md), [U04](tickets/SH-U04.md) |
| [SH-U06](tickets/SH-U06.md) | Build candidate conclusions and comparison cards | **CLAIMED — codex-ui** | [U01](tickets/SH-U01.md), [R11](tickets/SH-R11.md) |
| [SH-U07](tickets/SH-U07.md) | Build the stable investigation DAG | **CLAIMED — codex-ui** | [U01](tickets/SH-U01.md), [R04](tickets/SH-R04.md) |
| [SH-U08](tickets/SH-U08.md) | Build evidence and numerical-result inspection | **CLAIMED — codex-ui** | [R03](tickets/SH-R03.md), [U03](tickets/SH-U03.md) |
| [SH-U09](tickets/SH-U09.md) | Implement the event reducer and reconnect behavior | **CLAIMED — codex-ui** | [U01](tickets/SH-U01.md), [R03](tickets/SH-R03.md) |
| [SH-U10](tickets/SH-U10.md) | Implement deterministic timeline replay | **CLAIMED — codex-ui** | [U09](tickets/SH-U09.md), [R12](tickets/SH-R12.md) |
| [SH-U11](tickets/SH-U11.md) | Add cinematic genome-follow cues | AVAILABLE — unclaimed | [U05](tickets/SH-U05.md), [U10](tickets/SH-U10.md) |
| [SH-U12](tickets/SH-U12.md) | Build the harness-change comparison drawer | **CLAIMED — codex-ui** | [H08](tickets/SH-H08.md), [U07](tickets/SH-U07.md) |
| [SH-U13](tickets/SH-U13.md) | Build the presentation and dossier flow | AVAILABLE — unclaimed | [U06](tickets/SH-U06.md), [U08](tickets/SH-U08.md), [U12](tickets/SH-U12.md), [R12](tickets/SH-R12.md) |
| [SH-U14](tickets/SH-U14.md) | Verify projection readability and motion behavior | AVAILABLE — unclaimed | [U05](tickets/SH-U05.md), [U07](tickets/SH-U07.md), [U11](tickets/SH-U11.md) |
| [SH-Q01](tickets/SH-Q01.md) | Run the first real candidate end to end | AVAILABLE — unclaimed | [D08](tickets/SH-D08.md), [R11](tickets/SH-R11.md), [U06](tickets/SH-U06.md) |
| [SH-Q02](tickets/SH-Q02.md) | Run scientific correctness and honest-unknown journeys | AVAILABLE — unclaimed | [Q01](tickets/SH-Q01.md), [D09](tickets/SH-D09.md) |
| [SH-Q03](tickets/SH-Q03.md) | Exercise actual crash recovery | AVAILABLE — unclaimed | [R08](tickets/SH-R08.md) |
| [SH-Q04](tickets/SH-Q04.md) | Exercise revision during active work | AVAILABLE — unclaimed | [R09](tickets/SH-R09.md) |
| [SH-Q05](tickets/SH-Q05.md) | Exercise idempotency, invalid plans and budgets | AVAILABLE — unclaimed | [R05](tickets/SH-R05.md), [R07](tickets/SH-R07.md), [H02](tickets/SH-H02.md) |
| [SH-Q06](tickets/SH-Q06.md) | Exercise answer-key and tool-access isolation | AVAILABLE — unclaimed | [H05](tickets/SH-H05.md) |
| [SH-Q07](tickets/SH-Q07.md) | Prove structural adaptation executes | AVAILABLE — unclaimed | [H07](tickets/SH-H07.md), [U12](tickets/SH-U12.md) |
| [SH-Q08](tickets/SH-Q08.md) | Prove replay equals committed state | AVAILABLE — unclaimed | [U10](tickets/SH-U10.md) |
| [SH-Q09](tickets/SH-Q09.md) | Prove the genome zoom remains truthful | AVAILABLE — unclaimed | [U05](tickets/SH-U05.md), [U11](tickets/SH-U11.md), [U14](tickets/SH-U14.md) |
| [SH-Q10](tickets/SH-Q10.md) | Exercise bounded context over accumulated history | AVAILABLE — unclaimed | [R08](tickets/SH-R08.md), [R10](tickets/SH-R10.md), [R12](tickets/SH-R12.md) |
| [SH-Q11](tickets/SH-Q11.md) | Produce the canonical real demonstration run | AVAILABLE — unclaimed | [Q01](tickets/SH-Q01.md), [Q02](tickets/SH-Q02.md), [Q03](tickets/SH-Q03.md), [Q04](tickets/SH-Q04.md), [Q05](tickets/SH-Q05.md), [Q06](tickets/SH-Q06.md), [Q07](tickets/SH-Q07.md), [Q08](tickets/SH-Q08.md), [Q09](tickets/SH-Q09.md), [H08](tickets/SH-H08.md), [U13](tickets/SH-U13.md) |
| [SH-Q12](tickets/SH-Q12.md) | Perform the final adversarial claim review | AVAILABLE — unclaimed | [Q10](tickets/SH-Q10.md), [Q11](tickets/SH-Q11.md) |
