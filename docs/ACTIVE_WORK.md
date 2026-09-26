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

Separate worktrees and ticket branches isolate each writer. Shared contracts and
root configuration remain integrator-owned. Do not take these tickets without
coordinating with the current owner. Tickets remain open until their documented
acceptance is demonstrated; code or fixture execution alone is not completion.

First integration target: a runnable browser/API/MongoDB source-and-evidence
workspace, with explicitly labeled engineering fixtures for availability and
replay. Model investigation, checkpointed workflow and policy optimization are
subsequent tickets; fixture behavior must not be represented as those results.
