"""Independent local-pilot evaluation. Not FlyAOC semantic scoring."""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import json
import math
from collections.abc import Mapping

METRIC_NAME = "pilot_exact_anatomy_recall_at_10"

def _ids(values, label):
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{label} must be a list")
    result = list(values)
    if any(not isinstance(v, str) or not v.strip() for v in result):
        raise ValueError(f"invalid {label}")
    if len(result) != len(set(result)):
        raise ValueError(f"duplicate {label}")
    return result

def _anatomy(value):
    return (
        isinstance(value, str)
        and value.startswith("FBbt:")
        and value[5:].isdigit()
    )

def normalize_prediction_rows(scheduled_gene_ids, rows):
    scheduled = _ids(scheduled_gene_ids, "scheduled genes")
    allowed = set(scheduled)
    found = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("row must be an object")
        gene = row.get("gene_id")
        if not isinstance(gene, str) or gene not in allowed or gene in found:
            raise ValueError("unknown or duplicate gene")
        status = row.get("run_status", "ok")
        if not isinstance(status, str) or status not in {
            "ok", "failed", "empty_output", "missing"
        }:
            raise ValueError("unknown run status")
        normalized = {
            "gene_id": gene, "run_status": status,
            "task2_expression_predictions": [],
        }
        if status == "ok":
            predictions = row.get("task2_expression_predictions", [])
            if not isinstance(predictions, list) or any(
                not isinstance(item, Mapping) or not _anatomy(item.get("anatomy_id"))
                for item in predictions
            ):
                normalized["run_status"] = "failed"
                normalized["validation_error"] = "malformed anatomy predictions"
            else:
                normalized["task2_expression_predictions"] = [
                    {"anatomy_id": item["anatomy_id"]} for item in predictions
                ]
                if not predictions:
                    normalized["run_status"] = "empty_output"
        found[gene] = normalized
    return [
        found.get(gene, {
            "gene_id": gene, "run_status": "missing",
            "task2_expression_predictions": [],
        })
        for gene in scheduled
    ]

def anatomy_recall_at_10(scheduled_gene_ids, rows, reference_by_gene):
    normalized = normalize_prediction_rows(scheduled_gene_ids, rows)
    if set(reference_by_gene) != {row["gene_id"] for row in normalized}:
        raise ValueError("reference genes must exactly match manifest")
    output = []
    hits_total = count_total = 0
    for row in normalized:
        gene = row["gene_id"]
        references = _ids(reference_by_gene[gene], "anatomy references")
        if any(not _anatomy(value) for value in references):
            raise ValueError("invalid reference anatomy")
        ranked = list(dict.fromkeys(
            item["anatomy_id"] for item in row["task2_expression_predictions"]
        ))[:10]
        hits = len(set(ranked).intersection(references))
        count = len(references)
        hits_total += hits
        count_total += count
        output.append({
            "gene_id": gene, "run_status": row["run_status"],
            "hits": hits, "reference_count": count,
            "recall": hits / count if count else None,
        })
    return {
        "metric": METRIC_NAME, "k": 10, "hits": hits_total,
        "reference_count": count_total,
        "recall": hits_total / count_total if count_total else None,
        "genes": output,
    }

def decision_accuracy(expected, observed):
    if not expected:
        raise ValueError("empty decision manifest")
    _ids(list(expected), "decision IDs")
    if any(not isinstance(value, str) or not value for value in expected.values()):
        raise ValueError("expected labels must be nonempty strings")
    if set(observed) - set(expected):
        raise ValueError("unknown observed decisions")
    correct = sum(observed.get(key) == value for key, value in expected.items())
    return {
        "correct_count": correct, "decision_count": len(expected),
        "accuracy": correct / len(expected),
        "missing_case_ids": sorted(set(expected) - set(observed)),
    }

