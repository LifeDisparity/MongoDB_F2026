# Active implementation ownership

Claimed before implementation on 2026-09-26.
Integration branch: `codex/living-atlas-wave1-20260926`.
Base: published Living Atlas bootstrap (PR #31).

| Owner | Taken tickets | Scope |
|---|---|---|
| Codex integrator | LA-01, LA-02, LA-14 | Contracts, setup, API composition and integration |
| Codex data/evidence | LA-04, LA-06 | Pinned source import, rights and canonical evidence tools |
| Codex storage/events | LA-11, LA-13 | MongoDB persistence, atomic operations and ordered events |
| Codex frontend | LA-20, LA-21, LA-22, LA-23 | Workspace, stable graph, inspector, live/replay |
| Codex data/science, wave 2 | LA-05, LA-07 | Frozen identity/ontology lookup and shared scientific prompts |
| Codex model adapter, wave 2 | LA-09 | Structured provider responses, usage and bounded failures |
| Codex frontend, wave 2 | LA-24 | Persisted policy differences and measured evaluation display |

Separate worktrees and ticket branches isolate each writer. Shared contracts and
root configuration remain integrator-owned. Do not take these tickets without
coordinating with the current owner. Tickets remain open until their documented
acceptance is demonstrated; code or fixture execution alone is not completion.

First integration target: a runnable browser/API/MongoDB source-and-evidence
workspace, with explicitly labeled engineering fixtures for availability and
replay. Model investigation, checkpointed workflow and policy optimization are
subsequent tickets; fixture behavior must not be represented as those results.

## Integrated handoff, 2026-09-26

Both waves are integrated in draft PR #32. The full engineering browser run at
commit `c3760a2` passed 16 recorded checks in 6.118 seconds; see
`artifacts/manifests/wave2-e2e.json`. This duration is the engineering verification,
not scientific model execution. Model configuration, LangGraph workflow and
Atlas/canonical scientific acceptance remain pending. Do not close their tickets.
