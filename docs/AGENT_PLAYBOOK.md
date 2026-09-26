# Parallel agent playbook

## Coordination

The backlog contains 30 bounded tickets and one copy-ready assignment per ticket.
These are implementation lanes, not 30 runtime model agents.

One integrator owns shared contracts, API composition, root dependencies and
cross-cutting configuration. Other agents work only in assigned paths.
Coordinate interface changes before editing another lane's files.

Start with the highest-value independent work:
- LA-01 contracts;
- LA-04 data preparation;
- LA-07 scientific instructions;
- LA-09 model adapter;
- LA-11 storage;
- LA-20 frontend shell against the contract fixture.

The bootstrap begins LA-03, LA-12 and LA-15 with production source.
They remain open until full-application E2E integration.

## Waves

Wave A:
contracts, scaffold, grounding, data, scientific review and UI fixture.

Wave B:
identity, evidence tools, context packets, model adapter, storage, graph,
inspector and replay reducer.

Wave C:
runtime, API, events, policy, optimizer, experiment runner and metrics panel.

Wave D:
real interruption, source-withdrawal E2E, canonical run, export and rehearsal.

Use as many independent build lanes as the team can review.
Do not run multiple writers on the same files.
When only three agent slots are available, keep one backend/runtime lane,
one data/evaluation lane and one frontend lane active.

## Working branch

Create a ticket branch from the shared bootstrap/integration branch.
Use git worktrees or separate clones for simultaneous coding sessions.
Suggested branch naming: codex/LA-XX-short-description.

## Assignment text

Individual assignments are in docs/agents/LA-XX.md.
Each includes its scope, paths, dependencies, acceptance and handoff.
An agent must report a concrete blocker rather than silently rewriting scope.

## Handoff

Return:
- commit/PR and exact paths;
- public interfaces;
- full-app E2E flow executed and actual result;
- unresolved limitations;
- next dependency/owner.

No unit tests.
No code-only completion claims.
No fake model/Atlas execution.
No benchmark gain claims until measured.

## Integration

Integrate small coherent commits.
Keep scientific evaluation answers out of worker retrieval.
Keep temporary synthetic fixtures labeled.
Replace presentation fixtures with the canonical recorded run.
Freeze the final hour around the demonstrated flow.
