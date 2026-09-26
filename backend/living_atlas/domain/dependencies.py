"""Pure availability transitions; repository adds transactions/run/event order."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

STATUSES = {"candidate", "supported", "conflicting", "needs_review", "unsupported"}

def _index(rows, fields, label):
    if not isinstance(rows, list):
        raise ValueError(f"{label} must be a list")
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{label} entries must be objects")
        key = tuple(row.get(field) for field in fields)
        if any(not isinstance(value, str) or not value.strip() for value in key):
            raise ValueError(f"invalid {label} identity")
        if key in result:
            raise ValueError(f"duplicate {label} identity")
        result[key] = row
    return result

def _refs(claim, field):
    values = claim.get(field, [])
    if not isinstance(values, list) or any(
        not isinstance(value, str) or not value for value in values
    ):
        raise ValueError(f"invalid {field}")
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate {field}")
    return values

def _revision(row):
    revision = row.get("revision", 0)
    if type(revision) is not int or revision < 0:
        raise ValueError("invalid revision")
    return revision

def change_source_availability(
    snapshot, *, source_id, source_version, available, operation_id,
    reason="", occurred_at=None,
):
    """Return detached state/upserts/events. Never certify restored support.

    Input: sources, source_state, evidence, claims, applied_operations lists.
    source_state is a run-scoped overlay; sources/evidence are immutable.
    Repositories must commit the returned operation ledger even for a no-op.
    """
    if not isinstance(snapshot, dict):
        raise ValueError("snapshot must be an object")
    for value in (source_id, source_version, operation_id):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("nonempty identifiers required")
    if type(available) is not bool or not isinstance(reason, str):
        raise ValueError("invalid availability request")
    if occurred_at is not None and not isinstance(occurred_at, str):
        raise ValueError("invalid occurred_at")

    sources = _index(snapshot.get("sources"), ("source_id", "source_version"), "sources")
    states = _index(snapshot.get("source_state"), ("source_id", "source_version"), "source_state")
    evidence = _index(snapshot.get("evidence"), ("evidence_id",), "evidence")
    claims = _index(snapshot.get("claims"), ("claim_id",), "claims")
    operations = _index(snapshot.get("applied_operations"), ("operation_id",), "operations")

    if sources.keys() != states.keys():
        raise ValueError("exactly one overlay is required per source version")
    for state in states.values():
        if type(state.get("available")) is not bool:
            raise ValueError("availability must be boolean")
        _revision(state)
        if not isinstance(state.get("availability_history", []), list):
            raise ValueError("invalid availability history")
    for item in evidence.values():
        identity = (item.get("source_id"), item.get("source_version"))
        if any(not isinstance(part, str) for part in identity) or identity not in sources:
            raise ValueError("evidence references unknown source version")

    def usable(ids, overlays):
        return [
            evidence_id for evidence_id in ids
            if overlays[
                (evidence[(evidence_id,)]["source_id"],
                 evidence[(evidence_id,)]["source_version"])
            ]["available"]
        ]

    for claim in claims.values():
        if claim.get("status") not in STATUSES:
            raise ValueError("invalid claim status")
        _revision(claim)
        if not isinstance(claim.get("support_history", []), list):
            raise ValueError("invalid support history")
        positive = _refs(claim, "evidence_ids")
        negative = _refs(claim, "conflicting_evidence_ids")
        if set(positive) & set(negative):
            raise ValueError("evidence cannot both support and conflict")
        for evidence_id in positive + negative:
            if (evidence_id,) not in evidence:
                raise ValueError("claim references unknown evidence")
        for cache_field, ids in (
            ("usable_evidence_ids", positive),
            ("usable_conflicting_evidence_ids", negative),
        ):
            if cache_field in claim and claim[cache_field] != usable(ids, states):
                raise ValueError("stale cached support")
    for operation in operations.values():
        if not isinstance(operation.get("payload"), dict):
            raise ValueError("operation requires request payload")

    key = (source_id, source_version)
    if key not in sources:
        raise ValueError("unknown source version")
    payload = dict(
        source_id=source_id, source_version=source_version,
        available=available, reason=reason, occurred_at=occurred_at,
    )
    result = deepcopy(snapshot)
    empty = {
        "snapshot": result, "source_state_upserts": [], "claim_upserts": [],
        "affected_claim_ids": [], "events": [],
    }
    previous = operations.get((operation_id,))
    if previous:
        if previous["payload"] != payload:
            raise ValueError("operation ID reused for a different request")
        return empty

    result["applied_operations"].append(
        {"operation_id": operation_id, "payload": payload}
    )
    original = states[key]
    if original["available"] == available:
        return empty

    changed = deepcopy(original)
    changed["available"] = available
    changed["revision"] = _revision(original) + 1
    changed.setdefault("availability_history", []).append({
        "operation_id": operation_id,
        "from_available": original["available"],
        "to_available": available,
        "from_revision": _revision(original),
        "reason": reason,
        "occurred_at": occurred_at,
    })
    result["source_state"] = [
        changed if (row["source_id"], row["source_version"]) == key else row
        for row in result["source_state"]
    ]
    next_states = dict(states)
    next_states[key] = changed

    def event(kind, identity, entity):
        digest = sha256(json.dumps(
            [operation_id, kind, identity], separators=(",", ":")
        ).encode()).hexdigest()
        return {
            "event_id": "dep_" + digest,
            "operation_id": operation_id,
            "type": kind,
            "payload": deepcopy(entity),
        }

    impacted = {
        item["evidence_id"] for item in evidence.values()
        if (item["source_id"], item["source_version"]) == key
    }
    updates = {}
    events = [event("source.availability_changed", key, changed)]
    for (claim_id,) in sorted(claims):
        claim = claims[(claim_id,)]
        positive = _refs(claim, "evidence_ids")
        negative = _refs(claim, "conflicting_evidence_ids")
        if not impacted.intersection(positive + negative):
            continue
        supports = usable(positive, next_states)
        conflicts = usable(negative, next_states)
        status = claim["status"]
        if conflicts:
            status = "conflicting"
        elif not supports:
            status = "unsupported"
        elif status in {"unsupported", "conflicting"}:
            status = "needs_review"
        updated = deepcopy(claim)
        updated.update(
            usable_evidence_ids=supports,
            usable_conflicting_evidence_ids=conflicts,
            status=status,
            revision=_revision(claim) + 1,
        )
        updated.setdefault("support_history", []).append({
            "operation_id": operation_id,
            "revision": _revision(claim),
            "status": claim["status"],
            "usable_evidence_ids": usable(positive, states),
            "usable_conflicting_evidence_ids": usable(negative, states),
        })
        updates[claim_id] = updated
        events.append(event("claim.upserted", (claim_id,), updated))

    result["claims"] = [
        updates.get(row["claim_id"], row) for row in result["claims"]
    ]
    return {
        "snapshot": result,
        "source_state_upserts": [deepcopy(changed)],
        "claim_upserts": [deepcopy(updates[key]) for key in sorted(updates)],
        "affected_claim_ids": sorted(updates),
        "events": events,
    }
