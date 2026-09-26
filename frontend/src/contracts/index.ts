/** Living Atlas snake_case public contracts v1. Keep aligned with FastAPI models. */
export const SCHEMA_VERSION = 1 as const;
export type RunMode = 'fixture' | 'sources' | 'live';
export type ClaimStatus = 'candidate' | 'supported' | 'conflicting' | 'needs_review' | 'unsupported';
export interface SourceSnapshot {
  source_id: string; source_version: string; title: string; original_url: string;
  pmcid?: string | null; content_sha256: string; license_id?: string | null;
  license_url?: string | null; distribution_status: string;
  sections: Record<string, unknown>[]; gene_ids?: string[];
}
export interface SourceAvailability {
  run_id: string; source_id: string; source_version: string; available: boolean;
  revision: number; availability_history: Record<string, unknown>[];
}
export interface Evidence {
  evidence_id: string; source_id: string; source_version: string; chunk_id: string;
  span_id: string; start_offset: number; end_offset: number; quote_sha256: string;
}
export interface Qualifiers {
  stage_id?: string | null; stage_label?: string | null; cell_class?: string | null;
  assay?: string | null; intervention?: string | null;
  polarity: 'observed' | 'not_observed' | 'uncertain'; scope_notes: string;
}
export interface Claim {
  claim_id: string; run_id: string; revision: number; gene_id: string;
  relation: 'expressed_in' | 'perturbation_observation' | 'involved_in';
  object_id?: string | null; object_label: string; qualifiers: Qualifiers;
  evidence_ids: string[]; conflicting_evidence_ids: string[];
  usable_evidence_ids: string[]; usable_conflicting_evidence_ids: string[];
  status: ClaimStatus; policy_version: string;
}
export interface Investigation {
  investigation_id: string; run_id: string; question: string; decision_target: string;
  workflow_id: string; policy_version: string; budget: Record<string, unknown>;
  frontier: Record<string, unknown>[]; status: string; gene_id?: string | null;
}
export interface Decision {
  decision_id: string; investigation_id: string; question: string; selected_action: string;
  reason_summary: string; decision_target: string; decision_it_can_change: string;
  evidence_ids: string[]; stopping_condition: string; budget: Record<string, unknown>;
}
export interface Policy {
  policy_version: string; parent_policy_version?: string | null;
  configuration: Record<string, unknown>; configuration_sha256: string;
  proposed_by: string; development_failure_ids: string[];
  evaluation_id?: string | null; selection_status: string;
}
export interface Evaluation {
  evaluation_id: string; run_id: string; arm: 'P0' | 'H0' | 'H1';
  split: 'development' | 'validation' | 'final_test'; manifest_sha256: string;
  model_id: string; policy_sha256: string; case_ids: string[];
  correct_count: number; decision_count: number; supported_count: number; support_count: number;
  reference_hits: number; reference_count: number; usage: Record<string, unknown>;
  failures: Record<string, unknown>[]; integrity_outcomes: Record<string, unknown>;
  prediction_sha256: string;
}
export interface RunSnapshot {
  schema_version: 1; run_id: string; mode: RunMode; created_at: string; last_sequence: number;
  sources: SourceSnapshot[]; source_state: SourceAvailability[]; evidence: Evidence[];
  claims: Claim[]; investigations: Investigation[]; decisions: Decision[];
  policies: Policy[]; evaluations: Evaluation[];
}
export type RunEventType =
  | 'run.created' | 'investigation.created' | 'decision.recorded' | 'evidence.upserted'
  | 'claim.upserted' | 'source.availability_changed' | 'worker.resumed' | 'policy.proposed'
  | 'evaluation.completed' | 'policy.promoted' | 'policy.rejected' | 'run.completed';
export interface RunEvent {
  schema_version: 1; run_id: string; sequence: number; event_id: string;
  operation_id: string; occurred_at: string; type: RunEventType;
  payload: Record<string, unknown>;
}
export interface EventPage { run_id: string; events: RunEvent[]; last_sequence: number; has_more: boolean }
export interface EvidenceDetail extends Evidence { quote: string; source: SourceSnapshot; available: boolean }
export interface ErrorEnvelope { code: string; message: string; retryable: boolean; details?: Record<string, unknown> | null }
