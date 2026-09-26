import { useEffect, useState } from 'react';
import type { EvidenceDetail, RunSnapshot, SourceSnapshot } from '../contracts';
import { api } from '../api/client';
import { Icon } from '../app/Icon';
import { relationLabel, statusLabel, type Selection } from '../graph/EvidenceGraph';
import { PassageBrowser } from './PassageBrowser';
import { HarnessPanel } from '../policy/HarnessPanel';

function Version({ value }: { value: string }) {
  return <code title={value}>{value.length > 24 ? `${value.slice(0, 12)}…${value.slice(-8)}` : value}</code>;
}

function SourceDetails({ source, snapshot, mode, onChanged }: { source: SourceSnapshot; snapshot: RunSnapshot; mode: 'LIVE' | 'REPLAY'; onChanged: () => Promise<void> }) {
  const availability = snapshot.source_state.find(row => row.source_id === source.source_id && row.source_version === source.source_version);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const available = availability?.available ?? false;
  const toggle = async () => {
    setPending(true); setError(null);
    try { await api.changeSource(snapshot.run_id, source.source_id, source.source_version, !available); await onChanged(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'The source could not be updated.'); }
    finally { setPending(false); }
  };
  return <>
    <div className="source-reference"><Icon name="book" size={20} /><div><strong>{source.title}</strong><a href={source.original_url} target="_blank" rel="noreferrer">Open original source <Icon name="external" size={12} /></a></div></div>
    <dl className="metadata-list"><div><dt>Source</dt><dd>{source.pmcid ?? source.source_id}</dd></div><div><dt>Version</dt><dd><Version value={source.source_version} /></dd></div><div><dt>Rights</dt><dd>{source.license_url ? <a href={source.license_url} target="_blank" rel="noreferrer">{source.license_id ?? 'Source terms'} <Icon name="external" size={11} /></a> : source.license_id ?? 'See original source'}</dd></div><div><dt>Distribution</dt><dd>{source.distribution_status.replaceAll('_', ' ')}</dd></div><div><dt>Content hash</dt><dd><Version value={source.content_sha256} /></dd></div></dl>
    <div className={`availability-card ${available ? '' : 'withdrawn'}`}><div><Icon name={available ? 'shield' : 'warning'} size={16} /><strong>{available ? 'Available as support' : 'Unavailable as support'}</strong></div><p>{mode === 'REPLAY' ? 'Availability at this point in the recorded history.' : 'Availability applies only to this run. The original source and evidence are preserved.'}</p></div>
    <div className="simulation-block"><span className="eyebrow">Availability simulation</span><p>{available ? 'Withdraw this source to inspect which claims lose support.' : 'Restore availability. Affected claims still require scientific review.'}</p><button className="button secondary full" onClick={() => void toggle()} disabled={pending || mode === 'REPLAY'}><Icon name={available ? 'branch' : 'plus'} size={15} />{pending ? 'Updating…' : available ? 'Simulate source withdrawal' : 'Restore source availability'}</button>{mode === 'REPLAY' && <small>Return to live to change source availability.</small>}{error && <p className="inline-error" role="alert">{error}</p>}</div>
  </>;
}

