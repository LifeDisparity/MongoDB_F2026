#!/usr/bin/env python3
"""E2E driver for LA-08 (bounded context packets) and LA-17 (policy controls).

This exercises the complete relevant application flow for these two lanes:
a content-addressed policy selects a context-assembly mode and a frozen budget,
the context builder assembles a bounded packet from real source-backed records,
and a fresh worker resumes from that packet and retrieves the exact original
passage. It then runs the actual proposal flow: allowed context/review changes
execute and produce a new linked version, while forbidden budget/model/evaluator
changes reject.

It uses the explicitly labelled synthetic engineering fixture (never a
scientific measurement) so it runs offline without a model or Atlas. Full
browser -> API -> workflow -> Atlas integration remains LA-10/LA-14/LA-18.

Run:
    PYTHONPATH=backend python e2e/context_policy_e2e.py
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

from living_atlas.api.fixtures import availability_fixture
from living_atlas.context import (
    PassageCandidate,
    build_context_packet,
    original_quote_matches,
    passage_candidates_from_records,
)
from living_atlas.policies import (
    PolicyViolation,
    default_policy,
    propose_policy,
    resolve_context_settings,
    verify_integrity,
)

QUESTION = "Which synthetic sources support engineering claim B and its scope?"
GENE_ID = "fixture-gene-1"


def _check(results: list[dict], name: str, passed: bool, detail: object = "") -> bool:
    results.append({"check": name, "passed": bool(passed), "detail": detail})
    print(f"  [{'PASS' if passed else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    return passed


def main() -> int:
    started = time.time()
    results: list[dict] = []
    fixture = availability_fixture("run-la08-la17-e2e")
    chunk_text = {c["chunk_id"]: c["text"] for c in fixture["chunks"]}
    candidates = passage_candidates_from_records(
        fixture["chunks"], fixture["evidence"], fixture["claims"],
    )

    print("LA-08 / LA-17 engineering E2E (labelled synthetic fixture; not scientific)\n")

    print("Policy (LA-17): baseline H0")
    baseline = default_policy(proposed_by="e2e-bootstrap")
    verify_integrity(baseline)
    settings = resolve_context_settings(baseline)
    _check(results, "baseline policy is content-addressed and mode is ranked_passages",
           settings["mode"] == "ranked_passages"
           and baseline["policy_version"] == "pol_" + baseline["configuration_sha256"][:16])

    print("\nContext packet (LA-08): ranked_passages under the policy budget")
    ranked = build_context_packet(
        mode=settings["mode"], question=QUESTION, gene_id=GENE_ID,
        candidates=candidates, token_budget=settings["token_budget"],
        per_passage_overhead_tokens=settings["per_passage_overhead_tokens"],
        max_passages=settings["max_passages"],
    )
    print(f"  budget={ranked['token_budget']} tokens  used={ranked['tokens_used']}  "
          f"included={ranked['included_count']}  omitted={ranked['omitted_count']}  "
          f"truncated={ranked['truncated']}")
    _check(results, "packet stays within its token budget",
           ranked["tokens_used"] <= ranked["token_budget"])
    _check(results, "every included passage keeps a direct original reference",
           all("retrieve_via" in p and p["retrieve_via"]["quote_sha256"] for p in ranked["passages"]))

    print("\nResume: retrieve the exact original passage from a bounded reference")
    top = ranked["passages"][0]
    ref = top["retrieve_via"]
    retrievable = original_quote_matches(ref, chunk_text[ref["chunk_id"]])
    _check(results, "original passage is retrievable and hash-exact after resume", retrievable,
           detail=f"{ref['evidence_id']} sha256={ref['quote_sha256'][:12]}...")

    print("\nBudget/truncation is visible under a deliberately tiny budget")
    tiny = build_context_packet(
        mode="ranked_passages", question=QUESTION, gene_id=GENE_ID,
        candidates=candidates, token_budget=20, per_passage_overhead_tokens=4,
    )
    tiny_visible = tiny["truncated"] and tiny["omitted_count"] > 0 and all(
        "retrieve_via" in o for o in tiny["omitted"])
    _check(results, "tiny budget truncates and every omitted passage stays retrievable",
           tiny_visible,
           detail=f"included={tiny['included_count']} omitted={tiny['omitted_count']}")

    print("\nPolicy proposal (LA-17): ALLOWED context/review change executes")
    allowed = propose_policy(
        baseline,
        {"context_policy": {"mode": "experimental_context"},
         "review_policy": {"mode": "on_scope_ambiguity", "retrieve_controls": True}},
        proposed_by="e2e-optimizer", development_failure_ids=["fail-scope-ambiguity-1"],
    )
    verify_integrity(allowed)
    linked = (allowed["parent_policy_version"] == baseline["policy_version"]
              and allowed["policy_version"] != baseline["policy_version"]
              and allowed["selection_status"] == "proposed")
    _check(results, "allowed proposal yields a new version linked to its parent", linked,
           detail=f"{baseline['policy_version']} -> {allowed['policy_version']}")

    print("\nThe accepted change actually reroutes context assembly (labelled synthetic)")
    # A minimal synthetic set where experimental signal and relevance disagree:
    # ex_intro is highly relevant framing (INTRODUCTION); ex_result carries a
    # scoped experimental observation. ranked_passages leads with relevance,
    # experimental_context leads with the scoped observation.
    routing_candidates = [
        PassageCandidate(
            evidence_id="ex_intro", source_id="S1", source_version="v",
            chunk_id="S1:chunk:0", span_id="s:intro", start_offset=0, end_offset=1,
            quote="scope scope scope claim B framing overview introduction",
            quote_sha256="0" * 64, section_type="introduction", section_title="Intro",
            qualifiers={"polarity": "observed", "scope_notes": ""}),
        PassageCandidate(
            evidence_id="ex_result", source_id="S2", source_version="v",
            chunk_id="S2:chunk:0", span_id="s:result", start_offset=0, end_offset=1,
            quote="claim B under RNAi in the mushroom body was not observed at stage L3",
            quote_sha256="1" * 64, section_type="results", section_title="Results",
            qualifiers={"polarity": "not_observed", "intervention": "RNAi",
                        "cell_class": "mushroom body", "stage_label": "L3",
                        "scope_notes": "scoped negative observation"}),
    ]
    ranked_route = build_context_packet(
        mode="ranked_passages", question=QUESTION, gene_id=GENE_ID,
        candidates=routing_candidates, token_budget=settings["token_budget"])
    experimental_route = build_context_packet(
        mode=resolve_context_settings(allowed)["mode"], question=QUESTION, gene_id=GENE_ID,
        candidates=routing_candidates, token_budget=settings["token_budget"])
    ranked_lead = ranked_route["passages"][0]["evidence_id"]
    experimental_lead = experimental_route["passages"][0]["evidence_id"]
    same_budget = experimental_route["token_budget"] == ranked_route["token_budget"]
    _check(results,
           "the two modes lead with different passages under the identical budget",
           same_budget and ranked_lead != experimental_lead,
           detail=f"ranked->{ranked_lead}, experimental->{experimental_lead}, "
                  f"identical budget={same_budget}")

    # Keep the fixture-driven experimental packet for the artifact summary.
    experimental = build_context_packet(
        mode=resolve_context_settings(allowed)["mode"], question=QUESTION, gene_id=GENE_ID,
        candidates=candidates, token_budget=settings["token_budget"],
        per_passage_overhead_tokens=settings["per_passage_overhead_tokens"])

    print("\nPolicy proposal (LA-17): FORBIDDEN changes reject")
    forbidden_cases = {
        "budget": {"budget": {"context_tokens": 100000}},
        "model": {"model": {"model_id": "smuggled-model"}},
        "evaluator": {"evaluator": {"evaluator_id": "self-graded"}},
        "unknown_field": {"context_policy": {"secret_boost": True}},
    }
    for name, patch in forbidden_cases.items():
        try:
            propose_policy(baseline, patch, proposed_by="e2e-attacker")
            _check(results, f"forbidden {name} change is rejected", False, detail="ACCEPTED (bug)")
        except PolicyViolation as violation:
            _check(results, f"forbidden {name} change is rejected", True,
                   detail=f"{violation.code}")

    print("\nImmutable version integrity is enforced")
    tampered = json.loads(json.dumps(allowed))
    tampered["configuration"]["review_policy"]["retrieve_controls"] = False
    try:
        verify_integrity(tampered)
        _check(results, "tampered version is detected", False, detail="undetected (bug)")
    except PolicyViolation as violation:
        _check(results, "tampered version is detected", True, detail=violation.code)

    passed = all(row["passed"] for row in results)
    manifest = {
        "artifact": "la-08-la-17-e2e",
        "labelled": "synthetic engineering fixture; not a scientific or model measurement",
        "run_id": "run-la08-la17-e2e",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "duration_seconds": round(time.time() - started, 3),
        "tickets": ["LA-08", "LA-17"],
        "baseline_policy_version": baseline["policy_version"],
        "proposed_policy_version": allowed["policy_version"],
        "ranked_packet": {k: ranked[k] for k in (
            "mode", "token_budget", "tokens_used", "included_count", "omitted_count", "truncated")},
        "experimental_packet": {k: experimental[k] for k in (
            "mode", "token_budget", "tokens_used", "included_count", "omitted_count", "truncated")},
        "checks": results,
        "result": "pass" if passed else "fail",
    }
    out = Path(__file__).resolve().parent.parent / "artifacts/manifests/la-08-la-17-e2e.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"\n{'PASS' if passed else 'FAIL'}: {sum(r['passed'] for r in results)}/{len(results)} checks")
    print(f"Artifact: {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
