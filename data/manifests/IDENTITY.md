# Frozen identity lookup inputs

`gene_aliases.json` is an attributed subset of the FlyBase Symbol-Synonym
Correspondence Table from release `FB2026_03`, generated upstream 2026-08-31.
Its provenance includes the release URL and downloaded compressed file SHA-256.
The subset contains Ten-a, Ten-m and lola identities and aliases, plus collisions
with other Dmel genes. No gene summaries, expression/function annotations,
benchmark rows or gold labels are included.

The subset was formed by reading six tab-separated columns from every `FBgn`
row with organism abbreviation `Dmel` (32,192 rows), splitting the two synonym
columns on `|`, and retaining unique nonempty strings. For every current name,
symbol and alias of the three selected genes, all matching Dmel gene identities
were collected from the complete table. Multi-gene matches are retained under
`ambiguous_aliases`; subset selection therefore cannot make these aliases appear
unique. In this release, `Teneurin`, `Lola`, `eyeful`, `e`, `1.2` and `misguided`
have collisions. Case remains meaningful: do not case-fold fly gene symbols.
Every ambiguity candidate can be looked up again by its explicit primary ID,
including candidates outside the source cohort. Their unrelated aliases are
not indexed, and resolution does not add them to the source corpus.
Unknown/historical IDs remain unresolved; this file is not an obsolete-ID
mapping database. The alias artifact's own SHA-256 is exposed on every result
so all experimental arms can verify identical input.

Production interfaces:

```python
from living_atlas.tools.identity import GeneResolver
from living_atlas.tools.ontology import OntologyResolver

genes = GeneResolver.from_file("data/manifests/gene_aliases.json")
genes.resolve_gene("Ten-a", "NCBITaxon:7227")
terms = OntologyResolver.from_manifest(
    "data/manifests/showcase.json", cache_dir="data/raw/flyaoc"
)
terms.resolve_term("primary spermatocyte", "FBbt")
```

Gene lookup returns `resolved`, `ambiguous`, `not_found`, or `taxon_mismatch`.
Only `resolved` has a top-level `gene_id`; every candidate retains exact identity
and match type. A match proves identity only, not that a word in a paper is an
experimental mention of the gene. The API/workflow must preserve ambiguity.

Ontology initialization verifies complete file SHA-256s from `showcase.json`
before indexing. Standard cache paths are `ontologies/fly_anatomy.obo` and
`ontologies/fly_development.obo`; the initial flat cached filenames also work
after the same full hash check. Missing inputs raise `FileNotFoundError`; there
is no network fallback, silent updated ontology, or model-generated term ID.
Prepare files with the source-import CLI's `--download --ontologies` option.

Term lookup accepts only `FBbt` and `FBdv`. It checks exact primary IDs, alternate
IDs, then case/whitespace-normalized names and OBO `EXACT` synonyms. `BROAD`,
`NARROW` and `RELATED` synonyms do not become equivalent terms. Results preserve
obsolete terms, `replaced_by`, and `consider` without automatic replacement.
Only `resolved` supplies top-level `term_id`; `obsolete`, `ambiguous` and
`not_found` remain explicit. Multi-match results show the first 10 candidates,
the full count, and explicit truncation. Definitions are bounded to 1,500
characters with an explicit truncation flag. This index is not an ontology
reasoner and does not infer stage, anatomy or biological entailment.

Verification: Python syntax compilation only in this lane. Application lookup
and scientific acceptance are verified by the integrator through actual API and
browser flows. No isolated test suite is provided.
