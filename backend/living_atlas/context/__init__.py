"""Bounded context packets (LA-08).

Ranked-passage and experimental-context assembly under one identical fixed
budget, with explicit truncation and preserved direct original-evidence
references for durable investigation resumption.
"""

from .packets import (
    DEFAULT_PER_PASSAGE_OVERHEAD_TOKENS,
    EXPERIMENTAL_SECTIONS,
    MODES,
    PassageCandidate,
    build_context_packet,
    estimate_tokens,
    original_quote_matches,
    passage_candidates_from_records,
)

__all__ = [
    "DEFAULT_PER_PASSAGE_OVERHEAD_TOKENS",
    "EXPERIMENTAL_SECTIONS",
    "MODES",
    "PassageCandidate",
    "build_context_packet",
    "estimate_tokens",
    "original_quote_matches",
    "passage_candidates_from_records",
]
