# Living Atlas implementation status

## Integrated and exercised

The evidence workspace runs end to end through React/React Flow, FastAPI and a
real MongoDB replica set. It includes typed contracts, atomic accepted operations,
immutable source/chunk/evidence records, run-specific availability overlays,
ordered events, stable graph, canonical evidence inspector, replay and JSON
dossier export.

Two genuine FlyAOC-derived development papers are pinned by dataset revision,
file/record/source hashes and article-specific rights. Search, chunk reads and
canonical span pinning work through the browser and survive API process restart.
Restricted full text remains in ignored local storage.

The explicit engineering fixture demonstrates A:S1, B:S1+S2, C:S3. Browser E2E
verifies selective withdrawal, preserved historical evidence, review-required
restoration, replay parity, duplicate delivery, operation collision rejection,
export and actual API SIGKILL/restart. This is not LangGraph worker recovery.

See [the recorded engineering run](../artifacts/manifests/wave1-e2e.json) and
[installation/launch commands](OPERATIONS.md).
No unit tests were added or run. Frontend build and Python compilation pass.

## Still pending

- Configured Atlas execution (the repository uses MongoDB transactions, verified locally).
- Real-model investigation and accepted scientific claims.
- LangGraph checkpointed workflow, worker recovery and bounded context routing.
- Frozen scientific decision/reference fixtures and fair P0/H0/H1 experiments.
- Model-proposed policy optimization, executed validation and measured selection.
- Canonical scientific replay and its presentation rehearsal.
- Complete readable cited-dossier export beyond the current JSON export.

The two-paper development source subset is not a frozen benchmark. Ten-a figure
captions are absent from the selected upstream corpus, and upstream experimental
paragraphs are labeled INTRO. Do not claim the entire scientific showcase is
established by source import or exact quote matching.

## Active next lanes

LA-05/LA-07: deterministic identity/ontology lookup and shared scientific prompts.
LA-09: configured structured model adapter with actual usage and bounded failures.
LA-24: persisted policy differences and measured evaluation display.

These lanes are claimed before coding in [ACTIVE_WORK](ACTIVE_WORK.md) and the
GitHub issues. Their code is not complete until integrated and appropriately
verified. Tickets requiring model/Atlas/canonical runs remain open.

## Preserved production foundations

AGR helpers remain unchanged at the verified upstream revision.
The dependency transition and evaluator cores from the bootstrap are reused.
The evaluator/benchmark and self-improvement claims are not exercised by the
engineering browser run.
