"""HTTP boundary for durable source/evidence workspace; no simulated model runs."""
from __future__ import annotations

from contextlib import asynccontextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
from threading import Lock
from functools import lru_cache
from typing import Literal
import uuid

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from living_atlas.contracts import (
    Claim, CreateRun, Decision, ErrorEnvelope, Evaluation, EventPage,
    Evidence, EvidenceDetail, Investigation, Policy, RequestModel,
    RunEvent, RunSnapshot, SourceAvailability, SourceChange,
)
from pydantic import Field
from living_atlas.repositories import (
    Conflict, IntegrityError, MongoRepository, NotFound, RepositoryError, RepositoryUnavailable,
)
from .fixtures import availability_fixture
from living_atlas.models import StructuredModelAdapter

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CATALOG_LOCK = Lock()

class RecordEvidence(RequestModel):
    span_ids: list[str] = Field(min_length=1, max_length=20)
    source_version: str = Field(min_length=1, max_length=200)
    operation_id: str = Field(min_length=1, max_length=200)

def error(code, message, status=400, retryable=False):
    return JSONResponse(
        ErrorEnvelope(code=code, message=message, retryable=retryable).model_dump(),
        status_code=status,
    )

def public_snapshot(snapshot):
    return RunSnapshot.model_validate(snapshot).model_dump(mode="json")

def public_event(event):
    row = dict(event)
    payload_models = {
        "run.created": RunSnapshot, "claim.upserted": Claim,
        "evidence.upserted": Evidence, "source.availability_changed": SourceAvailability,
        "investigation.created": Investigation, "investigation.updated": Investigation,
        "decision.recorded": Decision, "policy.proposed": Policy,
        "policy.promoted": Policy, "policy.rejected": Policy,
        "evaluation.completed": Evaluation,
    }
    model = payload_models.get(row["type"])
    if model:
        row["payload"] = model.model_validate(row["payload"]).model_dump(mode="json")
    return RunEvent.model_validate(row).model_dump(mode="json")

@asynccontextmanager
async def lifespan(app):
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise RuntimeError("MONGODB_URI is required; use the documented development launcher.")
    repo = MongoRepository(uri, os.environ.get("MONGODB_DATABASE", "living_atlas"))
    try:
        model_adapter = StructuredModelAdapter.from_env()
        try:
            repo.ensure_indexes()
            app.state.repo = repo
            app.state.model_adapter = model_adapter
            app.state.catalog_bundle = None
            yield
        finally:
            await model_adapter.close()
    finally:
        repo.close()

app = FastAPI(title="Living Atlas", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
)

@app.exception_handler(RepositoryError)
async def repository_error(request: Request, exc: RepositoryError):
    if isinstance(exc, NotFound):
        return error("not_found", str(exc), 404)
    if isinstance(exc, Conflict):
        return error("conflict", str(exc), 409)
    if isinstance(exc, IntegrityError):
        return error("integrity_rejected", str(exc), 422)
    return error("storage_unavailable", "MongoDB is unavailable. Retry the same operation ID.", 503, True)

@app.exception_handler(RequestValidationError)
async def request_error(request: Request, exc: RequestValidationError):
    # Do not echo rejected inputs (which may contain pasted credentials).
    return error("invalid_request", "Request fields do not match the API contract.", 422)

@app.exception_handler(ValueError)
async def value_error(request: Request, exc: ValueError):
    return error("invalid_request", "The request failed source or contract validation.", 422)

def catalog():
    with CATALOG_LOCK:
        if app.state.catalog_bundle is None:
            from living_atlas.data import SourceCatalog
            from living_atlas.tools.evidence import EvidenceTools
            manifest = Path(os.environ.get("LIVING_ATLAS_SOURCE_MANIFEST", PROJECT_ROOT / "data/manifests/showcase.json"))
            cache_dir = Path(os.environ.get("SOURCE_CACHE_DIR", PROJECT_ROOT / "data/raw/flyaoc"))
            source_catalog = SourceCatalog.from_manifest(manifest, cache_dir=cache_dir, download=False)
            app.state.catalog_bundle = (source_catalog, EvidenceTools(source_catalog))
        return app.state.catalog_bundle

