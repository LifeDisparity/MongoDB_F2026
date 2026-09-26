"""Replay the same complete entity upserts emitted by the repository.

No timestamps, random IDs, source reads or model calls occur during replay.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json


EVENT_ENTITIES = {
    "investigation.created": ("investigations", ("investigation_id",)),
    "investigation.updated": ("investigations", ("investigation_id",)),
    "decision.recorded": ("decisions", ("decision_id",)),
    "evidence.upserted": ("evidence", ("evidence_id",)),
    "claim.upserted": ("claims", ("claim_id",)),
    "source.availability_changed": ("source_state", ("source_id", "source_version")),
    "policy.proposed": ("policies", ("policy_version",)),
    "policy.promoted": ("policies", ("policy_version",)),
    "policy.rejected": ("policies", ("policy_version",)),
    "evaluation.completed": ("evaluations", ("evaluation_id",)),
}
EVENT_TYPES = frozenset(EVENT_ENTITIES) | {"run.created", "worker.resumed", "run.completed"}


def make_event(run_id, sequence, operation_id, occurred_at, kind, payload):
    """The transaction supplies one contiguous sequence for each accepted event."""
    if kind not in EVENT_TYPES:
        raise ValueError(f"unsupported event type: {kind}")
    if type(sequence) is not int or sequence < 1:
        raise ValueError("event sequence must be a positive integer")
    digest = sha256(json.dumps(
        [run_id, operation_id, sequence, kind], separators=(",", ":")
    ).encode()).hexdigest()
    return {
        "schema_version": 1, "run_id": run_id, "sequence": sequence,
        "event_id": "evt_" + digest, "operation_id": operation_id,
        "occurred_at": occurred_at, "type": kind, "payload": deepcopy(payload),
    }


def replay_events(events, initial=None):
    """Apply contiguous events, ignoring already-applied duplicate delivery.

    A gap is an error; clients must fetch the missing page before advancing.
    Pass the resulting snapshot as ``initial`` to continue a paginated replay.
    """
    state = deepcopy(initial) if initial is not None else None
    for event in events:
        if event.get("schema_version") != 1 or event.get("type") not in EVENT_TYPES:
            raise ValueError("unknown event schema or type")
        sequence = event["sequence"]
        cursor = state["last_sequence"] if state is not None else 0
        if state is not None and state["run_id"] != event["run_id"]:
            raise ValueError("cannot combine different runs")
        if sequence <= cursor:
            continue
        if sequence != cursor + 1:
            raise ValueError(f"event gap: expected {cursor + 1}, received {sequence}")
        kind = event["type"]
        if kind == "run.created":
            if state is not None:
                raise ValueError("run already initialized")
            state = deepcopy(event["payload"])
            if state.get("run_id") != event["run_id"]:
                raise ValueError("run creation identity mismatch")
        elif state is None:
            raise ValueError("replay must begin with run.created")
        elif kind in EVENT_ENTITIES:
            collection, fields = EVENT_ENTITIES[kind]
            entity = deepcopy(event["payload"])
            identity = tuple(entity[field] for field in fields)
            rows = state.setdefault(collection, [])
            for index, row in enumerate(rows):
                if tuple(row[field] for field in fields) == identity:
                    rows[index] = entity
                    break
            else:
                rows.append(entity)
            rows.sort(key=lambda row: tuple(row[field] for field in fields))
        elif kind == "run.completed":
            state["status"] = event["payload"].get("status", "completed")
        state["last_sequence"] = sequence
    return state
