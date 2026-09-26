"""Deterministic, case-sensitive gene identity from a frozen alias subset.

The subset retains collisions discovered against the complete pinned Dmel gene
table. Thus a common alias cannot silently become unique after corpus pruning.
These are identity records, never gene summaries or benchmark answers.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re


class GeneResolver:
    def __init__(self, manifest: dict, manifest_sha256: str):
        if manifest.get("schema_version") != 1 or manifest.get("match_rule") != "case_sensitive_exact":
            raise ValueError("Unsupported alias manifest")
        self.manifest_sha256 = manifest_sha256
        self._source = deepcopy(manifest["source"])
        self._scope = manifest["scope"]
        self._index: dict[str, dict[str, dict]] = {}
        self._primary: dict[str, dict] = {}
        for gene in manifest["genes"]:
            candidate = self._candidate(gene)
            gene_id = candidate["gene_id"]
            if gene_id in self._primary:
                raise ValueError("Duplicate primary gene ID")
            self._primary[gene_id] = candidate
            aliases = gene.get("aliases", [])
            if not isinstance(aliases, list) or any(not isinstance(v, str) or not v for v in aliases):
                raise ValueError("Invalid gene aliases")
            for mention in {candidate["symbol"], candidate["name"], *aliases}:
                if mention:
                    self._index.setdefault(mention, {})[gene_id] = candidate
        for alias, rows in manifest.get("ambiguous_aliases", {}).items():
            if not isinstance(alias, str) or not alias or not isinstance(rows, list):
                raise ValueError("Invalid alias collision")
            for gene in rows:
                candidate = self._candidate(gene)
                self._index.setdefault(alias, {})[candidate["gene_id"]] = candidate

    @staticmethod
    def _candidate(gene: dict) -> dict:
        if not isinstance(gene, dict) or not re.fullmatch(r"FBgn[0-9]{7}", gene.get("gene_id", "")):
            raise ValueError("Invalid FlyBase gene ID")
        if any(not isinstance(gene.get(key), str) for key in ("symbol", "name", "taxon")):
            raise ValueError("Invalid gene identity fields")
        if not gene["symbol"] or gene["taxon"] != "NCBITaxon:7227":
            raise ValueError("Alias subset requires explicit Dmel identity")
        return {key: gene[key] for key in ("gene_id", "symbol", "name", "taxon")}

    @classmethod
    def from_file(cls, path: str | Path, expected_sha256: str | None = None) -> "GeneResolver":
        raw = Path(path).read_bytes()
        digest = sha256(raw).hexdigest()
        if expected_sha256 is not None and expected_sha256 != digest:
            raise ValueError("Alias manifest hash mismatch")
        return cls(json.loads(raw), digest)

    def resolve_gene(self, mention: str, taxon: str = "NCBITaxon:7227") -> dict:
        if not isinstance(mention, str) or not mention.strip() or len(mention) > 256:
            raise ValueError("Gene mention must contain 1-256 characters")
        if not isinstance(taxon, str) or not taxon.strip():
            raise ValueError("An explicit taxon is required")
        mention = mention.strip()
        taxon = {"7227": "NCBITaxon:7227", "Drosophila melanogaster": "NCBITaxon:7227"}.get(taxon.strip(), taxon.strip())
        # Accept a single known provider prefix, not stacked namespaces such
        # as FB:FLYBASE:FBgn... that are not valid FlyBase identifiers.
        identifier = re.sub(r"^(?:FB|FLYBASE):", "", mention, count=1)
        if identifier in self._primary:
            candidates = [self._primary[identifier]]
            match_type = "primary_id"
        else:
            candidates = list(self._index.get(mention, {}).values())
            match_type = "exact_alias"
        matches = [{**deepcopy(row), "match_type": (
            "current_symbol" if mention == row["symbol"] and match_type != "primary_id"
            else "current_name" if mention == row["name"] and match_type != "primary_id"
            else match_type
        )} for row in candidates if row["taxon"] == taxon]
        matches.sort(key=lambda row: row["gene_id"])
        status = "resolved" if len(matches) == 1 else "ambiguous" if len(matches) > 1 else "not_found"
        if taxon != "NCBITaxon:7227":
            status = "taxon_mismatch"
        return {
            "status": status, "mention": mention, "taxon": taxon,
            "gene_id": matches[0]["gene_id"] if status == "resolved" else None,
            "candidates": matches, "candidate_count": len(matches),
            "provenance": {**deepcopy(self._source), "alias_manifest_sha256": self.manifest_sha256},
            "scope": self._scope,
            "resolution_note": "Exact case-sensitive identity only. A match does not establish that a passage discusses this gene. Unlisted or historical IDs remain unresolved.",
        }