def validate_policy_patch(patch):
    if not isinstance(patch, Mapping) or not patch:
        raise ValueError("nonempty patch required")
    if set(patch) - {"context_policy", "review_policy"}:
        raise ValueError("immutable/unknown patch fields")
    result = deepcopy(dict(patch))
    for section, values in result.items():
        allowed = {"mode"} if section == "context_policy" else {
            "mode", "retrieve_controls"
        }
        if not isinstance(values, dict) or not values or set(values) - allowed:
            raise ValueError("invalid policy section")
        if "mode" in values:
            modes = (
                {"ranked_passages", "experimental_context"}
                if section == "context_policy"
                else {"on_conflict", "on_scope_ambiguity", "always"}
            )
            if not isinstance(values["mode"], str) or values["mode"] not in modes:
                raise ValueError("invalid policy mode")
        if "retrieve_controls" in values and type(values["retrieve_controls"]) is not bool:
            raise ValueError("retrieve_controls must be boolean")
    return result

def apply_policy_patch(policy, patch):
    result = deepcopy(dict(policy))
    for section, changes in validate_policy_patch(patch).items():
        existing = result.get(section, {})
        if not isinstance(existing, dict):
            raise ValueError("invalid existing policy section")
        result[section] = {**existing, **changes}
    if result == policy:
        raise ValueError("policy patch has no effect")
    return result

def promotion_decision(baseline, candidate):
    """Evaluator-owned records only; validation selection, never final test.

    Required fields:
    manifest_hash, model, budget, split, case_ids, policy_hash, finalized,
    total_cost, correct_count, decision_count, supported_count, support_count,
    reference_hits, reference_count, budget_ok, integrity_ok.
    """
    reasons = []
    for label, record in (("baseline", baseline), ("candidate", candidate)):
        for field in ("manifest_hash", "model", "policy_hash"):
            if not isinstance(record.get(field), str) or not record[field].strip():
                raise ValueError(f"invalid {label}.{field}")
        if not isinstance(record.get("budget"), dict) or not record["budget"]:
            raise ValueError("budget must be a nonempty object")
        json.dumps(record["budget"], sort_keys=True, allow_nan=False)
        ids = _ids(record.get("case_ids"), "case IDs")
        for field in (
            "correct_count", "decision_count", "supported_count",
            "support_count", "reference_hits", "reference_count",
        ):
            if type(record.get(field)) is not int or record[field] < 0:
                raise ValueError(f"invalid {label}.{field}")
        if (
            not record["decision_count"]
            or record["decision_count"] != len(ids)
            or record["correct_count"] > record["decision_count"]
            or not record["support_count"]
            or record["supported_count"] > record["support_count"]
            or not record["reference_count"]
            or record["reference_hits"] > record["reference_count"]
        ):
            raise ValueError("inconsistent evaluation counts")
        cost = record.get("total_cost")
        if type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0:
            raise ValueError("invalid cost")
        if record.get("split") != "validation":
            reasons.append(f"{label}: selection requires validation")
        for flag in ("finalized", "budget_ok", "integrity_ok"):
            if record.get(flag) is not True:
                reasons.append(f"{label}: {flag} failed")
    for field in (
        "manifest_hash", "model", "decision_count", "support_count",
        "reference_count",
    ):
        if baseline[field] != candidate[field]:
            reasons.append(f"different {field}")
    if json.dumps(baseline["budget"], sort_keys=True) != json.dumps(
        candidate["budget"], sort_keys=True
    ):
        reasons.append("different budget")
    if set(baseline["case_ids"]) != set(candidate["case_ids"]):
        reasons.append("different case IDs")
    if baseline["policy_hash"] == candidate["policy_hash"]:
        reasons.append("unchanged policy")
    for field in ("correct_count", "supported_count", "reference_hits"):
        if candidate[field] < baseline[field]:
            reasons.append(f"{field} regressed")

    old_cost = Decimal(str(baseline["total_cost"]))
    new_cost = Decimal(str(candidate["total_cost"]))
    quality_gain = candidate["correct_count"] > baseline["correct_count"]
    cost_gain = old_cost > 0 and new_cost <= old_cost * Decimal("0.85")
    reduction = float((old_cost - new_cost) / old_cost) if old_cost > 0 else None
    if old_cost <= 0:
        reasons.append("positive baseline cost required")
    if not quality_gain and not cost_gain:
        reasons.append("no correctness gain or 15% cost reduction")
    return {
        "promote": not reasons, "reasons": reasons,
        "quality_gain": quality_gain, "cost_gain": cost_gain,
        "cost_reduction": reduction, "minimum_cost_reduction": 0.15,
        "baseline_policy_hash": baseline["policy_hash"],
        "candidate_policy_hash": candidate["policy_hash"],
    }
