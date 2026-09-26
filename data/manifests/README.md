# Pinned development source import

`showcase.json` pins FlyAOC revision
`8a766e6418e309ef869fbbadfc65c662ed20bdd8`, complete downloaded file SHA-256s,
article-record SHA-256s and normalized source versions. The selected corpus is
two development papers, **not** the planned frozen 12-gene benchmark. There
are no validation/final-test cases, scores or reference labels here.

From the repository root, with the backend installed (or `PYTHONPATH=backend`):

```sh
python3 -m living_atlas.data.import_sources --manifest data/manifests/showcase.json --cache-dir data/raw/flyaoc --download --ontologies
```

The first import downloads the 660 MB literature file and verifies its complete
hash before extracting the two allowlisted records. Later imports validate
the selected record caches and reuse the same source versions and chunk IDs.
Only `data/raw/` holds article text and ontologies; that directory is ignored.
The importer does not download benchmark, hidden-label or hidden-term files.
The optional ontology files are prepared for LA-05; they are not yet a term
resolution service. Article-specific rights come from the pinned upstream
license manifest and original article links, not the dataset's overall label.

Both selected articles have manuscript/text-mining restrictions. The application
may inspect the private imported text for this research workflow. Do not commit
or publish their full text. Public exports must retain source links and avoid
bulk restricted article text. Source snapshots contain metadata only; chunks
contain the private text.

The upstream corpus omits Ten-a figure captions and classifies most of that
paper's experimental paragraphs as `INTRO`. Retrieval preserves these labels.
For its developmental showcase, search without a section filter (or include
`INTRO`) and inspect the linked original paper for figure details. This source
subset does not replace independently checked evaluation fixtures.

## Integration interface

```python
from living_atlas.data import SourceCatalog
from living_atlas.tools.evidence import EvidenceTools

catalog = SourceCatalog.from_manifest(
    "data/manifests/showcase.json", cache_dir="data/raw/flyaoc"
)
tools = EvidenceTools(catalog)
matches = tools.search_evidence("FBgn0267001", "DA1 VA1d knockdown", [])
match = matches["matches"][0]
page = tools.read_chunk(match["chunk_id"], match["source_version"])
evidence = tools.record_evidence(
    [page["spans"][0]["span_id"]], match["source_version"]
)
```

`catalog.sources` and `catalog.chunks` are detached lists for the repository's
immutable import. `source_version` and `content_sha256` are the complete
SHA-256 of normalized source text. The normalization joins the unmodified
title, abstract and paragraphs (sorted by upstream section type) with two
newlines. No model rewrites source text. `Chunk.start_offset/end_offset` locate
the paragraph in that normalized source; `Evidence.start_offset/end_offset`
locate the quote **within the chunk**. Offsets count Python/Unicode code points,
not UTF-8 bytes or JavaScript UTF-16 code units. Browsers should show the
server-reconstructed quote rather than re-slicing text with JavaScript offsets.

Search returns `matches`, `total_count`, `returned_count`, `next_cursor`, and
`complete`. Each match includes source/version/chunk identity, section metadata,
score and a visibly truncated preview. Read returns `spans` (with exact text,
`span_id`, `char_start`, `char_end`), source metadata, `next_cursor` and `complete`.
Continuation cursors are opaque and bound to the query/catalog or chunk/version.
Follow a returned cursor with the same request. All model-visible search/read
responses are measured using AGR's bounded-result utilities. Oversized single
spans produce an explicit budget error; no text is silently truncated.

`record_evidence` accepts only spans returned by that tool session, rejects
changed versions and forged IDs, and returns canonical Evidence contract
records. It does not commit them. A resumed worker should re-read the chunk to
obtain spans in its new session. `evidence_detail(evidence_id)` reconstructs
the canonical quote and source metadata; the API must first establish that the
requested evidence was accepted in the specified run. This separation prevents
an arbitrary valid source span from masquerading as accepted evidence.

The repository must recheck run-specific source availability and source/chunk
identity in the acceptance transaction. Source retrieval alone does not certify
biological entailment or create a supported claim.

## Verification boundary

The actual import completed with 2 source versions and 100 paragraph chunks.
Python compilation completed. No unit tests were created or run. Browser/API/
Atlas E2E acceptance is the integration owner's next step; this directory does
not claim that flow or the full scientific experiment has passed.