def sources_ready():
    try:
        return catalog()
    except (OSError, ValueError, RuntimeError):
        return None

@lru_cache(maxsize=1)
def gene_resolver():
    from living_atlas.tools.identity import GeneResolver
    return GeneResolver.from_file(PROJECT_ROOT / "data/manifests/gene_aliases.json")

@lru_cache(maxsize=2)
def ontology_resolver(ontology: str):
    from living_atlas.tools.ontology import OntologyResolver
    manifest = Path(os.environ.get("LIVING_ATLAS_SOURCE_MANIFEST", PROJECT_ROOT / "data/manifests/showcase.json"))
    cache_dir = Path(os.environ.get("SOURCE_CACHE_DIR", PROJECT_ROOT / "data/raw/flyaoc"))
    return OntologyResolver.from_manifest(manifest, cache_dir=cache_dir, ontologies=(ontology,))

@app.get("/tools/resolve-gene")
def resolve_gene(mention: str = Query(min_length=1, max_length=200),
                 taxon: str = Query("NCBITaxon:7227", max_length=100)):
    return gene_resolver().resolve_gene(mention, taxon)

@app.get("/tools/resolve-term")
def resolve_term(mention: str = Query(min_length=1, max_length=300),
                 ontology: Literal["FBbt", "FBdv"] = "FBbt"):
    try:
        return ontology_resolver(ontology).resolve_term(mention, ontology)
    except OSError:
        return error("ontology_import_required", "Import the pinned ontology files with --download --ontologies before resolving terms.", 409)

@app.get("/health")
def health():
    return {"status": "ok", "storage": app.state.repo.ping(), "schema_version": 1,
            "model_adapter": app.state.model_adapter.status(),
            "demo_source_withdrawal": os.environ.get("ENABLE_DEMO_SOURCE_WITHDRAWAL", "").lower() == "true",
            "scientific_workflow": "not_configured"}

@app.post("/runs", response_model=RunSnapshot, status_code=201)
def create_run(body: CreateRun):
    operation_id = body.operation_id or "create_" + uuid.uuid4().hex
    run_id = body.run_id or "run_" + sha256(operation_id.encode()).hexdigest()[:24]
    if body.mode == "fixture":
        seed = availability_fixture(run_id)
    else:
        loaded = sources_ready()
        if loaded is None:
            return error("source_import_required",
                         "Import the pinned showcase sources using the documented source import command.", 409)
        source_catalog, _ = loaded
        seed = {"sources": source_catalog.sources, "chunks": source_catalog.chunks}
    app.state.repo.create_run(
        run_id, mode=body.mode, operation_id=operation_id, **seed,
        metadata={"label": "Synthetic engineering fixture" if body.mode == "fixture" else "Imported source workspace",
                  "scientific_workflow": "not_configured"},
    )
    return public_snapshot(app.state.repo.snapshot(run_id))

@app.get("/runs/{run_id}/snapshot", response_model=RunSnapshot)
def snapshot(run_id: str):
    return public_snapshot(app.state.repo.snapshot(run_id))

@app.get("/runs/{run_id}/events", response_model=EventPage)
def events(run_id: str, after: int = Query(0, ge=0), limit: int = Query(500, ge=1, le=1000)):
    page = app.state.repo.events(run_id, after=after, limit=limit)
    page["events"] = [public_event(event) for event in page["events"]]
    return page

@app.get("/runs/{run_id}/evidence/{evidence_id}", response_model=EvidenceDetail)
def evidence_detail(run_id: str, evidence_id: str):
    detail = app.state.repo.evidence(run_id, evidence_id)
    detail["available"] = detail.get("available", detail.get("source_state", {}).get("available", False))
    return EvidenceDetail.model_validate(detail)

@app.get("/runs/{run_id}/evaluations", response_model=list[Evaluation])
def evaluations(run_id: str):
    return app.state.repo.snapshot(run_id)["evaluations"]

