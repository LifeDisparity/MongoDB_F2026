"""Structured proposal records for the policy optimizer (LA-18).

The model returns a :class:`ProposedPatch`: a change limited to the two
proposable policy sections plus a rationale and the development failure IDs it
claims to address. The schema itself cannot express a budget/model/evaluator
change, and the optimizer additionally re-validates every proposal against the
immutable controls (LA-17) before it can run.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ContextChange(_Strict):
    mode: Literal["ranked_passages", "experimental_context"]


class ReviewChange(_Strict):
    mode: Literal["on_conflict", "on_scope_ambiguity", "always"]
    retrieve_controls: bool


class ProposedPatch(_Strict):
    """A model-proposed policy change linked to development evidence."""

    rationale: str = Field(min_length=1, max_length=2000)
    addresses_failure_ids: list[str] = Field(default_factory=list)
    context_policy: ContextChange | None = None
    review_policy: ReviewChange | None = None

    def to_patch_dict(self) -> dict:
        """Render the change as a policy patch for validation and application."""
        patch: dict = {}
        if self.context_policy is not None:
            patch["context_policy"] = {"mode": self.context_policy.mode}
        if self.review_policy is not None:
            patch["review_policy"] = {
                "mode": self.review_policy.mode,
                "retrieve_controls": self.review_policy.retrieve_controls,
            }
        return patch


@dataclass(frozen=True)
class OptimizationContext:
    """Inputs handed to a proposer for one candidate attempt."""

    baseline_policy: dict
    baseline_evaluation: dict
    development_failure_ids: tuple[str, ...]
    attempt: int
    prior_outcomes: tuple[dict, ...] = field(default_factory=tuple)
