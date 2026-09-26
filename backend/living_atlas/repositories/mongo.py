"""MongoDB entity, operation and event persistence.

Every accepted mutation and its contiguous events commit in the same snapshot
transaction. The run watermark serializes writers, including source withdrawal
versus late model output. Use an Atlas cluster or local replica set; standalone
MongoDB and in-memory fallbacks are deliberately unsupported.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json

from pymongo import ASCENDING, MongoClient, ReadPreference
from pymongo.errors import DuplicateKeyError, PyMongoError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from living_atlas.domain.dependencies import change_source_availability
from living_atlas.events.replay import make_event


class RepositoryError(Exception):
    """A safe public error; never includes the connection string."""


class NotFound(RepositoryError):
    pass


class Conflict(RepositoryError):
    pass


class IntegrityError(RepositoryError):
    pass


class RepositoryUnavailable(RepositoryError):
    pass


IDENTITIES = {
    "sources": ("source_id", "source_version"),
    "chunks": ("chunk_id",),
    "source_state": ("source_id", "source_version"),
    "evidence": ("evidence_id",),
    "claims": ("claim_id",),
    "investigations": ("investigation_id",),
    "decisions": ("decision_id",),
    "policies": ("policy_version",),
    "evaluations": ("evaluation_id",),
}
GLOBAL = {"sources", "chunks"}
MUTABLE = {"claims", "investigations", "policies"}
UPSERT_EVENTS = {
    "evidence": "evidence.upserted", "claims": "claim.upserted",
    "investigations": "investigation.created", "decisions": "decision.recorded",
    "policies": "policy.proposed", "evaluations": "evaluation.completed",
}


def _utcnow():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hash(value):
    return sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()


def _public(row):
    return {key: deepcopy(value) for key, value in row.items() if key != "_id"}


def _identifier(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


class MongoRepository:
    def __init__(self, uri, database="living_atlas", *, server_selection_timeout_ms=5000):
        _identifier(uri, "MongoDB URI")
        _identifier(database, "database")
        self.client = MongoClient(
            uri, serverSelectionTimeoutMS=server_selection_timeout_ms,
            connectTimeoutMS=server_selection_timeout_ms, appname="living-atlas",
        )
        self.db = self.client[database]

    def close(self):
        self.client.close()

    def ping(self):
        try:
            hello = self.client.admin.command("hello")
            if not hello.get("setName") and hello.get("msg") != "isdbgrid":
                raise RepositoryUnavailable("MongoDB replica set or Atlas cluster required")
            return {"ok": True, "transactions": True}
        except PyMongoError as exc:
            raise RepositoryUnavailable("MongoDB is unavailable; check server configuration") from exc

    def ensure_indexes(self):
        self.ping()
        try:
            self.db.runs.create_index("run_id", unique=True)
            for name, fields in IDENTITIES.items():
                keys = ([] if name in GLOBAL else [("run_id", ASCENDING)])
                self.db[name].create_index(keys + [(field, ASCENDING) for field in fields], unique=True)
            self.db.events.create_index([("run_id", 1), ("sequence", 1)], unique=True)
            self.db.events.create_index([("run_id", 1), ("event_id", 1)], unique=True)
            self.db.operations.create_index([("run_id", 1), ("operation_id", 1)], unique=True)
            self.db.evidence.create_index([("run_id", 1), ("source_id", 1), ("source_version", 1)])
            self.db.claims.create_index([("run_id", 1), ("evidence_ids", 1)])
            self.db.claims.create_index([("run_id", 1), ("conflicting_evidence_ids", 1)])
            self.db.chunks.create_index([("source_id", 1), ("source_version", 1)])
        except PyMongoError as exc:
            raise RepositoryUnavailable("Unable to create required MongoDB indexes") from exc

    def _transaction(self, callback):
        try:
            with self.client.start_session() as session:
                return session.with_transaction(
                    callback, read_concern=ReadConcern("snapshot"),
                    write_concern=WriteConcern("majority"),
                    read_preference=ReadPreference.PRIMARY,
                    max_commit_time_ms=10000,
                )
        except DuplicateKeyError as exc:
            raise Conflict("A concurrent operation already owns this identity; retry the same request") from exc
        except PyMongoError as exc:
            raise RepositoryUnavailable("MongoDB transaction failed; retry the same operation ID") from exc

    def _run(self, run_id, session):
        result = self.db.runs.find_one({"run_id": run_id}, session=session)
        if result is None:
            raise NotFound("Run not found")
        return result

    def _query(self, collection, row, run_id):
        query = {field: _identifier(row.get(field), field) for field in IDENTITIES[collection]}
        if collection not in GLOBAL:
            if row.get("run_id", run_id) != run_id:
                raise IntegrityError("Entity belongs to a different run")
            query["run_id"] = run_id
        return query

    def _insert_immutable(self, collection, row, run_id, session):
        query = self._query(collection, row, run_id)
        value = deepcopy(row)
        if "_id" in value:
            raise IntegrityError("MongoDB internal IDs cannot be supplied")
        if collection not in GLOBAL:
            value["run_id"] = run_id
        existing = self.db[collection].find_one(query, session=session)
        if existing is not None:
            if _public(existing) != value:
                raise Conflict(f"Immutable {collection} identity has different content")
            return value
        self.db[collection].insert_one(deepcopy(value), session=session)
        return value

    def _snapshot(self, run_id, session):
        run = self._run(run_id, session)
        result = {key: deepcopy(value) for key, value in run.items()
                  if key not in {"_id", "source_keys", "revision"}}
        result["schema_version"] = 1
        source_filter = {"$or": run["source_keys"]} if run["source_keys"] else {"_id": {"$exists": False}}
        result["sources"] = [_public(row) for row in self.db.sources.find(source_filter, session=session)
                             .sort([("source_id", 1), ("source_version", 1)])]
        for collection, fields in IDENTITIES.items():
            if collection in GLOBAL:
                continue
            result[collection] = [_public(row) for row in self.db[collection]
                                  .find({"run_id": run_id}, session=session)
                                  .sort([(field, 1) for field in fields])]
        return result

    def snapshot(self, run_id):
        """Return all visible entities and watermark from one database snapshot."""
        return self._transaction(lambda session: self._snapshot(run_id, session))

    def events(self, run_id, after=0, limit=500):
        if type(after) is not int or after < 0 or type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("after must be nonnegative; limit must be 1..1000")
        def read(session):
            run = self._run(run_id, session)
            watermark = run["last_sequence"]
            if after > watermark:
                raise Conflict("Event cursor exceeds the run watermark")
            rows = [_public(row) for row in self.db.events.find(
                {"run_id": run_id, "sequence": {"$gt": after, "$lte": watermark}}, session=session,
            ).sort("sequence", 1).limit(limit)]
            return {"run_id": run_id, "events": rows, "last_sequence": watermark,
                    "has_more": bool(rows and rows[-1]["sequence"] < watermark)}
        return self._transaction(read)

    def _duplicate(self, run_id, operation_id, request_hash, session):
        previous = self.db.operations.find_one(
            {"run_id": run_id, "operation_id": operation_id}, session=session,
        )
        if previous is None:
            return None
        if previous["request_hash"] != request_hash:
            raise Conflict("Operation ID reused for a different request")
        result = deepcopy(previous["result"])
        result["replayed"] = True
        return result

    def _finish(self, run, operation_id, request_hash, domain_events, session, *, occurred_at=None):
        now = occurred_at or _utcnow()
        first = run["last_sequence"] + 1
        events = [make_event(run["run_id"], first + index, operation_id, now,
                             event["type"], event["payload"])
                  for index, event in enumerate(domain_events)]
        last = run["last_sequence"] + len(events)
        changes = {"last_sequence": last}
        for event in domain_events:
            if event["type"] == "run.completed":
                changes["status"] = event["payload"].get("status", "completed")
        update = self.db.runs.update_one(
            {"run_id": run["run_id"], "revision": run["revision"]},
            {"$set": changes, "$inc": {"revision": 1}}, session=session,
        )
        if update.modified_count != 1:
            raise Conflict("Run changed during acceptance; retry the same operation ID")
        if events:
            self.db.events.insert_many(deepcopy(events), session=session)
        result = {"operation_id": operation_id, "first_sequence": first if events else None,
                  "last_sequence": last, "events": events, "replayed": False}
        self.db.operations.insert_one({
            "run_id": run["run_id"], "operation_id": operation_id,
            "request_hash": request_hash, "occurred_at": now, "result": deepcopy(result),
        }, session=session)
        return result

    def _validate_chunk(self, row, sources):
        identity = (row.get("source_id"), row.get("source_version"))
        if identity not in sources:
            raise IntegrityError("Chunk references a source outside this run")
        text = row.get("text")
        if not isinstance(text, str) or sha256(text.encode()).hexdigest() != row.get("content_sha256"):
            raise IntegrityError("Chunk text does not match its content hash")
        start, end = row.get("start_offset"), row.get("end_offset")
        if type(start) is not int or type(end) is not int or start < 0 or end - start != len(text):
            raise IntegrityError("Chunk offsets do not match its text")

    def _evidence_quote(self, row, run_id, session, *, accepting=False):
        state = self.db.source_state.find_one({
            "run_id": run_id, "source_id": row.get("source_id"),
            "source_version": row.get("source_version"),
        }, session=session)
        if state is None:
            raise IntegrityError("Evidence source version is outside the run")
        if accepting and not state["available"]:
            raise Conflict("Evidence source was withdrawn before acceptance")
        chunk = self.db.chunks.find_one({"chunk_id": row.get("chunk_id")}, session=session)
        if chunk is None or any(chunk.get(field) != row.get(field) for field in ("source_id", "source_version")):
            raise IntegrityError("Evidence references an unknown or mismatched chunk")
        if sha256(chunk["text"].encode()).hexdigest() != chunk["content_sha256"]:
            raise IntegrityError("Stored source chunk failed integrity verification")
        start, end = row.get("start_offset"), row.get("end_offset")
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(chunk["text"]):
            raise IntegrityError("Invalid evidence offsets")
        _identifier(row.get("span_id"), "span_id")
        quote = chunk["text"][start:end]
        if sha256(quote.encode()).hexdigest() != row.get("quote_sha256"):
            raise IntegrityError("Evidence quotation failed integrity verification")
        return quote, state

    def _validate_claim(self, row, run_id, session):
        positive = row.get("evidence_ids", [])
        negative = row.get("conflicting_evidence_ids", [])
        for refs in (positive, negative):
            if not isinstance(refs, list) or any(not isinstance(value, str) for value in refs) or len(set(refs)) != len(refs):
                raise IntegrityError("Claim evidence IDs must be unique strings")
        if set(positive) & set(negative):
            raise IntegrityError("The same evidence cannot support and conflict")
        for identity in positive + negative:
            evidence = self.db.evidence.find_one({"run_id": run_id, "evidence_id": identity}, session=session)
            if evidence is None:
                raise IntegrityError("Claim references evidence outside the run")
            self._evidence_quote(evidence, run_id, session, accepting=True)
        row["usable_evidence_ids"] = list(positive)
        row["usable_conflicting_evidence_ids"] = list(negative)
        status = row.get("status")
        if status not in {"candidate", "supported", "conflicting", "needs_review", "unsupported"}:
            raise IntegrityError("Invalid claim status")
        if status == "supported" and (not positive or negative):
            raise IntegrityError("Supported claim must have positive evidence and no unresolved conflict")
        if status == "conflicting" and not negative:
            raise IntegrityError("Conflicting claim must reference conflicting evidence")

    def create_run(self, run_id, *, mode, sources=None, chunks=None, evidence=None,
                   claims=None, investigations=None, policy=None, metadata=None,
                   operation_id=None, decisions=None, evaluations=None):
        _identifier(run_id, "run_id")
        if mode not in {"fixture", "sources", "live"}:
            raise ValueError("mode must be fixture, sources or live")
        operation_id = operation_id or "create:" + run_id
        _identifier(operation_id, "operation_id")
        request = deepcopy({
            "mode": mode, "sources": sources or [], "chunks": chunks or [],
            "evidence": evidence or [], "claims": claims or [],
            "investigations": investigations or [], "policies": [policy] if policy else [],
            "metadata": metadata or {}, "decisions": decisions or [], "evaluations": evaluations or [],
        })
        request_hash = _hash(request)
        def create(session):
            duplicate = self._duplicate(run_id, operation_id, request_hash, session)
            if duplicate:
                return duplicate
            if self.db.runs.find_one({"run_id": run_id}, session=session):
                raise Conflict("Run already exists")
            source_keys = [self._query("sources", row, run_id) for row in request["sources"]]
            source_ids = {(row["source_id"], row["source_version"]) for row in source_keys}
            if len(source_ids) != len(source_keys):
                raise IntegrityError("Duplicate source version in run")
            now = _utcnow()
            run = {"run_id": run_id, "mode": mode, "created_at": now, "metadata": request["metadata"],
                   "last_sequence": 0, "revision": 0, "source_keys": source_keys, "status": "ready"}
            self.db.runs.insert_one(deepcopy(run), session=session)
            for row in request["sources"]:
                self._insert_immutable("sources", row, run_id, session)
                self._insert_immutable("source_state", {
                    "source_id": row["source_id"], "source_version": row["source_version"],
                    "available": True, "revision": 0, "availability_history": [],
                }, run_id, session)
            for row in request["chunks"]:
                self._validate_chunk(row, source_ids)
                self._insert_immutable("chunks", row, run_id, session)
            for collection in ("evidence", "claims", "investigations", "decisions", "policies", "evaluations"):
                for original in request[collection]:
                    row = deepcopy(original)
                    if collection == "evidence":
                        self._evidence_quote(row, run_id, session, accepting=True)
                    elif collection == "claims":
                        self._validate_claim(row, run_id, session)
                    if collection in MUTABLE:
                        if row.get("revision", 0) != 0:
                            raise IntegrityError("New entity revision must be zero")
                        row["revision"] = 0
                    self._insert_immutable(collection, row, run_id, session)
            initial = self._snapshot(run_id, session)
            initial["last_sequence"] = 1
            return self._finish(run, operation_id, request_hash,
                                [{"type": "run.created", "payload": initial}], session, occurred_at=now)
        return self._transaction(create)

    def accept_operation(self, run_id, operation_id, *, payload, upserts=None,
                         events=None, expected_revisions=None):
        """Accept an operation once and derive complete events for its upserts.

        upserts maps collection names to complete entity lists. Updates to claims,
        investigations and policies require expected_revisions[collection][ID].
        New entity revisions are zero; update revisions are assigned here.
        Additional events may only be worker.resumed or run.completed.
        """
        _identifier(operation_id, "operation_id")
        request = deepcopy({"payload": payload, "upserts": upserts or {},
                            "events": events or [], "expected_revisions": expected_revisions or {}})
        if set(request["upserts"]) - set(UPSERT_EVENTS):
            raise ValueError("Unsupported entity collection; source availability uses change_availability")
        if any(event.get("type") not in {"worker.resumed", "run.completed"} for event in request["events"]):
            raise ValueError("Entity events are derived from accepted upserts")
        request_hash = _hash(request)
        def accept(session):
            run = self._run(run_id, session)
            duplicate = self._duplicate(run_id, operation_id, request_hash, session)
            if duplicate:
                return duplicate
            output_events = []
            for collection in UPSERT_EVENTS:
                seen = set()
                for original in request["upserts"].get(collection, []):
                    row = deepcopy(original)
                    query = self._query(collection, row, run_id)
                    row["run_id"] = run_id
                    identity = row[IDENTITIES[collection][0]]
                    if identity in seen:
                        raise IntegrityError("Duplicate entity in one operation")
                    seen.add(identity)
                    if collection == "evidence":
                        self._evidence_quote(row, run_id, session, accepting=True)
                    elif collection == "claims":
                        self._validate_claim(row, run_id, session)
                    event_type = UPSERT_EVENTS[collection]
                    existing = self.db[collection].find_one(query, session=session)
                    if collection in MUTABLE:
                        if "_id" in row:
                            raise IntegrityError("MongoDB internal IDs cannot be supplied")
                        if existing is None:
                            if row.get("revision", 0) != 0:
                                raise Conflict("New entity revision must be zero")
                            row["revision"] = 0
                            self.db[collection].insert_one(deepcopy(row), session=session)
                        else:
                            expected = request["expected_revisions"].get(collection, {}).get(identity)
                            if type(expected) is not int or expected != existing["revision"]:
                                raise Conflict(f"Stale or missing {collection} revision")
                            if collection == "policies" and any(
                                row.get(field) != existing.get(field) for field in
                                ("configuration", "configuration_sha256", "parent_policy_version", "proposed_by", "development_failure_ids")
                            ):
                                raise IntegrityError("Policy configuration and provenance are immutable")
                            row["revision"] = expected + 1
                            changed = self.db[collection].replace_one(
                                {**query, "revision": expected}, deepcopy(row), session=session,
                            )
                            if changed.modified_count != 1:
                                raise Conflict("Entity changed during acceptance")
                            if collection == "investigations":
                                event_type = "investigation.updated"
                            if collection == "policies" and row.get("selection_status") in {"promoted", "rejected"}:
                                event_type = "policy." + row["selection_status"]
                    else:
                        row = self._insert_immutable(collection, row, run_id, session)
                    if existing is None or _public(existing) != row:
                        output_events.append({"type": event_type, "payload": row})
            output_events.extend(request["events"])
            return self._finish(run, operation_id, request_hash, output_events, session)
        return self._transaction(accept)

    def change_availability(self, run_id, source_id, source_version, available,
                            operation_id, reason="", *, expected_revision=None):
        _identifier(operation_id, "operation_id")
        request = dict(source_id=source_id, source_version=source_version, available=available,
                       reason=reason, expected_revision=expected_revision)
        request_hash = _hash(request)
        def change(session):
            run = self._run(run_id, session)
            duplicate = self._duplicate(run_id, operation_id, request_hash, session)
            if duplicate:
                return duplicate
            snapshot = self._snapshot(run_id, session)
            snapshot["applied_operations"] = []
            if expected_revision is not None:
                current = next((row for row in snapshot["source_state"] if
                                (row["source_id"], row["source_version"]) == (source_id, source_version)), None)
                if current is None or type(expected_revision) is not int or current["revision"] != expected_revision:
                    raise Conflict("Stale or unknown source availability revision")
            now = _utcnow()
            result = change_source_availability(
                snapshot, source_id=source_id, source_version=source_version,
                available=available, operation_id=operation_id, reason=reason, occurred_at=now,
            )
            for collection, rows in (("source_state", result["source_state_upserts"]), ("claims", result["claim_upserts"])):
                for row in rows:
                    query = self._query(collection, row, run_id)
                    changed = self.db[collection].replace_one(
                        {**query, "revision": row["revision"] - 1}, deepcopy(row), session=session,
                    )
                    if changed.modified_count != 1:
                        raise Conflict("Source dependency changed during acceptance")
            return self._finish(run, operation_id, request_hash, result["events"], session, occurred_at=now)
        return self._transaction(change)

    def evidence(self, run_id, evidence_id):
        """Reconstruct the quotation from immutable server-held text, even after withdrawal."""
        def read(session):
            self._run(run_id, session)
            row = self.db.evidence.find_one({"run_id": run_id, "evidence_id": evidence_id}, session=session)
            if row is None:
                raise NotFound("Evidence not found")
            quote, state = self._evidence_quote(row, run_id, session)
            source = self.db.sources.find_one({"source_id": row["source_id"], "source_version": row["source_version"]}, session=session)
            return {**_public(row), "quote": quote, "source": _public(source), "source_state": _public(state)}
        return self._transaction(read)