@app.post("/runs/{run_id}/demo-events/source-withdrawal")
def source_withdrawal(run_id: str, body: SourceChange):
    if os.environ.get("ENABLE_DEMO_SOURCE_WITHDRAWAL", "").lower() != "true":
        return error("demo_disabled", "Source availability simulation is disabled on this server.", 403)
    result = app.state.repo.change_availability(run_id, **body.model_dump())
    if "events" in result:
        result["events"] = [public_event(event) for event in result["events"]]
    return result

@app.post("/runs/{run_id}/resume")
def resume(run_id: str):
    app.state.repo.snapshot(run_id)
    return error("workflow_not_configured",
                 "This workspace persists evidence. The checkpointed scientific worker is not implemented yet.", 501)

@app.get("/runs/{run_id}/export")
def export(run_id: str):
    snapshot = public_snapshot(app.state.repo.snapshot(run_id))
    # Metadata and references only: source corpus and credentials are not exported.
    body = json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n"
    return Response(body, media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="living-atlas-dossier.json"'})

def source_run(run_id):
    run = app.state.repo.snapshot(run_id)
    if run["mode"] != "sources":
        return error("source_mode_required", "Open an imported source workspace to browse paper passages.", 409)
    loaded = sources_ready()
    if loaded is None:
        return error("source_import_required", "The pinned source cache is unavailable.", 409)
    keys = lambda sources: {(row["source_id"], row["source_version"]) for row in sources}
    if keys(run["sources"]) != keys(loaded[0].sources):
        return error("source_manifest_changed", "This run uses different pinned sources. Restore its source manifest to browse new passages.", 409)
    return None

@app.get("/runs/{run_id}/search")
def search(run_id: str, gene_id: str = Query(min_length=1, max_length=200),
           query: str = Query("", max_length=500), cursor: str | None = None):
    invalid = source_run(run_id)
    if invalid is not None:
        return invalid
    loaded = sources_ready()
    if loaded is None:
        return error("source_import_required", "The pinned source cache is unavailable.", 409)
    if not gene_id.startswith("FBgn"):
        identity = gene_resolver().resolve_gene(gene_id)
        if identity["status"] != "resolved":
            return JSONResponse(ErrorEnvelope(
                code="gene_" + identity["status"],
                message="Gene mention is unresolved or ambiguous. Select an explicit FlyBase gene ID.",
                details={"candidates": identity.get("candidates", [])},
            ).model_dump(), status_code=422)
        gene_id = identity["candidates"][0]["gene_id"]
    states = app.state.repo.snapshot(run_id)["source_state"]
    available = {(row["source_id"], row["source_version"]) for row in states if row["available"]}
    return loaded[1].search_evidence(gene_id, query, cursor=cursor, available_sources=available)

@app.get("/runs/{run_id}/chunks/{chunk_id}")
def read_chunk(run_id: str, chunk_id: str, source_version: str, cursor: str | None = None):
    invalid = source_run(run_id)
    if invalid is not None:
        return invalid
    loaded = sources_ready()
    if loaded is None:
        return error("source_import_required", "The pinned source cache is unavailable.", 409)
    try:
        chunk = loaded[0].get_chunk(chunk_id, source_version)
    except ValueError as exc:
        # Preserve version/hash failures as validation errors; only absence is 404.
        if str(exc) == "Unknown chunk":
            return error("not_found", "Source chunk not found.", 404)
        raise
    states = app.state.repo.snapshot(run_id)["source_state"]
    if not any(row["available"] and row["source_id"] == chunk["source_id"]
               and row["source_version"] == source_version for row in states):
        return error("source_unavailable", "This source is withdrawn. Previously accepted evidence remains inspectable.", 409)
    return loaded[1].read_chunk(chunk_id, source_version, cursor)

@app.post("/runs/{run_id}/evidence")
def record_evidence(run_id: str, body: RecordEvidence):
    invalid = source_run(run_id)
    if invalid is not None:
        return invalid
    loaded = sources_ready()
    if loaded is None:
        return error("source_import_required", "The pinned source cache is unavailable.", 409)
    rows = loaded[1].record_evidence(body.span_ids, body.source_version)
    result = app.state.repo.accept_operation(
        run_id, body.operation_id, payload=body.model_dump(),
        upserts={"evidence": rows},
    )
    result["events"] = [public_event(event) for event in result.get("events", [])]
    return result
