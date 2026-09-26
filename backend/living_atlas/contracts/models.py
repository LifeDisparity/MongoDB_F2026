"""Living Atlas wire contracts v1; requests are strict and responses redact extras."""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

class WireModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class SourceSnapshot(WireModel):
    source_id: str
    source_version: str
    title: str
    original_url: str
    pmcid: str | None = None
    content_sha256: str
    license_id: str | None = None
    license_url: str | None = None
    distribution_status: str
    sections: list[dict[str, Any]] = Field(default_factory=list)
    gene_ids: list[str] = Field(default_factory=list)

class SourceAvailability(WireModel):
    run_id: str
    source_id: str
    source_version: str
    available: bool
    revision: int = Field(ge=0)
    availability_history: list[dict[str, Any]] = Field(default_factory=list)

class Evidence(WireModel):
    evidence_id: str
    source_id: str
    source_version: str
    chunk_id: str
    span_id: str
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)
    quote_sha256: str

class Qualifiers(WireModel):
    stage_id: str | None = None
    stage_label: str | None = None
    cell_class: str | None = None
    assay: str | None = None
    intervention: str | None = None
    polarity: Literal["observed", "not_observed", "uncertain"]
    scope_notes: str

class Claim(WireModel):
    claim_id: str
    run_id: str
    revision: int = Field(ge=0)
    gene_id: str
    relation: Literal["expressed_in", "perturbation_observation", "involved_in"]
    object_id: str | None = None
    object_label: str
    qualifiers: Qualifiers
    evidence_ids: list[str]
    conflicting_evidence_ids: list[str] = Field(default_factory=list)
    usable_evidence_ids: list[str] = Field(default_factory=list)
    usable_conflicting_evidence_ids: list[str] = Field(default_factory=list)
    status: Literal["candidate", "supported", "conflicting", "needs_review", "unsupported"]
    policy_version: str

class Decision(WireModel):
    decision_id: str
    investigation_id: str
    question: str
    selected_action: str
    reason_summary: str
    decision_target: str
    decision_it_can_change: str
    evidence_ids: list[str] = Field(default_factory=list)
    stopping_condition: str
    budget: dict[str, Any]

class Investigation(WireModel):
    investigation_id: str
    run_id: str
    question: str
    decision_target: str
    workflow_id: str
    policy_version: str
    budget: dict[str, Any]
    frontier: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "pending"
    gene_id: str | None = None

class Policy(WireModel):
    policy_version: str
    parent_policy_version: str | None = None
    configuration: dict[str, Any]
    configuration_sha256: str
    proposed_by: str
    development_failure_ids: list[str] = Field(default_factory=list)
    evaluation_id: str | None = None
    selection_status: str

class Evaluation(WireModel):
    evaluation_id: str
    run_id: str
    arm: Literal["P0", "H0", "H1"]
    split: Literal["development", "validation", "final_test"]
    manifest_sha256: str
    model_id: str
    policy_sha256: str
    case_ids: list[str]
    correct_count: int
    decision_count: int
    supported_count: int
    support_count: int
    reference_hits: int
    reference_count: int
    usage: dict[str, Any]
    failures: list[dict[str, Any]] = Field(default_factory=list)
    integrity_outcomes: dict[str, Any]
    prediction_sha256: str

class RunSnapshot(WireModel):
    schema_version: Literal[1] = 1
    run_id: str
    mode: Literal["fixture", "sources", "live"]
    created_at: str
    last_sequence: int = Field(ge=0)
    sources: list[SourceSnapshot] = Field(default_factory=list)
    source_state: list[SourceAvailability] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    investigations: list[Investigation] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    policies: list[Policy] = Field(default_factory=list)
    evaluations: list[Evaluation] = Field(default_factory=list)

EventType = Literal[
    "run.created", "investigation.created", "investigation.updated", "decision.recorded",
    "evidence.upserted", "claim.upserted", "source.availability_changed",
    "worker.resumed", "policy.proposed", "evaluation.completed",
    "policy.promoted", "policy.rejected", "run.completed",
]

class RunEvent(WireModel):
    schema_version: Literal[1] = 1
    run_id: str
    sequence: int = Field(ge=1)
    event_id: str
    operation_id: str
    occurred_at: str
    type: EventType
    payload: dict[str, Any]

class EventPage(WireModel):
    run_id: str
    events: list[RunEvent]
    last_sequence: int = Field(ge=0)
    has_more: bool

class EvidenceDetail(Evidence):
    quote: str
    source: SourceSnapshot
    available: bool

class ErrorEnvelope(WireModel):
    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] | None = None

class CreateRun(RequestModel):
    mode: Literal["fixture", "sources"] = "fixture"
    run_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,100}$")
    operation_id: str | None = Field(default=None, min_length=1, max_length=200)

class SourceChange(RequestModel):
    source_id: str = Field(min_length=1, max_length=200)
    source_version: str = Field(min_length=1, max_length=200)
    available: bool = False
    operation_id: str = Field(min_length=1, max_length=200)
    reason: str = Field(default="User-requested availability simulation", max_length=1000)
