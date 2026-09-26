# Visual and demonstration specification

## One sentence

Living Atlas is an AI that maps what genes do, remembers the evidence, and tests
better ways to investigate.

## Screen

Full-canvas evidence graph.
Prominent gene circles.
Atomic experimental claims as readable branch cards.
Small paper/evidence anchors.
Right-hand evidence inspector appears on selection.
Bottom replay timeline.
Small expandable harness-evolution panel.

Use deterministic positions; no force simulation.
Keep roughly 15-25 nodes visible and collapse evidence groups.
Expression, perturbation and function relations must look distinct.
Stage/assay are attributes of a claim, not unrelated global edges.

Dark graphite background, strong readable typography.
Cyan = supported/active.
Dotted = unresolved.
Amber = support missing/review needed.
Violet = proposed policy.
Always accompany color with words/icons.

## Three camera movements

Zoom out: see the small atlas and actual run counts.
Zoom in: question -> chosen evidence -> qualified conclusion.
Scrub time: inspect what changed and why.

Every animation is caused by an accepted recorded event.
Use one reducer for live and replay states.

## Signature transition

Withdraw one source in a labeled simulation.
An amber pulse follows its evidence dependencies.
Only dependent claims change state.
Unrelated branches remain stable.
Rewind restores the historical support state.
Never label unsupported claims biologically false.

## Three-minute sequence

0:00-0:15:
pitch, atlas, actual run counts.

0:15-1:00:
Ten-a scope question, targeted retrieval and experimental distinctions.

1:00-1:40:
model-proposed policy diff, executed route, actual selection result.

1:40-2:05:
terminate/restart a worker, resume pending work.

2:05-2:40:
source-withdrawal simulation and selective reopening.

2:40-3:00:
rewind, open original evidence, export cited dossier.

## Labels

LIVE and REPLAY must be explicit.
Replay shows original execution duration.
Synthetic fixtures never appear as a real canonical run.
Do not imply the final evaluation runs instantly.
Show actual cohort size, raw counts and cost.

## Cuts

No 3D.
No giant moving hairball.
No workflow editor.
No auth.
No chat-first dashboard.
No decorative animations disconnected from real events.
