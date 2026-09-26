"""Exact-source retrieval and evidence identities, without model-authored quotes."""
from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256
import json
import re

from living_atlas.data import SourceCatalog
from living_atlas.vendor.agr.evidence_spans import (
    build_evidence_spans, parse_evidence_span_id, resolve_evidence_span_id,
)
from living_atlas.vendor.agr.tool_result_bounds import (
    ToolResultBudgetError, budget_failure, fit_page,
)


def _hash(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _cursor(scope: str, index: int) -> str:
    return base64.urlsafe_b64encode(json.dumps([scope, index]).encode()).decode()


def _offset(cursor: str | None, scope: str, total: int) -> int:
    if cursor is None:
        return 0
    try:
        saved_scope, index = json.loads(base64.b64decode(cursor, altchars=b"-_", validate=True))
    except (ValueError, TypeError, UnicodeError) as error:
        raise ValueError("Invalid continuation cursor") from error
    if saved_scope != scope:
        raise ValueError("Continuation cursor belongs to a different request or source version")
    if type(index) is not int or not 0 <= index <= total:
        raise ValueError("Invalid continuation offset")
    return index


class EvidenceTools:
    """One catalog can be shared; acceptance still requires repository recheck.

    This class performs no mutations to accepted scientific records. The
    repository checks run-specific availability in the same transaction that
    accepts the evidence and corresponding event.
    """

    def __init__(self, catalog: SourceCatalog, max_result_bytes: int = 16000):
        if type(max_result_bytes) is not int or not 2048 <= max_result_bytes <= 65536:
            raise ValueError("Tool result budget must be between 2048 and 65536 bytes")
        self.catalog = catalog
        self.max_result_bytes = max_result_bytes
        self._evidence: dict[str, dict] = {}
        self._span_lookup: dict[str, dict] = {}
        self._chunk_spans: dict[str, list[dict]] = {}
        for chunk in catalog.chunks:
            spans = [span.to_dict() for span in build_evidence_spans(
                chunk_id=chunk["chunk_id"], chunk_text=chunk["text"],
                section_title=chunk["section_title"],
            )]
            self._chunk_spans[chunk["chunk_id"]] = spans
            for span in spans:
                self._span_lookup[span["span_id"]] = span
                evidence = self._canonical_evidence(span, chunk)
                self._evidence[evidence["evidence_id"]] = evidence

    @staticmethod
    def _canonical_evidence(span: dict, chunk: dict) -> dict:
        quote = chunk["text"][span["char_start"]:span["char_end"]]
        return {
            "evidence_id": "ev_" + _hash([chunk["source_id"], chunk["source_version"], span["span_id"]]),
            "source_id": chunk["source_id"], "source_version": chunk["source_version"],
            "chunk_id": chunk["chunk_id"], "span_id": span["span_id"],
            "start_offset": span["char_start"], "end_offset": span["char_end"],
            "quote_sha256": sha256(quote.encode("utf-8")).hexdigest(),
        }

    def search_evidence(self, gene_id: str, query: str,
                        section_types: list[str] | None = None,
                        cursor: str | None = None) -> dict:
        if not isinstance(query, str) or len(query) > 2000:
            raise ValueError("Query must be a string of at most 2000 characters")
        if section_types is not None and (
            not isinstance(section_types, list) or any(not isinstance(kind, str) for kind in section_types)
        ):
            raise ValueError("section_types must be a list of strings")
        source_ids = self.catalog.gene_source_ids(gene_id)
        kinds = set(section_types or [])
        terms = set(re.findall(r"[\w-]+", query.casefold()))
        matches = []
        for chunk in self.catalog.chunks:
            if chunk["source_id"] not in source_ids or (kinds and chunk["section_type"] not in kinds):
                continue
            words = set(re.findall(r"[\w-]+", chunk["text"].casefold()))
            score = len(terms & words)
            if terms and score == 0:
                continue
            matches.append({
                "chunk_id": chunk["chunk_id"], "source_id": chunk["source_id"],
                "source_version": chunk["source_version"],
                "section_type": chunk["section_type"], "section_title": chunk["section_title"],
                "score": score, "preview": chunk["text"][:240],
                "preview_truncated": len(chunk["text"]) > 240,
                "read_tool": "read_chunk",
            })
        matches.sort(key=lambda row: (-row["score"], row["chunk_id"]))
        scope = _hash([self.catalog.manifest_sha256, gene_id, query, sorted(kinds)])
        start = _offset(cursor, scope, len(matches))

        def render(page: list, count: int) -> dict:
            end = start + count
            return {
                "status": "ok", "gene_id": gene_id, "matches": page,
                "total_count": len(matches), "returned_count": count,
                "next_cursor": _cursor(scope, end) if end < len(matches) else None,
                "complete": end >= len(matches),
                "manifest_sha256": self.catalog.manifest_sha256,
                "result_limit_bytes": self.max_result_bytes,
            }

        try:
            return fit_page(matches, start=start, limit=10, render=render,
                            budget=self.max_result_bytes)[0]
        except ToolResultBudgetError as error:
            return budget_failure(tool_name="search_evidence", measured=error.measured, limit=error.limit)

    def read_chunk(self, chunk_id: str, source_version: str,
                   cursor: str | None = None) -> dict:
        chunk = self.catalog.get_chunk(chunk_id, source_version)
        spans = self._chunk_spans[chunk_id]
        scope = _hash([chunk_id, source_version, chunk["content_sha256"]])
        start = _offset(cursor, scope, len(spans))

        def render(page: list, count: int) -> dict:
            end = start + count
            return {
                "status": "ok", "source_id": chunk["source_id"],
                "source_version": source_version, "chunk_id": chunk_id,
                "section_type": chunk["section_type"], "section_title": chunk["section_title"],
                "content_sha256": chunk["content_sha256"],
                "source_start_offset": chunk["start_offset"],
                "source_end_offset": chunk["end_offset"],
                "offset_basis": "unicode_code_points_relative_to_chunk",
                "spans": page, "total_spans": len(spans),
                "next_cursor": _cursor(scope, end) if end < len(spans) else None,
                "complete": end >= len(spans), "result_limit_bytes": self.max_result_bytes,
            }

        try:
            result, _ = fit_page(spans, start=start, limit=len(spans), render=render,
                                 budget=self.max_result_bytes)
        except ToolResultBudgetError as error:
            return budget_failure(tool_name="read_chunk", measured=error.measured, limit=error.limit)
        return result

    def record_evidence(self, span_ids: list[str], source_version: str) -> list[dict]:
        if not isinstance(span_ids, list) or not span_ids or len(span_ids) > 32:
            raise ValueError("Supply between 1 and 32 returned span IDs")
        if any(not isinstance(span_id, str) for span_id in span_ids) or len(set(span_ids)) != len(span_ids):
            raise ValueError("Span IDs must be unique strings")
        result = []
        for span_id in span_ids:
            # The immutable catalog regenerates precisely the same IDs in a
            # fresh process. Membership proves this is a complete canonical
            # span that read_chunk can return, without an ephemeral issuance
            # ledger that would reject a retry after restart. AGR resolution
            # additionally checks exact chunk identity, offsets and text hash.
            if span_id not in self._span_lookup:
                raise ValueError("Select only canonical spans returned by read_chunk")
            parsed = parse_evidence_span_id(span_id)
            chunk = self.catalog.get_chunk(parsed.chunk_id, source_version)
            span = resolve_evidence_span_id(
                span_id=span_id, chunk_text=chunk["text"], expected_chunk_id=chunk["chunk_id"],
            ).to_dict()
            result.append(self._canonical_evidence(span, chunk))
        return result

    def evidence_detail(self, evidence_id: str) -> dict:
        if evidence_id not in self._evidence:
            raise ValueError("Unknown evidence identity")
        evidence = deepcopy(self._evidence[evidence_id])
        chunk = self.catalog.get_chunk(evidence["chunk_id"], evidence["source_version"])
        quote = chunk["text"][evidence["start_offset"]:evidence["end_offset"]]
        if sha256(quote.encode("utf-8")).hexdigest() != evidence["quote_sha256"]:
            raise ValueError("Canonical quote integrity mismatch")
        return {**evidence, "quote": quote, "source": self.catalog.get_source(evidence["source_id"]),
                "section_type": chunk["section_type"], "section_title": chunk["section_title"]}
