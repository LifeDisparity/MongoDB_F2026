import type { RunEvent, RunSnapshot } from '../contracts';

function replace<T>(rows: T[], value: T, key: (row: T) => string): T[] {
  const existing = rows.findIndex(row => key(row) === key(value));
  return (existing < 0 ? [...rows, value] : rows.map((row, i) => i === existing ? value : row)).sort((a, b) => key(a).localeCompare(key(b)));
}

export function emptySnapshot(snapshot: RunSnapshot): RunSnapshot {
  return { ...snapshot, last_sequence: 0, sources: [], source_state: [], evidence: [], claims: [], investigations: [], decisions: [], policies: [], evaluations: [] };
}

/** The same accepted-event reducer drives both the live graph and time replay. */
export function applyEvent(state: RunSnapshot, event: RunEvent): RunSnapshot {
  if (event.run_id !== state.run_id || event.sequence <= state.last_sequence) return state;
  if (event.sequence !== state.last_sequence + 1) throw new Error(`Event gap: waiting for event ${state.last_sequence + 1}.`);
  const payload = event.payload as Record<string, unknown>;
  let next = { ...state, last_sequence: event.sequence };
  switch (event.type as string) {
    case 'run.created':
      next = { ...next, ...(payload.snapshot ?? payload) as Partial<RunSnapshot>, run_id: state.run_id, last_sequence: event.sequence };
      break;
    case 'source.upserted':
      next.sources = replace(state.sources, payload as unknown as RunSnapshot['sources'][number], row => `${row.source_id}/${row.source_version}`);
      break;
    case 'source.availability_changed':
      next.source_state = replace(state.source_state, payload as unknown as RunSnapshot['source_state'][number], row => `${row.source_id}/${row.source_version}`);
      break;
    case 'evidence.upserted':
      next.evidence = replace(state.evidence, payload as unknown as RunSnapshot['evidence'][number], row => row.evidence_id);
      break;
    case 'claim.upserted':
      next.claims = replace(state.claims, payload as unknown as RunSnapshot['claims'][number], row => row.claim_id);
      break;
    case 'investigation.created':
    case 'investigation.updated':
    case 'worker.resumed':
      if (typeof payload.investigation_id === 'string') next.investigations = replace(state.investigations, payload as unknown as RunSnapshot['investigations'][number], row => row.investigation_id);
      break;
    case 'decision.recorded':
      next.decisions = replace(state.decisions, payload as unknown as RunSnapshot['decisions'][number], row => row.decision_id);
      break;
    case 'policy.proposed':
    case 'policy.promoted':
    case 'policy.rejected':
      next.policies = replace(state.policies, payload as unknown as RunSnapshot['policies'][number], row => row.policy_version);
      break;
    case 'evaluation.completed':
      next.evaluations = replace(state.evaluations, payload as unknown as RunSnapshot['evaluations'][number], row => row.evaluation_id);
      break;
  }
  return next;
}

/** Accept only a contiguous prefix. Missing sequences are fetched before advance. */
export function appendEvents(current: RunEvent[], incoming: RunEvent[]): RunEvent[] {
  const bySequence = new Map(current.map(event => [event.sequence, event]));
  const ids = new Map(current.map(event => [event.event_id, event.sequence]));
  for (const event of incoming) {
    if (event.sequence < 1 || !Number.isInteger(event.sequence)) throw new Error('The event stream contains an invalid sequence.');
    const existing = bySequence.get(event.sequence);
    if (existing && existing.event_id !== event.event_id) throw new Error('The event stream contains conflicting sequences.');
    if (ids.has(event.event_id) && ids.get(event.event_id) !== event.sequence) throw new Error('The event stream contains a reused event identity.');
    bySequence.set(event.sequence, event);
    ids.set(event.event_id, event.sequence);
  }
  const result: RunEvent[] = [];
  for (let sequence = 1; bySequence.has(sequence); sequence++) result.push(bySequence.get(sequence)!);
  return result;
}

export function replayThrough(snapshot: RunSnapshot, events: RunEvent[], sequence: number): RunSnapshot {
  return events.filter(event => event.sequence <= sequence).reduce(applyEvent, emptySnapshot(snapshot));
}

export function eventLabel(event?: RunEvent): string {
  if (!event) return 'Before the first recorded event';
  const labels: Record<string, string> = {
    'run.created': 'Investigation workspace created',
    'source.availability_changed': event.payload.available === false ? 'Source withdrawn · simulation' : 'Source availability restored · review required',
    'claim.upserted': `Claim ${String(event.payload.claim_id ?? '')} · ${String(event.payload.status ?? 'updated').replaceAll('_', ' ')}`,
    'evidence.upserted': 'Canonical evidence recorded',
    'decision.recorded': 'Investigation decision recorded',
    'worker.resumed': 'Worker resumed',
    'policy.proposed': 'Harness policy proposed',
    'policy.promoted': 'Harness policy promoted',
    'policy.rejected': 'Harness policy rejected',
    'evaluation.completed': 'Evaluation recorded',
    'run.completed': 'Run completed',
  };
  return labels[event.type] ?? event.type.replaceAll('.', ' · ').replaceAll('_', ' ');
}
