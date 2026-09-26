# Living Atlas — start here

> Living Atlas is an AI that maps what genes do, remembers the evidence, and
> tests better ways to investigate.

## What we are building

A scientific workspace for maintaining a small, cited Drosophila gene atlas.
The main screen is a stable, inspectable evidence graph with time replay.
Workers investigate ambiguity, preserve experimental qualifiers and commit
source-backed claims. A separate loop proposes and evaluates changes to how
future investigations assemble context and route scientific review.

The user receives a maintained atlas and an exportable cited gene dossier.

## Why this fits the hackathon

Recursive Harnessing:
a model proposes an executable context/review policy change; a frozen evaluator
selects or rejects it on separate cases.

Long Horizon Engineering:
investigation state, original evidence, pending questions and dependencies
survive worker loss and evidence changes. Fresh workers receive bounded context
packets reconstructed from durable records.

We demonstrate these mechanisms. We do not claim validated operation across
billions of tokens or weeks.

## The four demo moments

1. Investigate: resolve Ten-a experimental scope through a targeted source read.
2. Improve: show a proposed runtime policy change and actual selection result.
3. Interrupt: terminate a worker; resume the same investigation.
4. Reconsider: withdraw a source in a labeled simulation; selectively reopen
   claims losing support while unrelated claims remain stable.

## Frozen stack

- React + TypeScript + React Flow.
- Python 3.11+ + FastAPI + LangGraph.
- MongoDB Atlas, including the supported MongoDB checkpoint integration.
- One configured model shared across fair experimental comparisons.
- AGR portable grounding utilities and adapted scientific instructions.
- A frozen FlyAOC-derived data subset with rights and provenance metadata.

## Scope

Expression and scoped perturbation observations first.
Broader GO-function curation is secondary.
Begin with a small declared cohort; aim for 12 genes in 4/4/4 splits.
Reduce before observing results if data preparation or runtime demands it.
Known showcase cases belong in development, never the final test.

## Verification

**NO UNIT TESTS. E2E ONLY.**
The complete application must demonstrate the four behaviors.
Build/type checks are allowed.
No fabricated metrics or passing fixture animations in the canonical demo.

## Documents

- [Architecture](ARCHITECTURE.md)
- [Contracts](CONTRACTS.md)
- [Scientific cases and evaluation](EVALUATION.md)
- [Visual and demo specification](DEMO.md)
- [E2E acceptance](E2E.md)
- [Roadmap](ROADMAP.md)
- [Agent coordination](AGENT_PLAYBOOK.md)
- [Reuse and sources](REUSE.md)
- [Ticket index](TICKETS.md)
- [Bootstrap implementation status](IMPLEMENTATION_STATUS.md)

## First work

Freeze contracts and build the real source -> model -> evidence -> Atlas -> UI
path immediately. Start frontend work against clearly labeled fixtures while
backend integration proceeds.

The bootstrap supplies production helper modules, not a completed application.
See IMPLEMENTATION_STATUS.md for the exact boundary.
