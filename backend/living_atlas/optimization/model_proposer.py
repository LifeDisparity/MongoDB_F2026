"""Production proposer backed by the LA-09 structured model adapter.

Kept separate from the optimizer core so importing the optimizer never pulls in
the provider SDK. Given development failure/cost traces it asks the one
configured model for a :class:`ProposedPatch`. When no model is configured it
raises :class:`ProposerUnavailable` rather than fabricating a proposal, so the
optimizer records an honest blocker instead of a fake candidate.
"""
from __future__ import annotations

import asyncio
import json

from living_atlas.models import StructuredModelAdapter, StructuredRequest

from .types import OptimizationContext, ProposedPatch

INSTRUCTIONS = (
    "You tune how future investigations assemble context and route scope review. "
    "You may only change context_policy.mode and review_policy (mode, retrieve_controls). "
    "You cannot change budgets, the model or the evaluator. Propose one change that "
    "addresses the listed development failures, cite their IDs in addresses_failure_ids, "
    "and explain the rationale. Return only the structured schema."
)


class ProposerUnavailable(RuntimeError):
    """No configured model is available to generate a real proposal."""

    def __init__(self, status: dict) -> None:
        self.status = status
        super().__init__(status.get("error_code", "model_unavailable"))


def _input_text(context: OptimizationContext) -> str:
    return json.dumps({
        "baseline_policy": {
            "policy_version": context.baseline_policy["policy_version"],
            "configuration": context.baseline_policy["configuration"],
        },
        "baseline_evaluation": context.baseline_evaluation,
        "development_failure_ids": list(context.development_failure_ids),
        "attempt": context.attempt,
        "prior_rejected": [
            {"policy_version": o.get("policy_version"),
             "reasons": o.get("promotion", {}).get("reasons", [])}
            for o in context.prior_outcomes
        ],
    }, sort_keys=True, ensure_ascii=False)


class ModelPolicyProposer:
    """Callable proposer wrapping :class:`StructuredModelAdapter`."""

    def __init__(self, adapter: StructuredModelAdapter):
        self._adapter = adapter

    async def apropose(self, context: OptimizationContext) -> ProposedPatch:
        if not self._adapter.available:
            raise ProposerUnavailable(self._adapter.status())
        request = StructuredRequest(
            request_id=f"optimization-attempt-{context.attempt}",
            instructions=INSTRUCTIONS, input_text=_input_text(context),
            purpose="optimization",
        )
        result = await self._adapter.generate(
            request, ProposedPatch, self._adapter.new_budget())
        if result.status != "completed" or result.output is None:
            raise ProposerUnavailable({
                "error_code": (result.failure.code if result.failure else result.status),
                "status": result.status,
            })
        return result.output

    def __call__(self, context: OptimizationContext) -> ProposedPatch:
        """Synchronous entry for non-async callers (raises inside a running loop)."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.apropose(context))
        raise RuntimeError(
            "ModelPolicyProposer.__call__ cannot run inside an active event loop; "
            "await apropose(context) from async workflow code instead.")
