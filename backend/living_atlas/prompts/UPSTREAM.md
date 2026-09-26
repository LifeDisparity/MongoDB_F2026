# Scientific instructions provenance

The scientific rules are adapted from Alliance of Genome Resources' AGR AI
Curation repository, commit `9d478db87997fb7695ee268293d5ad58cbb4a2e2`:

- `packages/alliance/agents/gene_expression/prompt.yaml`, SHA-256
  `939a4ab76a82650637991a013fdc3eba77ca348376519d192b1aa1316f02076f`
- `packages/alliance/agents/gene_extractor/prompt.yaml`, SHA-256
  `dc1d274d938439aca63864e1c9948453a6aee8df72e447a61ff21401bc8841b4`
- `packages/alliance/agents/gene_extractor/group_rules/fb.yaml`, SHA-256
  `509c0b583f6173a8859e9e34fdc838b3d9eb1e6704c8657257daa78014b4dd41`

Source: <https://github.com/alliance-genome/agr_ai_curation/tree/9d478db87997fb7695ee268293d5ad58cbb4a2e2/packages/alliance/agents>

Copyright 2025 Alliance of Genome Resources; MIT license. The original license
is retained at `backend/living_atlas/vendor/agr/LICENSE`.

Adaptation keeps source-span grounding, experimental-evidence gates, direct
versus prior-work distinctions, explicit gene/species context, common-word
disambiguation, marker/rescue exclusions, negative-observation scope, and
unresolved controlled identities. Living Atlas uses its small deterministic
`resolve_gene`/`resolve_term` tools and its own claim contract in place of AGR's
host-specific validators and builder envelopes. Added rules preserve atomic
perturbation scope, run-specific source availability, bounded follow-up reads,
fresh-worker evidence references, and separation from frozen evaluation.

The common rules are identical in investigator and reviewer prompts and are
intended to be identical across P0/H0/H1. The role addition changes the assigned
job, not scientific acceptance criteria. No showcase answers, benchmark labels,
FlyAOC implementation source, or biological example outcomes are embedded.

`load_scientific_prompt(role)` returns the production instructions.
`common_scientific_rules()` returns the arm-independent base.
`prompt_manifest()` supplies hashes to persist with runs/evaluations.

These instructions do not guarantee scientific correctness. Acceptance still
requires real source/model/workflow/Atlas/browser E2E and scoped evidence review.
