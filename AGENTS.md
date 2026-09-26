# Living Atlas: agent instructions

## Non-negotiable user direction

**NO UNIT TESTS. E2E ONLY. WE NEED SPEED.**

Do not write, port, or commit unittest/pytest/component test suites.
Build/type/syntax checks are permitted.
Validate behavior through complete application flows.
Scientific benchmark fixtures remain necessary product inputs; they are not a
software unit-test suite.

## Product

Living Atlas is an AI that maps what genes do, remembers the evidence, and tests
better ways to investigate.

Four observable behaviors define the product:
1. Targeted evidence acquisition resolves or changes a scientific decision.
2. A model proposes an executable harness change and a separate evaluator
   promotes or rejects it using frozen criteria.
3. A fresh worker resumes a persistent investigation.
4. Changing evidence availability reopens only dependent conclusions.

## Read first

- docs/START_HERE.md
- docs/ARCHITECTURE.md
- docs/CONTRACTS.md
- docs/EVALUATION.md
- docs/E2E.md
- Your docs/tickets/LA-XX.md and docs/agents/LA-XX.md

## Delivery discipline

Work on a bounded ticket and named branch. Respect file ownership.
One integrator owns shared contracts, root dependency/config files and API
composition. Coordinate before changing these.

Deliver working vertical slices. Avoid speculative infrastructure.
Do not claim completion for code that has not been integrated.
Handoff: commit/PR, changed paths, interfaces, actual E2E evidence, limitations,
and the next owner/dependency.

Do not overwrite other contributors' changes.
Do not introduce a second database, distributed scheduler, workflow editor,
authentication system, 3D graph, or giant runtime agent swarm.

## Runtime

Python/FastAPI/LangGraph/MongoDB Atlas.
React/TypeScript/React Flow.
One durable workflow per investigation, at most two concurrent investigations.
Checkpoints own execution progress.
Immutable source versions and evidence references own scientific memory.
Availability is a run-scoped overlay, not a rewrite of a paper.

## Scientific integrity

Expression is not function.
Negative results are specific to the reported experiment.
Keep gene, tissue, stage, assay, intervention and cell class explicit.
Canonical quotations are reconstructed from server-held source spans.
Source withdrawal changes support, not biological truth.
Do not invent baseline failures, autonomous decisions, performance gains,
citations, run duration, or billion-token validation.

All experimental arms receive known aliases and strong scientific instructions.
Keep gold/reference labels inaccessible to worker retrieval.
Final-test results never feed back into optimization.

## Allowed harness changes

Context assembly and conditional scientific scope review only.
Keep evaluator, source provenance, model identity, permissions and budgets
outside the mutable policy.
A rejected candidate demonstrates evaluation, not successful self-improvement.

## Reuse

AGR pin: 9d478db87997fb7695ee268293d5ad58cbb4a2e2.
Retain its MIT license and UPSTREAM.md.
Do not copy FlyAOC implementation source without an explicit license/permission.
Do not commit credentials, downloaded corpora, or restricted full article text.