export function Inspector({ snapshot, selection, onSelect, mode, onChanged }: { snapshot: RunSnapshot; selection: Selection; onSelect: (selection: Selection) => void; mode: 'LIVE' | 'REPLAY'; onChanged: () => Promise<void> }) {
  const claim = selection?.kind === 'claim' ? snapshot.claims.find(row => row.claim_id === selection.id) : undefined;
  const source = selection?.kind === 'source' ? snapshot.sources.find(row => row.source_id === selection.id && row.source_version === selection.version) : undefined;
  const evidenceIds = claim ? [...claim.evidence_ids, ...claim.conflicting_evidence_ids] : [];
  const [evidenceIndex, setEvidenceIndex] = useState(0);
  const [detail, setDetail] = useState<EvidenceDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const evidenceId = evidenceIds[Math.min(evidenceIndex, Math.max(evidenceIds.length - 1, 0))];
  useEffect(() => { setEvidenceIndex(0); }, [claim?.claim_id]);
  useEffect(() => {
    let cancelled = false;
    setDetail(null); setError(null);
    if (!evidenceId) { setLoading(false); return; }
    setLoading(true);
    api.evidence(snapshot.run_id, evidenceId).then(value => { if (!cancelled) setDetail(value); }).catch(reason => { if (!cancelled) setError(reason instanceof Error ? reason.message : 'Evidence could not be loaded.'); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [snapshot.run_id, evidenceId]);
  const decision = claim ? snapshot.decisions.find(row => row.decision_target === claim.claim_id || row.evidence_ids.some(id => evidenceIds.includes(id))) : undefined;
  const investigation = decision ? snapshot.investigations.find(row => row.investigation_id === decision.investigation_id) : claim ? snapshot.investigations.find(row => row.gene_id === claim.gene_id) : undefined;
  const usable = claim?.usable_evidence_ids.includes(evidenceId) || claim?.usable_conflicting_evidence_ids.includes(evidenceId);
  const conflicting = claim?.conflicting_evidence_ids.includes(evidenceId);

  return <aside className="inspector" aria-label="Evidence inspector"><div className="inspector-heading"><span><Icon name={source ? 'book' : 'search'} size={16} />{claim ? 'Evidence inspector' : source ? 'Source provenance' : 'Atlas overview'}</span>{selection && <button className="icon-button" onClick={() => onSelect(null)} aria-label="Close inspector selection"><Icon name="close" size={16} /></button>}</div><div className="inspector-body">
    {claim ? <>
      <div className="inspector-kicker"><span className="eyebrow">{relationLabel(claim.relation)} · {claim.claim_id}</span><span className={`status status-${claim.status}`}>{statusLabel(claim.status)}</span></div>
      <h2>{claim.object_label}</h2>
      <p className="inspector-subtitle">{claim.gene_id} <span>·</span> revision {claim.revision}</p>
      <dl className="qualifier-list">{[['Cell class', claim.qualifiers.cell_class], ['Intervention', claim.qualifiers.intervention], ['Stage', claim.qualifiers.stage_label ?? claim.qualifiers.stage_id], ['Assay', claim.qualifiers.assay], ['Observation', statusLabel(claim.qualifiers.polarity)]].filter(([, value]) => value).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
      {claim.qualifiers.scope_notes && <div className="scope-note"><Icon name="shield" size={16} /><p>{claim.qualifiers.scope_notes}</p></div>}
      {(decision || investigation) && <section className="inspector-section"><h3>Investigation</h3><p className="question">{decision?.question ?? investigation?.question}</p>{decision && <><span className="eyebrow">Chosen follow-up</span><p>{decision.selected_action}</p><p className="muted">{decision.reason_summary}</p><span className="eyebrow">Decision it can change</span><p>{decision.decision_it_can_change}</p><span className="eyebrow">Stopping condition</span><p>{decision.stopping_condition}</p></>}</section>}
      <section className="inspector-section evidence-section"><div className="section-title"><h3>Original evidence</h3><span>{evidenceIds.length} {evidenceIds.length === 1 ? 'reference' : 'references'}</span></div>
        {evidenceIds.length > 1 && <div className="evidence-tabs" role="group" aria-label="Evidence references">{evidenceIds.map((id, i) => <button key={id} className={evidenceId === id ? 'active' : ''} onClick={() => setEvidenceIndex(i)}>{i + 1}{claim.conflicting_evidence_ids.includes(id) ? ' · conflict' : ''}</button>)}</div>}
        {loading && <div className="loading-passage">Retrieving canonical passage…</div>}
        {error && <div className="inline-error" role="alert">{error}</div>}
        {!evidenceIds.length && <p className="muted">No evidence has been accepted for this claim.</p>}
        {detail && <><div className={`passage-label ${usable ? '' : 'muted'}`}><Icon name={usable ? 'check' : 'warning'} size={13} />{conflicting ? 'Conflicting evidence' : 'Canonical source passage'}{!usable && ' · unavailable'}</div><blockquote>{detail.quote}</blockquote><div className="passage-footer"><span>Server-reconstructed span</span><code>{detail.start_offset}–{detail.end_offset}</code></div><SourceDetails key={`${detail.source_id}/${detail.source_version}`} source={detail.source} snapshot={snapshot} mode={mode} onChanged={onChanged} /></>}
      </section>
    </> : source ? <><span className="eyebrow">Immutable scientific record</span><h2 className="source-detail-title">{source.pmcid ?? source.source_id}</h2><SourceDetails key={`${source.source_id}/${source.source_version}`} source={source} snapshot={snapshot} mode={mode} onChanged={onChanged} />{snapshot.mode !== 'fixture' && <PassageBrowser key={`${snapshot.run_id}/${source.source_id}/${source.source_version}`} source={source} snapshot={snapshot} mode={mode} onChanged={onChanged} />}<section className="inspector-section"><h3>Linked claims</h3>{snapshot.claims.filter(row => [...row.evidence_ids, ...row.conflicting_evidence_ids].some(id => snapshot.evidence.some(evidence => evidence.evidence_id === id && evidence.source_id === source.source_id && evidence.source_version === source.source_version))).map(row => <button className="source-list-row" key={row.claim_id} onClick={() => onSelect({ kind: 'claim', id: row.claim_id })}><span>{row.object_label}</span><Icon name="chevron" size={15} /></button>)}{!snapshot.claims.length && <p className="muted">No scientific claims have been accepted. Source import does not constitute model investigation.</p>}</section></> : <>
      <div className="overview-mark"><Icon name="atlas" size={34} /></div><span className="eyebrow">A map with a memory</span><h2>Every claim.<br />Back to its evidence.</h2><p className="overview-intro">Select a branch to inspect its experimental scope, original passage, and current support.</p>
      <div className="overview-stats"><div><strong>{snapshot.claims.length}</strong><span>claims</span></div><div><strong>{snapshot.sources.length}</strong><span>sources</span></div><div><strong>{snapshot.investigations.length}</strong><span>investigations</span></div></div>
      <section className="inspector-section"><h3>Source library</h3>{snapshot.sources.map(row => <button className="source-list-row" key={`${row.source_id}/${row.source_version}`} onClick={() => onSelect({ kind: 'source', id: row.source_id, version: row.source_version })}><Icon name="book" size={16} /><span><strong>{row.pmcid ?? row.source_id}</strong><small>{row.title}</small></span><Icon name="chevron" size={14} /></button>)}{!snapshot.sources.length && <p className="muted">No sources existed at this point in the run.</p>}</section>
      <div className="small-note"><Icon name="shield" size={16} /><p>Source availability changes support. It does not change biological truth.</p></div>
    </>}
    <HarnessPanel snapshot={snapshot} />
    </div></aside>;
}
