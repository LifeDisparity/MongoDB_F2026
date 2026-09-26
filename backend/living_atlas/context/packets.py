"""Bounded context packets for durable investigation resumption (LA-08).

A fresh worker cannot inherit an unbounded transcript. It receives a *packet*:
an ordered, byte/token-bounded selection of source-backed passages assembled
under a fixed budget. Two assembly modes rank the same candidates differently
but share one identical budget, so a policy change (LA-17) alters *what a
worker attends to*, never *how much* it may consume.

Nothing here fabricates evidence. Every passage keeps its direct original
references (source version, chunk, span, offsets, quote hash) so the exact
original passage is retrievable after resume via ``read_chunk`` /
``evidence_detail``. Truncation is always explicit: a trimmed passage records
the retained/total character counts and a ``retrieve_via`` reference, and any
passage that does not fit is listed under ``omitted`` with a reason.

This module is pure (standard library only) so it can run inside the workflow
lane, in offline drivers and in replay without pulling model or database
dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re

MODES = ("ranked_passages", "experimental_context")

# Sections that carry primary experimental observations rather than framing.
EXPERIMENTAL_SECTIONS = {
    "results", "methods", "materials_and_methods", "results_and_discussion",
}
# Qualifier keys whose presence marks an observation as experimentally scoped.
_QUALIFIER_KEYS = ("intervention", "assay", "stage_id", "stage_label", "cell_class")

# A small fixed accounting cost per included passage covering its reference
# metadata (identifiers, offsets, hashes) that a worker must also hold.
DEFAULT_PER_PASSAGE_OVERHEAD_TOKENS = 16
# Below this many content tokens a trimmed prefix is not worth including.
_MIN_TRIM_CONTENT_TOKENS = 4


def estimate_tokens(text: str) -> int:
    """Deterministic token estimate shared across modes and budgets.

    This is a stable heuristic (~4 characters per token), not a model
    tokenizer. It is used only to compare candidates and enforce one identical
    budget; both assembly modes call exactly this function.
    """
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


@dataclass(frozen=True)
class PassageCandidate:
    """One source-backed passage eligible for a context packet.

    ``quote`` is the exact canonical text of the span; it is never rewritten.
    Trimming for budget produces a prefix slice and always keeps the reference
    fields so the full original remains retrievable.
    """

    evidence_id: str
    source_id: str
    source_version: str
    chunk_id: str
    span_id: str
    start_offset: int
    end_offset: int
    quote: str
    quote_sha256: str
    section_type: str = ""
    section_title: str = ""
    qualifiers: dict | None = None


def passage_candidates_from_records(
    chunks: list[dict], evidence: list[dict], claims: list[dict] | None = None,
) -> list[PassageCandidate]:
    """Build candidates from snapshot-shaped records.

    ``chunks`` supply exact text and section metadata; ``evidence`` supplies the
    canonical span references; ``claims`` (optional) attach experimental
    qualifiers to the evidence they cite. No model text is introduced.
    """
    chunk_by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    qualifiers_by_evidence: dict[str, dict] = {}
    for claim in claims or []:
        for evidence_id in claim.get("evidence_ids", []):
            # First citing claim wins; qualifiers are descriptive, not merged.
            qualifiers_by_evidence.setdefault(evidence_id, claim.get("qualifiers") or {})
    candidates: list[PassageCandidate] = []
    for record in evidence:
        chunk = chunk_by_id.get(record["chunk_id"])
        if chunk is None:
            continue
        quote = chunk["text"][record["start_offset"]:record["end_offset"]]
        candidates.append(PassageCandidate(
            evidence_id=record["evidence_id"], source_id=record["source_id"],
            source_version=record["source_version"], chunk_id=record["chunk_id"],
            span_id=record["span_id"], start_offset=record["start_offset"],
            end_offset=record["end_offset"], quote=quote,
            quote_sha256=record["quote_sha256"],
            section_type=chunk.get("section_type", ""),
            section_title=chunk.get("section_title", ""),
            qualifiers=qualifiers_by_evidence.get(record["evidence_id"]),
        ))
    return candidates


def _relevance(question: str, text: str) -> int:
    terms = set(re.findall(r"[\w-]+", question.casefold()))
    if not terms:
        return 0
    return len(terms & set(re.findall(r"[\w-]+", text.casefold())))


def _experimental_signal(candidate: PassageCandidate) -> int:
    score = 0
    qualifiers = candidate.qualifiers or {}
    for key in _QUALIFIER_KEYS:
        if qualifiers.get(key):
            score += 2
    # Scoped negative or uncertain observations must not be dropped silently;
    # they are the ones a scope-review policy most needs to see.
    if qualifiers.get("polarity") in ("not_observed", "uncertain"):
        score += 2
    if (candidate.section_type or "").lower() in EXPERIMENTAL_SECTIONS:
        score += 1
    return score


def _order(mode: str, question: str, candidates: list[PassageCandidate]) -> list[PassageCandidate]:
    if mode == "ranked_passages":
        key = lambda c: (-_relevance(question, c.quote), c.evidence_id)
    elif mode == "experimental_context":
        key = lambda c: (-_experimental_signal(c), -_relevance(question, c.quote), c.evidence_id)
    else:
        raise ValueError(f"Unknown context mode: {mode!r}; expected one of {MODES}")
    return sorted(candidates, key=key)


def _reference(candidate: PassageCandidate) -> dict:
    """A direct, hash-addressed handle to the exact original passage."""
    return {
        "tool": "read_chunk",
        "evidence_id": candidate.evidence_id,
        "source_id": candidate.source_id,
        "source_version": candidate.source_version,
        "chunk_id": candidate.chunk_id,
        "span_id": candidate.span_id,
        "start_offset": candidate.start_offset,
        "end_offset": candidate.end_offset,
        "quote_sha256": candidate.quote_sha256,
    }


def build_context_packet(
    *,
    mode: str,
    question: str,
    gene_id: str | None,
    candidates: list[PassageCandidate],
    token_budget: int,
    per_passage_overhead_tokens: int = DEFAULT_PER_PASSAGE_OVERHEAD_TOKENS,
    max_passages: int | None = None,
) -> dict:
    """Assemble a bounded, JSON-serializable context packet.

    Passages are taken in ``mode`` order and included whole while the shared
    ``token_budget`` allows. The first passage that does not fit whole is
    included as an exact prefix (marked truncated) if a useful remainder fits;
    once the budget is spent, remaining passages are listed under ``omitted``.
    Every included passage keeps ``retrieve_via`` so the full original is
    retrievable after resume.
    """
    if mode not in MODES:
        raise ValueError(f"Unknown context mode: {mode!r}; expected one of {MODES}")
    if not isinstance(token_budget, int) or token_budget <= 0:
        raise ValueError("token_budget must be a positive integer")
    if per_passage_overhead_tokens < 0:
        raise ValueError("per_passage_overhead_tokens must be non-negative")

    ordered = _order(mode, question, candidates)
    if max_passages is not None:
        if not isinstance(max_passages, int) or max_passages <= 0:
            raise ValueError("max_passages must be a positive integer when provided")

    remaining = token_budget
    passages: list[dict] = []
    omitted: list[dict] = []
    budget_spent = False

    for rank, candidate in enumerate(ordered, start=1):
        content_tokens = estimate_tokens(candidate.quote)
        full_cost = per_passage_overhead_tokens + content_tokens
        reached_limit = max_passages is not None and len(passages) >= max_passages

        if budget_spent or reached_limit:
            omitted.append({
                "evidence_id": candidate.evidence_id,
                "section_type": candidate.section_type,
                "estimated_tokens": full_cost,
                "reason": "passage_limit_reached" if reached_limit else "budget_exhausted",
                "retrieve_via": _reference(candidate),
            })
            continue

        if full_cost <= remaining:
            passages.append(_included_passage(
                rank, candidate, content_chars=len(candidate.quote),
                estimated_tokens=full_cost, truncated=False,
            ))
            remaining -= full_cost
            continue

        content_budget = remaining - per_passage_overhead_tokens
        if content_budget >= _MIN_TRIM_CONTENT_TOKENS:
            kept_chars = _fit_chars(candidate.quote, content_budget)
            if kept_chars > 0:
                passages.append(_included_passage(
                    rank, candidate, content_chars=kept_chars,
                    estimated_tokens=per_passage_overhead_tokens + estimate_tokens(
                        candidate.quote[:kept_chars]),
                    truncated=True,
                ))
                remaining = token_budget - sum(p["estimated_tokens"] for p in passages)
                budget_spent = True
                continue
        omitted.append({
            "evidence_id": candidate.evidence_id,
            "section_type": candidate.section_type,
            "estimated_tokens": full_cost,
            "reason": "budget_exhausted",
            "retrieve_via": _reference(candidate),
        })
        budget_spent = True

    tokens_used = token_budget - remaining
    return {
        "schema": "context_packet_v1",
        "mode": mode,
        "gene_id": gene_id,
        "question": question,
        "token_budget": token_budget,
        "tokens_used": tokens_used,
        "tokens_remaining": remaining,
        "per_passage_overhead_tokens": per_passage_overhead_tokens,
        "candidate_count": len(ordered),
        "included_count": len(passages),
        "omitted_count": len(omitted),
        "truncated": bool(omitted) or any(p["truncated"] for p in passages),
        "passages": passages,
        "omitted": omitted,
        "resume": {
            "reconstructable": True,
            "note": (
                "Bounded resume context. Each passage retains retrieve_via for the "
                "exact original; omitted passages remain retrievable by the same handle."
            ),
        },
    }


def _fit_chars(text: str, content_token_budget: int) -> int:
    """Largest prefix length whose estimated tokens fit ``content_token_budget``."""
    if content_token_budget <= 0:
        return 0
    # estimate_tokens(prefix) = ceil(len/4); invert with a safe upper bound then
    # trim so the estimate is guaranteed within budget.
    kept = min(len(text), content_token_budget * 4)
    while kept > 0 and estimate_tokens(text[:kept]) > content_token_budget:
        kept -= 1
    return kept


def _included_passage(
    rank: int, candidate: PassageCandidate, *,
    content_chars: int, estimated_tokens: int, truncated: bool,
) -> dict:
    quote = candidate.quote[:content_chars]
    return {
        "rank": rank,
        "evidence_id": candidate.evidence_id,
        "source_id": candidate.source_id,
        "source_version": candidate.source_version,
        "chunk_id": candidate.chunk_id,
        "span_id": candidate.span_id,
        "start_offset": candidate.start_offset,
        "end_offset": candidate.end_offset,
        "quote_sha256": candidate.quote_sha256,
        "section_type": candidate.section_type,
        "section_title": candidate.section_title,
        "qualifiers": candidate.qualifiers,
        "quote": quote,
        "retained_chars": content_chars,
        "total_chars": len(candidate.quote),
        "truncated": truncated,
        "estimated_tokens": estimated_tokens,
        "retrieve_via": _reference(candidate),
    }


def original_quote_matches(candidate_or_reference: dict, chunk_text: str) -> bool:
    """Confirm a packet reference still resolves to its exact original passage.

    Used on resume/replay to prove the bounded packet did not lose fidelity:
    the chunk slice at the recorded offsets must hash to the recorded
    ``quote_sha256``.
    """
    start = candidate_or_reference["start_offset"]
    end = candidate_or_reference["end_offset"]
    quote = chunk_text[start:end]
    return sha256(quote.encode("utf-8")).hexdigest() == candidate_or_reference["quote_sha256"]
