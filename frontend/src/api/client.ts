import type { EvidenceDetail, RunEvent, RunSnapshot } from '../contracts';

const API = '/api';

export interface SearchMatch {
  chunk_id: string; source_id: string; source_version: string;
  section_type: string; section_title: string; score: number;
  preview: string; preview_truncated: boolean;
}
export interface SourceSpan {
  span_id: string; text: string; char_start: number; char_end: number;
}
export interface ChunkPage { spans: SourceSpan[]; next_cursor: string | null; complete: boolean }

export class ApiError extends Error {
  constructor(message: string, public code: string, public retryable: boolean) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body.detail ?? body;
    throw new ApiError(detail.message ?? `Request failed (${response.status})`, detail.code ?? 'request_failed', Boolean(detail.retryable));
  }
  return response.json() as Promise<T>;
}

export const api = {
  createRun: (mode: 'fixture' | 'sources') => request<RunSnapshot>('/runs', { method: 'POST', body: JSON.stringify({ mode }) }),
  snapshot: (runId: string) => request<RunSnapshot>(`/runs/${encodeURIComponent(runId)}/snapshot`),
  events: (runId: string, after: number) => request<{ events: RunEvent[]; last_sequence: number; has_more: boolean }>(`/runs/${encodeURIComponent(runId)}/events?after=${after}&limit=250`),
  evidence: (runId: string, evidenceId: string) => request<EvidenceDetail>(`/runs/${encodeURIComponent(runId)}/evidence/${encodeURIComponent(evidenceId)}`),
  search: (runId: string, geneId: string, query: string, cursor?: string) => request<{ matches: SearchMatch[]; next_cursor: string | null; complete: boolean }>(`/runs/${encodeURIComponent(runId)}/search?gene_id=${encodeURIComponent(geneId)}&query=${encodeURIComponent(query)}${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`),
  chunk: (runId: string, chunkId: string, sourceVersion: string, cursor?: string) => request<ChunkPage>(`/runs/${encodeURIComponent(runId)}/chunks/${encodeURIComponent(chunkId)}?source_version=${encodeURIComponent(sourceVersion)}${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`),
  pinEvidence: (runId: string, spanId: string, sourceVersion: string) => request<unknown>(`/runs/${encodeURIComponent(runId)}/evidence`, { method: 'POST', body: JSON.stringify({ span_ids: [spanId], source_version: sourceVersion, operation_id: crypto.randomUUID() }) }),
  changeSource: (runId: string, sourceId: string, sourceVersion: string, available: boolean) => request<unknown>(`/runs/${encodeURIComponent(runId)}/demo-events/source-withdrawal`, {
    method: 'POST', body: JSON.stringify({ source_id: sourceId, source_version: sourceVersion, available, operation_id: crypto.randomUUID(), reason: available ? 'User restored source in labeled availability simulation' : 'User withdrew source in labeled availability simulation' }),
  }),
  exportUrl: (runId: string) => `${API}/runs/${encodeURIComponent(runId)}/export`,
};
