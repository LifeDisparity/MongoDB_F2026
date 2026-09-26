# Living Atlas ticket index

**NO UNIT TESTS. E2E ONLY. SPEED.**

The bootstrap begins LA-03, LA-12 and LA-15. Their full-app integration and E2E acceptance remain pending.

| Ticket | Work | Lane | Dependencies |
|---|---|---|---|
| LA-01 | Freeze shared contracts | contracts | none |
| LA-02 | Repository scaffold and launch configuration | integration | none |
| LA-03 | Vendor AGR production grounding utilities | grounding | none |
| LA-04 | Import pinned corpus and rights manifest | data | LA-01 |
| LA-05 | Gene identity and ontology lookup | ontology | LA-04 |
| LA-06 | Grounded evidence tools | evidence | LA-03, LA-04 |
| LA-07 | Adapt scientific reader instructions | biology | LA-01, LA-03 |
| LA-08 | Bounded context packets | context | LA-01, LA-06 |
| LA-09 | Structured model adapter and usage | models | LA-01 |
| LA-10 | Persistent investigation workflow | runtime | LA-06, LA-07, LA-08, LA-09 |
| LA-11 | Atlas repositories and atomic acceptance | storage | LA-01 |
| LA-12 | Scientific dependency transitions | dependencies | LA-01 |
| LA-13 | Ordered events and consistent snapshots | events | LA-01, LA-11 |
| LA-14 | FastAPI integration endpoints | api | LA-10, LA-11, LA-13 |
| LA-15 | Independent evaluation core | evaluation | LA-01 |
| LA-16 | Scientific fixtures and frozen splits | scientific-evaluation | LA-04, LA-05 |
| LA-17 | Policy schema and immutable controls | policy | LA-01, LA-08 |
| LA-18 | Model-proposed policy optimizer | optimizer | LA-09, LA-15, LA-17 |
| LA-19 | Fair P0 H0 H1 experiment runner | experiments | LA-10, LA-15, LA-16, LA-18 |
| LA-20 | Frontend application shell | ui-shell | LA-01 |
| LA-21 | Stable scientific evidence graph | ui-graph | LA-20 |
| LA-22 | Investigation and evidence inspector | ui-evidence | LA-20 |
| LA-23 | Live and replay controller | ui-replay | LA-01, LA-20 |
| LA-24 | Harness evolution and measured metrics | ui-policy | LA-20 |
| LA-25 | Cited dossier export | export | LA-11, LA-14 |
| LA-26 | Real worker interruption E2E | reliability | LA-10, LA-11, LA-14 |
| LA-27 | Canonical scientific run and replay | canonical-run | LA-19, LA-23, LA-26 |
| LA-28 | Visual QA and three-minute rehearsal | demo | LA-21, LA-22, LA-23, LA-24, LA-27 |
| LA-29 | Operator setup and launch runbook | operations | LA-02, LA-11, LA-14 |
| LA-30 | Attribution and public-claim audit | provenance | LA-03, LA-04, LA-27 |

Detailed tickets: docs/tickets/LA-XX.md.
Copy-ready assignments: docs/agents/LA-XX.md.
Do not close an issue merely because a source module exists.
