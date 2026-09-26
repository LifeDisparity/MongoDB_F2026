# Run the evidence workspace

## Requirements

Python 3.11+ (verified with 3.13), Node 22.12+ (verified with 26.5), npm,
and a MongoDB replica set or Atlas cluster. The local option requires MongoDB
Community Server `mongod` on PATH. Transactions are required; a standalone
server is not a substitute.

## Install

From the repository root:

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.lock
.venv/bin/pip install --no-deps -e backend
npm --prefix frontend ci
```

Python and frontend dependency versions are pinned in
`backend/requirements.lock` and `frontend/package-lock.json`.
No unit-test framework or suite is installed.

## Local launch

```sh
.venv/bin/python scripts/dev.py --local-mongo --allow-demo
```

Open http://127.0.0.1:5173. The launcher owns a dedicated MongoDB replica set on
127.0.0.1:27019, API on 8000, and Vite on 5173. MongoDB data stays under ignored
`data/cache/local-mongo`. Ctrl-C shuts down processes started by this launch.
An existing matching local replica set can be reused and is not stopped by the
launcher. An unrelated MongoDB on that port is rejected without reconfiguration.

Choose **Explore dependency demo**. This creates an explicitly labeled synthetic
run in real MongoDB. It demonstrates A:S1, B:S1+S2 and C:S3, supports withdrawal
and restoration, opens canonical evidence, replays accepted events and exports
the current metadata/claim dossier. It contains no model results.

## Atlas configuration

Set `MONGODB_URI` and optionally `MONGODB_DATABASE` in the ignored root `.env`
or server environment. Then run:

```sh
.venv/bin/python scripts/dev.py --allow-demo
```

Use a project-specific database and an Atlas URI whose network rules allow this
machine. Credentials never go into frontend variables or committed files.
The same repository implementation uses transactions with Atlas or a local
replica set. This wave was verified on local MongoDB; Atlas execution remains
pending configuration. The app does not silently replace unavailable storage.

Omit `--allow-demo` to disable availability mutations (HTTP 403). No authentication
is implemented for this MVP; the launcher binds only to localhost.

## Import real papers

```sh
.venv/bin/python -m living_atlas.data.import_sources --manifest data/manifests/showcase.json --cache-dir data/raw/flyaoc --download
```

The first import downloads the pinned literature file (~660 MB), verifies it,
and retains two selected development articles in the private cache. Later runs
reuse their exact source versions. Add `--ontologies` only when preparing LA-05.
See [source provenance and limits](../data/manifests/README.md).

Choose **Open scientific sources**, select a paper, enter a decision-relevant
search, read exact spans and pin evidence. Accepted evidence can be reopened
after a process restart or source withdrawal. Pinning creates evidence records;
it does not create or certify a biological claim.

The two papers are restricted author manuscripts. Their full text stays in
ignored `data/raw`; exports contain metadata, references and claims, not article
text. Ten-a figure captions are absent from the selected upstream corpus and
its experimental paragraphs have the upstream label INTRO. This subset is
development-only, not the frozen scientific benchmark.

## Verification

```sh
npm --prefix frontend run build
.venv/bin/python -m compileall -q backend/living_atlas scripts
npm --prefix frontend exec -- playwright install chromium
npm --prefix frontend run e2e
```

E2E needs the local replica set from the development launch and the imported
source cache. It starts separate API/Vite processes on 8001/5174, creates a
unique MongoDB database, drives Chromium through the actual UI, and kills and
restarts its own API process. Override `MONGODB_URI`, `E2E_API_PORT`, or
`E2E_WEB_PORT` as needed. It does not stop an unrelated service.

Artifacts and service logs are written under ignored
`artifacts/private/workspace-<timestamp>`. Databases and artifacts are retained
for inspection; no destructive cleanup runs automatically. E2E evidence includes
run IDs, source/manifest hashes, the source commit, measured duration and checks.

This is engineering browser/API/MongoDB verification, including genuine source
retrieval. It is not a real-model scientific benchmark, Atlas validation,
LangGraph worker recovery or a demonstrated policy improvement. Those remain
explicit dependencies. `POST /runs/{id}/resume` returns HTTP 501 until the
checkpointed scientific workflow exists.

## API

Interactive schema: http://127.0.0.1:8000/docs.

Core routes follow [Contracts](CONTRACTS.md). Additions for source browsing:

- `GET /runs/{id}/search?gene_id=...&query=...&cursor=...`
- `GET /runs/{id}/chunks/{chunk_id}?source_version=...&cursor=...`
- `POST /runs/{id}/evidence` with span_ids, source_version and operation_id.

Create-run requests may supply run_id and operation_id for retry-safe creation.
Evidence and availability retries must reuse the original operation_id and
payload. Reusing an ID with different content is a conflict. Read continuation
cursors are opaque and version-bound. Availability changes invalidate search
cursors. Canonical offsets count Unicode code points within the chunk; clients
display server-returned quotes instead of slicing JavaScript strings.

A run's source versions must match the configured source catalog for new reads.
Historical accepted evidence is reconstructed from MongoDB even when the local
import cache changes. Unknown sources, altered spans, changed versions and
withdrawn-source acceptance reject.
