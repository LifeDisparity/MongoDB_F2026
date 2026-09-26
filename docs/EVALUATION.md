# Scientific cases and evaluation

## What we must establish

Agency:
a decision-specific evidence request changes or resolves a conclusion.

Adaptation:
a model proposes an executable policy change that is independently evaluated.

Continuity:
an investigation survives process loss and evidence updates.

These are separate claims and need separate evidence.

## Scientific development showcase

Paper:
https://pmc.ncbi.nlm.nih.gov/articles/PMC3345284/

Question:
Does changing Ten-a disrupt matching in every examined projection-neuron class?

Reported observations:
- Reducing Ten-a in DA1 PNs causes mismatching with Or47b neurons.
- Reducing Ten-a in VA1d/DC3 PNs does not cause mismatching in the reported assays.
- Increasing Ten-a in DA1 PNs does not produce ectopic connections with the
  tested non-partner classes.
- Increasing Ten-a in VA1d/DC3 PNs produces ectopic matching with Or23a neurons.

Use the relevant results and Figures 3-4/captions.
Preserve intervention, cell class, observation and tested scope.
Do not interpret a negative observation as universal biological absence.

The paper also contains different genes, assays and developmental contexts in
Figure 2. Do not confuse adult Ten-m reporter panels with developmental Ten-a
antibody observations.

Start with an unresolved question, not a fabricated model mistake.
This is a development/showcase case and cannot be final held-out evidence.

Unrelated expression branch:
https://pmc.ncbi.nlm.nih.gov/articles/PMC4006830/
The Lola study reports isoform expression in primary spermatocytes.
Verify the exact selected passage and isoform qualifier before demonstrating.

## Arms

P0: competent fixed retrieval -> structured extraction -> validation pipeline.
H0: persistent investigation harness with frozen configuration.
H1: same harness using the candidate selected on validation.

All share:
gene inputs, known aliases, scientific instructions, source permissions,
ontology versions, model/decoding settings, paper limits and spending caps.

P0 must already preserve qualifiers and retrieve experimental context.
Do not weaken it to manufacture improvement.

## Dataset

Use the FlyAOC dataset under its stated terms:
https://huggingface.co/datasets/anonymous-042/flyaoc

Resolve and pin the actual dataset revision and file SHA-256s during import.
Record article-specific rights.
Do not copy unlicensed FlyAOC implementation code.

Aim for 12 genes, 4 development / 4 validation / 4 final test.
Reduce before looking at results if needed.
Group shared papers into the same split when possible; record residual overlap.
Do not expose gold labels, curated answers or frozen predictions to runtime tools.

A source subset changes reachable gold. Call this a FlyAOC-derived local pilot.
Report the source manifest and denominator; do not compare the local metric
directly with published full-corpus semantic scores.

## Measurements

Primary:
correct decisions on a small frozen human-checked set, including required
identity/stage/assay/intervention/scope qualifiers.

Secondary:
pilot_exact_anatomy_recall_at_10, explicitly exact matching.

Support:
source fidelity plus a fixed human-checked support audit.
A valid quote alone does not prove entailment.

Operations:
completion, actual usage/cost, duplicate acceptance, restart recovery and
selective source-dependency propagation.

Missing/failed decisions count as incorrect.
Missing/failed gene outputs remain in the reference denominator.
Duplicate/unknown gene submissions reject.
No invented accuracy score.

## Promotion

Fix before seeing candidate results:
- validation split only;
- identical manifest/model/budget/case IDs and denominators;
- finalized runs with provenance and budget invariants passing;
- no decision, support-audit or reference-coverage regression;
- either more correct decisions or at least 15% lower total cost.

Actual total cost includes investigator/reviewer calls and retries.
Record optimizer cost separately and show it too.

Select once on validation, freeze, then run final test once.
Record all attempted patches and rejected results.
If there is no gain, retain H0 and report rejection.
A tiny pilot does not establish general superiority.

## E2E requirement

Run the experiment through the application:
proposal -> execution -> stored evaluation -> promotion/rejection -> UI display.
Do not substitute isolated unit tests for this flow.
