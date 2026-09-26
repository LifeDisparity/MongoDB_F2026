"""Model-proposed policy optimizer (LA-18).

One or at most two candidates are generated from development failure/cost
traces. Each candidate must (1) link to real development failure evidence,
(2) survive the immutable policy controls (LA-17) and the evaluator's patch
validation (LA-15), and (3) win the frozen selection rule
(:func:`evaluation.core.promotion_decision`) on the validation split. A winner
is promoted; otherwise every attempt is recorded as a rejection and the
baseline stands. Nothing here reads the final-test split or mutates budgets,
model or evaluator.

The proposer is injected: in production it wraps the LA-09 structured model
adapter; offline drivers pass a deterministic labelled proposer. The selection
logic is identical either way, so promotion/rejection is real regardless of how
the candidate text was produced.
"""
from __future__ import annotations

from collections.abc import Callable

from living_atlas.evaluation.core import promotion_decision, validate_policy_patch
from living_atlas.policies import PolicyViolation, propose_policy, verify_integrity

from .types import OptimizationContext, ProposedPatch

MAX_CANDIDATES = 2

Proposer = Callable[[OptimizationContext], ProposedPatch]
Evaluator = Callable[[dict], dict]


def build_candidate(
    baseline_policy: dict, patch: dict, *,
    addresses_failure_ids: list[str], proposed_by: str,
) -> dict:
    """Validate a raw patch and derive an immutable candidate policy version.

    Applies the evaluator's patch guard (LA-15) and the immutable policy
    controls (LA-17). Raises :class:`~living_atlas.policies.PolicyViolation`
    for a forbidden or empty change so it never enters selection.
    """
    try:
        validate_policy_patch(patch)
    except ValueError as error:
        raise PolicyViolation("invalid_patch", str(error), patch=patch) from error
    return propose_policy(
        baseline_policy, patch,
        proposed_by=proposed_by, development_failure_ids=addresses_failure_ids,
    )


def run_optimization(
    *,
    baseline_policy: dict,
    baseline_evaluation: dict,
    development_failure_ids: list[str],
    propose: Proposer,
    evaluate: Evaluator,
    max_candidates: int = MAX_CANDIDATES,
    proposed_by: str = "policy-optimizer",
) -> dict:
    """Generate, validate, evaluate and select at most ``max_candidates`` policies."""
    if not isinstance(max_candidates, int) or not 1 <= max_candidates <= MAX_CANDIDATES:
        raise ValueError(f"max_candidates must be between 1 and {MAX_CANDIDATES}")
    verify_integrity(baseline_policy)
    known = set(development_failure_ids)
    if not known:
        raise ValueError("development_failure_ids must be non-empty to link proposals to evidence")

    attempts: list[dict] = []
    promoted_version: str | None = None
    selected_policy = baseline_policy

    for attempt in range(1, max_candidates + 1):
        context = OptimizationContext(
            baseline_policy=baseline_policy, baseline_evaluation=baseline_evaluation,
            development_failure_ids=tuple(development_failure_ids), attempt=attempt,
            prior_outcomes=tuple(attempts),
        )
        proposal = propose(context)
        if not isinstance(proposal, ProposedPatch):
            raise TypeError("propose must return a ProposedPatch")

        addresses = [fid for fid in proposal.addresses_failure_ids if fid in known]
        if not addresses:
            attempts.append(_rejected(
                attempt, proposal, policy_version=None,
                reason="no_development_evidence_link",
                detail={"claimed": proposal.addresses_failure_ids,
                        "known": sorted(known)}))
            continue

        patch = proposal.to_patch_dict()
        try:
            candidate = build_candidate(
                baseline_policy, patch,
                addresses_failure_ids=addresses, proposed_by=proposed_by)
        except PolicyViolation as violation:
            attempts.append(_rejected(
                attempt, proposal, policy_version=None,
                reason=violation.code, detail=violation.details))
            continue

        candidate_evaluation = evaluate(candidate)
        decision = promotion_decision(baseline_evaluation, candidate_evaluation)
        outcome = {
            "attempt": attempt,
            "policy_version": candidate["policy_version"],
            "parent_policy_version": candidate["parent_policy_version"],
            "policy_sha256": candidate["configuration_sha256"],
            "patch": patch,
            "rationale": proposal.rationale,
            "addresses_failure_ids": addresses,
            "evaluation": candidate_evaluation,
            "promotion": decision,
            "selection_status": "promoted" if decision["promote"] else "rejected",
        }
        attempts.append(outcome)
        if decision["promote"]:
            promoted = dict(candidate)
            promoted["selection_status"] = "promoted"
            promoted["evaluation_id"] = candidate_evaluation.get("evaluation_id")
            promoted_version = candidate["policy_version"]
            selected_policy = promoted
            break

    return {
        "schema": "policy_optimization_v1",
        "baseline_policy_version": baseline_policy["policy_version"],
        "development_failure_ids": list(development_failure_ids),
        "max_candidates": max_candidates,
        "attempts_made": len(attempts),
        "promoted": promoted_version is not None,
        "selected_policy_version": selected_policy["policy_version"],
        "selected_policy": selected_policy,
        "attempts": attempts,
    }


def _rejected(attempt: int, proposal: ProposedPatch, *,
              policy_version: str | None, reason: str, detail: dict) -> dict:
    return {
        "attempt": attempt,
        "policy_version": policy_version,
        "patch": proposal.to_patch_dict(),
        "rationale": proposal.rationale,
        "addresses_failure_ids": proposal.addresses_failure_ids,
        "evaluation": None,
        "promotion": {"promote": False, "reasons": [reason], "detail": detail},
        "selection_status": "rejected",
    }


def optimization_events(result: dict) -> list[dict]:
    """Render an optimization result as ordered event payloads for LA-13.

    The repository assigns global sequences/operation IDs; these are payload
    bodies only (``policy.proposed`` for each attempt, then ``policy.promoted``
    or ``policy.rejected``).
    """
    events: list[dict] = []
    for outcome in result["attempts"]:
        events.append({
            "type": "policy.proposed",
            "payload": {
                "policy_version": outcome["policy_version"],
                "parent_policy_version": result["baseline_policy_version"],
                "patch": outcome["patch"],
                "rationale": outcome["rationale"],
                "addresses_failure_ids": outcome["addresses_failure_ids"],
                "attempt": outcome["attempt"],
            },
        })
        promoted = outcome["selection_status"] == "promoted"
        events.append({
            "type": "policy.promoted" if promoted else "policy.rejected",
            "payload": {
                "policy_version": outcome["policy_version"],
                "reasons": outcome["promotion"]["reasons"],
                "evaluation": outcome["evaluation"],
            },
        })
    return events
