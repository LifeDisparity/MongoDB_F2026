#!/usr/bin/env python3
"""E2E driver for LA-18 (model-proposed policy optimizer).

Exercises the complete optimizer flow: an evidence-linked candidate is proposed,
validated against the immutable policy controls (LA-17) and the evaluator patch
guard (LA-15), evaluated on the validation split, and selected by the frozen
rule (LA-15 promotion_decision) into a persisted promotion or rejection.

The proposer here is a deterministic labelled stub, so this is an *engineering*
acceptance, not the canonical real-model run (E2E-2). The selection logic,
immutable controls, evidence-linking, candidate cap and event shaping are
exercised for real. The real-model path is verified separately: the LA-09
adapter reports 'unavailable' without credentials, which the optimizer records
as an honest blocker (checked below).

Run:
    PYTHONPATH=backend python e2e/optimizer_e2e.py
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

from living_atlas.optimization import (
    MAX_CANDIDATES,
    ContextChange,
    ProposedPatch,
    ReviewChange,
    build_candidate,
    optimization_events,
    run_optimization,
)
from living_atlas.policies import PolicyViolation, default_policy

try:  # The model-backed proposer needs the optional provider SDK (LA-09).
    from living_atlas.optimization.model_proposer import ModelPolicyProposer, ProposerUnavailable
    _MODEL_PROPOSER_IMPORT_ERROR = None
except ImportError as error:  # openai not installed in this environment
    ModelPolicyProposer = ProposerUnavailable = None  # type: ignore[assignment]
    _MODEL_PROPOSER_IMPORT_ERROR = str(error)

FAILURE_IDS = ["fail-scope-ambiguity-1", "fail-context-recall-2"]


def _eval(policy_hash: str, *, correct: int, cost: float) -> dict:
    """A validation-split evaluation record in the shape promotion_decision needs."""
    return {
        "manifest_hash": "manifest-fixed", "model": "configured-model",
        "policy_hash": policy_hash, "split": "validation",
        "case_ids": [f"case-{i}" for i in range(10)],
        "budget": {"context_tokens": 1200, "max_passages": 8},
        "finalized": True, "budget_ok": True, "integrity_ok": True,
        "total_cost": cost, "correct_count": correct, "decision_count": 10,
        "supported_count": 5, "support_count": 6,
        "reference_hits": 4, "reference_count": 8,
        "evaluation_id": f"eval-{policy_hash[:8]}-{correct}-{int(cost)}",
    }


def _check(results: list[dict], name: str, passed: bool, detail: object = "") -> bool:
    results.append({"check": name, "passed": bool(passed), "detail": detail})
    print(f"  [{'PASS' if passed else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    return passed


def _proposer(patches):
    """Deterministic proposer that yields the given ProposedPatch per attempt."""
    def propose(context):
        return patches[min(context.attempt - 1, len(patches) - 1)]
    return propose


def main() -> int:
    started = time.time()
    results: list[dict] = []
    baseline = default_policy(proposed_by="e2e-bootstrap")
    baseline_eval = _eval(baseline["configuration_sha256"], correct=6, cost=100.0)
    print("LA-18 policy optimizer engineering E2E (deterministic labelled proposer; not E2E-2)\n")

    print("Promotion path: evidence-linked candidate that improves correctness")
    improving = ProposedPatch(
        rationale="Scope-ambiguous cases need experimental_context + scope review.",
        addresses_failure_ids=["fail-scope-ambiguity-1"],
        context_policy=ContextChange(mode="experimental_context"),
        review_policy=ReviewChange(mode="on_scope_ambiguity", retrieve_controls=True))
    promoted = run_optimization(
        baseline_policy=baseline, baseline_evaluation=baseline_eval,
        development_failure_ids=FAILURE_IDS, propose=_proposer([improving]),
        evaluate=lambda cand: _eval(cand["configuration_sha256"], correct=8, cost=100.0))
    _check(results, "candidate is promoted and becomes the selected policy",
           promoted["promoted"] and promoted["selected_policy_version"] == promoted["attempts"][0]["policy_version"])
    _check(results, "promoted candidate links to its parent and development evidence",
           promoted["attempts"][0]["parent_policy_version"] == baseline["policy_version"]
           and promoted["attempts"][0]["addresses_failure_ids"] == ["fail-scope-ambiguity-1"])
    events = optimization_events(promoted)
    _check(results, "events record policy.proposed then policy.promoted",
           [e["type"] for e in events] == ["policy.proposed", "policy.promoted"])

    print("\nRejection path: two candidates with no gain, baseline stands")
    no_gain = [
        ProposedPatch(rationale="Try experimental_context.",
                      addresses_failure_ids=["fail-context-recall-2"],
                      context_policy=ContextChange(mode="experimental_context")),
        ProposedPatch(rationale="Try always-review.",
                      addresses_failure_ids=["fail-context-recall-2"],
                      review_policy=ReviewChange(mode="always", retrieve_controls=False)),
    ]
    rejected = run_optimization(
        baseline_policy=baseline, baseline_evaluation=baseline_eval,
        development_failure_ids=FAILURE_IDS, propose=_proposer(no_gain),
        evaluate=lambda cand: _eval(cand["configuration_sha256"], correct=6, cost=100.0))
    _check(results, "no candidate is promoted and baseline is retained",
           not rejected["promoted"] and rejected["selected_policy_version"] == baseline["policy_version"])
    _check(results, "at most two candidates are attempted",
           rejected["attempts_made"] == MAX_CANDIDATES
           and all(a["selection_status"] == "rejected" for a in rejected["attempts"]))

    print("\nEvidence-linking is enforced")
    unlinked = ProposedPatch(rationale="Unrelated change.",
                             addresses_failure_ids=["not-a-real-failure"],
                             context_policy=ContextChange(mode="experimental_context"))
    unlinked_result = run_optimization(
        baseline_policy=baseline, baseline_evaluation=baseline_eval,
        development_failure_ids=FAILURE_IDS, propose=_proposer([unlinked]), max_candidates=1,
        evaluate=lambda cand: _eval(cand["configuration_sha256"], correct=9, cost=1.0))
    _check(results, "a proposal with no real failure link is rejected before evaluation",
           not unlinked_result["promoted"]
           and unlinked_result["attempts"][0]["promotion"]["reasons"] == ["no_development_evidence_link"])

    print("\nImmutable controls guard the optimizer (raw forbidden patches reject)")
    for name, patch in {
        "budget": {"budget": {"context_tokens": 999999}},
        "model": {"model": {"model_id": "smuggled"}},
        "unknown": {"context_policy": {"boost": True}},
    }.items():
        try:
            build_candidate(baseline, patch, addresses_failure_ids=FAILURE_IDS, proposed_by="e2e")
            _check(results, f"forbidden {name} patch rejected in optimizer", False, "ACCEPTED (bug)")
        except PolicyViolation as violation:
            _check(results, f"forbidden {name} patch rejected in optimizer", True, violation.code)

    print("\nCandidate cap is enforced")
    try:
        run_optimization(
            baseline_policy=baseline, baseline_evaluation=baseline_eval,
            development_failure_ids=FAILURE_IDS, propose=_proposer([improving]),
            evaluate=lambda cand: baseline_eval, max_candidates=3)
        _check(results, "max_candidates > 2 is rejected", False, "ACCEPTED (bug)")
    except ValueError:
        _check(results, "max_candidates > 2 is rejected", True)

    model_proposer_status = "checked"
    if _MODEL_PROPOSER_IMPORT_ERROR is not None:
        model_proposer_status = f"skipped (optional provider SDK missing: {_MODEL_PROPOSER_IMPORT_ERROR})"
        print(f"\nReal-model proposer check {model_proposer_status}")
    else:
        print("\nReal-model proposer is honest when no model is configured")
        adapter = __import__("living_atlas.models", fromlist=["StructuredModelAdapter"]).StructuredModelAdapter
        proposer = ModelPolicyProposer(adapter.from_env({}))  # no OPENAI_API_KEY / MODEL_ID
        from living_atlas.optimization.types import OptimizationContext
        try:
            proposer(OptimizationContext(baseline, baseline_eval, tuple(FAILURE_IDS), 1))
            _check(results, "unconfigured model proposer refuses to fabricate", False, "returned a patch (bug)")
        except ProposerUnavailable as unavailable:
            _check(results, "unconfigured model proposer refuses to fabricate", True,
                   unavailable.status.get("error_code"))

    passed = all(row["passed"] for row in results)
    manifest = {
        "artifact": "la-18-e2e",
        "labelled": "deterministic engineering proposer; not the canonical real-model run (E2E-2)",
        "ticket": "LA-18",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "duration_seconds": round(time.time() - started, 3),
        "baseline_policy_version": baseline["policy_version"],
        "promoted_policy_version": promoted["selected_policy_version"],
        "promoted_events": [e["type"] for e in events],
        "rejection_attempts": rejected["attempts_made"],
        "model_proposer_check": model_proposer_status,
        "checks": results,
        "result": "pass" if passed else "fail",
    }
    out = Path(__file__).resolve().parent.parent / "artifacts/manifests/la-18-e2e.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\n{'PASS' if passed else 'FAIL'}: {sum(r['passed'] for r in results)}/{len(results)} checks")
    print(f"Artifact: {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
