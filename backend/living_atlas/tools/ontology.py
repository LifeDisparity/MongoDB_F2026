"""Exact lookup in SHA-256-pinned anatomy and developmental-stage OBO files.

This is a bounded term index, not an ontology reasoner. It preserves obsolete
IDs and replacement suggestions without treating them as accepted annotations.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re

from living_atlas.data.catalog import file_sha256


_FILES = {"FBbt": "ontologies/fly_anatomy.obo", "FBdv": "ontologies/fly_development.obo"}
_QUOTED = re.compile(r'^"((?:[^"\\]|\\.)*)"(?:\s+(EXACT|BROAD|NARROW|RELATED))?')


def _unescape(value: str) -> str:
    return re.sub(r"\\(.)", lambda match: {"n": "\n", "t": "\t", "W": " "}.get(match[1], match[1]), value)


def _key(value: str) -> str:
    return " ".join(value.split()).casefold()


def _obo_terms(path: Path):
    """Read required lookup fields; ignore relations and external imports."""
    current = None
    continuation = ""
    with path.open(encoding="utf-8") as stream:
        for raw in stream:
            line = continuation + raw.rstrip("\r\n")
            trailing_slashes = len(line) - len(line.rstrip("\\"))
            if trailing_slashes % 2:
                continuation = line[:-1]
                continue
            continuation = ""
            if line.startswith("["):
                if current is not None:
                    yield current
                current = {} if line == "[Term]" else None
                continue
            if current is None or not line or line.startswith("!") or ": " not in line:
                continue
            field, value = line.split(": ", 1)
            if field in {"id", "alt_id", "replaced_by", "consider"}:
                value = value.split()[0]
            if field in {"id", "name", "is_obsolete"}:
                current[field] = _unescape(re.split(r"(?<!\\)\s+!", value, maxsplit=1)[0].strip())
            elif field in {"alt_id", "replaced_by", "consider"}:
                current.setdefault(field, []).append(value)
            elif field == "synonym":
                match = _QUOTED.match(value)
                if match and match[2] == "EXACT":
                    current.setdefault("exact_synonyms", []).append(_unescape(match[1]))
            elif field == "def":
                match = _QUOTED.match(value)
                if match:
                    current["definition"] = _unescape(match[1])
        if continuation:
            raise ValueError("Incomplete OBO continuation")
        if current is not None:
            yield current


class OntologyResolver:
    def __init__(self):
        self._terms: dict[str, dict[str, dict]] = {}
        self._labels: dict[str, dict[str, set[str]]] = {}
        self._alternate: dict[str, dict[str, set[str]]] = {}
        self._provenance: dict[str, dict] = {}

    @classmethod
    def from_manifest(cls, path: str | Path, cache_dir: str | Path | None = None,
                      ontologies: tuple[str, ...] = ("FBbt", "FBdv")) -> "OntologyResolver":
        path = Path(path).resolve()
        manifest = json.loads(path.read_text(encoding="utf-8"))
        cache = Path(cache_dir) if cache_dir else path.parent.parent / "raw/flyaoc"
        resolver = cls()
        for ontology in ontologies:
            if ontology not in _FILES:
                raise ValueError("Only pinned FBbt and FBdv lookup is available")
            filename = _FILES[ontology]
            spec = manifest["dataset"]["files"][filename]
            candidate = cache / filename
            # Initial operator downloads used flat cache names; both layouts
            # must verify the identical full pin before any terms are indexed.
            if not candidate.exists():
                candidate = cache / Path(filename).name
            if not candidate.exists():
                raise FileNotFoundError(f"{filename} is not cached; import sources with --download --ontologies")
            if file_sha256(candidate) != spec["sha256"]:
                raise ValueError(f"Pinned ontology hash mismatch: {ontology}")
            terms, labels, alternate = {}, {}, {}
            for row in _obo_terms(candidate):
                term_id = row.get("id", "")
                if not term_id.startswith(ontology + ":"):
                    continue
                if term_id in terms or not row.get("name"):
                    raise ValueError("Duplicate or unnamed ontology term")
                definition = row.get("definition", "")
                terms[term_id] = {
                    "term_id": term_id, "label": row["name"],
                    "is_obsolete": row.get("is_obsolete") == "true",
                    "replaced_by": row.get("replaced_by", []), "consider": row.get("consider", []),
                    "definition": definition[:1500], "definition_truncated": len(definition) > 1500,
                }
                for label in [row["name"], *row.get("exact_synonyms", [])]:
                    labels.setdefault(_key(label), set()).add(term_id)
                for alt_id in row.get("alt_id", []):
                    alternate.setdefault(alt_id, set()).add(term_id)
            resolver._terms[ontology], resolver._labels[ontology], resolver._alternate[ontology] = terms, labels, alternate
            resolver._provenance[ontology] = {
                "dataset_repository": manifest["dataset"]["repository"],
                "dataset_revision": manifest["dataset"]["revision"],
                "file": filename, "sha256": spec["sha256"],
                "license_id": spec.get("license_id"), "term_count": len(terms),
            }
        return resolver

    def resolve_term(self, mention: str, ontology: str) -> dict:
        if ontology not in self._terms:
            raise ValueError("Ontology is not loaded; choose a loaded FBbt or FBdv index")
        if not isinstance(mention, str) or not mention.strip() or len(mention) > 512:
            raise ValueError("Term mention must contain 1-512 characters")
        mention = mention.strip()
        if mention in self._terms[ontology]:
            ids, match_type = {mention}, "primary_id"
        elif mention in self._alternate[ontology]:
            ids, match_type = self._alternate[ontology][mention], "alternate_id"
        else:
            ids, match_type = self._labels[ontology].get(_key(mention), set()), "exact_label_or_synonym"
        candidate_count = len(ids)
        candidates = [{**deepcopy(self._terms[ontology][term_id]), "match_type": match_type} for term_id in sorted(ids)[:10]]
        status = "not_found"
        if candidate_count > 1:
            status = "ambiguous"
        elif candidates:
            status = "obsolete" if candidates[0]["is_obsolete"] else "resolved"
        return {
            "status": status, "mention": mention, "ontology": ontology,
            "term_id": candidates[0]["term_id"] if status == "resolved" else None,
            "candidates": candidates, "candidate_count": candidate_count,
            "returned_count": len(candidates), "candidates_truncated": candidate_count > len(candidates),
            "provenance": deepcopy(self._provenance[ontology]),
            "resolution_note": "Exact ID, label or EXACT synonym only; broad/related synonyms are not equivalent. Obsolete replacements require review. A resolved identity does not establish biological entailment.",
        }
