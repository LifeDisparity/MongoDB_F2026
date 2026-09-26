# Reuse, licensing and research sources

## AGR

Repository:
https://github.com/alliance-genome/agr_ai_curation

Pinned revision:
9d478db87997fb7695ee268293d5ad58cbb4a2e2

Reuse production helpers:
backend/src/agr_ai_curation_runtime/evidence_spans.py
backend/src/agr_ai_curation_runtime/tool_result_bounds.py

MIT copyright: 2025 Alliance of Genome Resources.
Retain original LICENSE and exact provenance.

Adapt scientific rules from:
packages/alliance/agents/gene_expression/prompt.yaml
packages/alliance/agents/gene_extractor/prompt.yaml
packages/alliance/agents/gene_extractor/group_rules/fb.yaml

Do not import the complete AGR runtime. Agent schemas/builders depend on its
host backend and domain-conversion machinery. Replace their interfaces with
our small tools.

AGR already has sophisticated curation, grounding, recovery, evaluation and
prompt-suggestion machinery. Do not claim we invented those capabilities.
Our contribution is the demonstrated automatic evaluated policy loop coupled
to persistent scientific dependencies.

## FlyAOC

Repository:
https://github.com/xingjian-zhang/flyaoc

Inspected revision:
e53ca328a7414be227d00a263b61d973a2d4d975

Dataset:
https://huggingface.co/datasets/anonymous-042/flyaoc

No code license was found in the inspected repository.
Do not vendor its implementation without permission/license.
Dataset rights are mixed; retain source-specific rights and attribution.
Resolve and pin the actual downloaded revision and hashes.

The published expression scorer does not establish stage/assay/citation
correctness. Our pilot explicitly adds scientific scope evaluation.

## Other components

MongoDB LangGraph integration:
https://www.mongodb.com/docs/atlas/ai-integrations/langgraph/

LangGraph:
https://github.com/langchain-ai/langgraph

MongoDB integration license:
https://github.com/langchain-ai/langchain-mongodb/blob/main/LICENSE

React Flow:
https://reactflow.dev/
https://github.com/xyflow/xyflow/blob/main/LICENSE

Pronto:
https://github.com/althonos/pronto

## Scientific papers

Ten-a:
https://pmc.ncbi.nlm.nih.gov/articles/PMC3345284/

Lola:
https://pmc.ncbi.nlm.nih.gov/articles/PMC4006830/

Application code licensing does not license scientific article text.
Use source links and permitted attributed excerpts in public artifacts.
