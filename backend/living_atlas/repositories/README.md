# MongoDB repository integration

`MongoRepository(uri, database)` uses synchronous PyMongo. Construct it once per
server process, call `ensure_indexes()` at startup, and `close()` at shutdown.
Atlas or a MongoDB replica set is required. There is no persistence fallback.
Use FastAPI synchronous handlers or a thread pool for these blocking methods.

All mutations run with snapshot read concern and majority write concern. The
run document serializes accepted writers, so source withdrawal and acceptance
of late model output cannot commit using inconsistent source availability.
The transaction contains the entity changes, accepted-operation record, events
and sequence watermark. Read snapshots and event pages also use a snapshot
transaction, preventing a snapshot/event-watermark race.

## Public methods

- `ping()` returns `{ok, transactions}` or raises `RepositoryUnavailable`.
- `create_run(run_id, *, mode, sources=[], chunks=[], evidence=[], claims=[],
  investigations=[], policy=None, metadata=None, operation_id=None,
  decisions=[], evaluations=[])` stores the initial records and a `run.created`
  event whose payload is the complete initial public snapshot. `mode` is
  `fixture`, `sources` or `live`; no model execution is implied by storing a run.
- `snapshot(run_id)` returns the complete public state with `last_sequence`.
  It excludes chunks, operation records and internal MongoDB IDs.
- `events(run_id, after=0, limit=500)` returns `{run_id, events, last_sequence,
  has_more}`. The watermark is the committed run watermark, **not** the last
  event on a truncated page. Continue from the last received event sequence.
- `evidence(run_id, evidence_id)` returns the Evidence fields plus `quote`,
  `source`, and `source_state`. It reconstructs the quotation from the stored
  chunk and checks its hash. Historical evidence stays inspectable after
  withdrawal. The API decides which permitted source fields to expose.
- `change_availability(run_id, source_id, source_version, available,
  operation_id, reason="", *, expected_revision=None)` atomically applies the
  existing scientific dependency transition and emits its complete upserts.
- `accept_operation(run_id, operation_id, *, payload, upserts=None,
  events=None, expected_revisions=None)` accepts complete entity upserts. The
  collection map accepts `evidence`, `claims`, `investigations`, `decisions`,
  `policies`, and `evaluations`. Mutable entity updates need the previous
  revision, for example `expected_revisions={"claims": {"claim-1": 0}}`.
  The repository assigns revision 1. New mutable entities start at revision 0.
  `events` accepts additional `worker.resumed` or `run.completed` records shaped
  as `{type, payload}`. Entity events are derived from the persisted upserts.

Mutation methods return `{operation_id, first_sequence, last_sequence, events,
replayed}`. Repeat an identical request under the same operation ID to retrieve
the original accepted result (`replayed: true`). Reusing the ID with different
content raises `Conflict`. A no-op availability change is still recorded as an
accepted operation but creates no events; `first_sequence` is then null.

Sources/chunks are globally shared immutable records; all scientific working
state and source availability are namespaced by `run_id`. Evidence identity is
immutable within a run. Claims, investigations and policy selection records
have optimistic revisions. Changing policy configuration or provenance under
the same policy identity is rejected. This repository is not a workflow
scheduler and does not replace LangGraph checkpoints.

`RepositoryError` subclasses are `NotFound`, `Conflict`, `IntegrityError`, and
`RepositoryUnavailable`. The messages omit connection strings. Translate these
at the API boundary; never expose the exception cause or raw driver error.

## Evidence coordinates and replay

Chunk offsets locate its exact `text` within normalized source text.
Evidence offsets are relative to that chunk. `content_sha256` covers chunk
text and `quote_sha256` covers the selected exact substring, both UTF-8.
Before accepting evidence or claims the repository rechecks the run-scoped
source availability, source version, chunk identity and quotation hash.
Evidence tools must validate that selected span IDs were actually issued.

`living_atlas.events.replay_events(events, initial=None)` rebuilds a snapshot
from `run.created` and complete entity upserts. It rejects gaps and mixed runs,
and tolerates already-applied delivery. `investigation.updated` updates an
existing investigation without falsely presenting its update as a creation.

## Verification boundary

No unit tests are supplied. Syntax/build checks are permitted; behavior must be
verified through the application E2E flows in `docs/E2E.md`. A local replica-set
integration is not evidence that Atlas or a real model was exercised.

Transaction behavior follows the [official PyMongo transaction guide](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/crud/transactions/).
