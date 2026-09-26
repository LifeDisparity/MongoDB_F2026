import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import { EvidenceGraph, type Selection } from '../graph/EvidenceGraph';
import { Inspector } from '../evidence/Inspector';
import { useRun } from '../replay/useRun';
import { Timeline } from '../replay/Timeline';
import { Icon } from './Icon';

function initialRun() {
  return new URLSearchParams(window.location.search).get('run') ?? window.localStorage.getItem('living-atlas-run');
}

export function App() {
  const [runId, setRunId] = useState<string | null>(initialRun);
  const [selection, setSelection] = useState<Selection>(null);
  const [showStart, setShowStart] = useState(!runId);
  const [creating, setCreating] = useState<string | null>(null);
  const [openId, setOpenId] = useState('');
  const [actionError, setActionError] = useState<string | null>(null);
  const startDialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (!showStart || !startDialog.current) return;
    const dialog = startDialog.current;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialog.showModal();
    return () => { dialog.close(); if (opener?.isConnected) opener.focus(); };
  }, [showStart]);
  const run = useRun(runId);
  const snapshot = run.snapshot;
  const openRun = (id: string) => {
    const cleaned = id.trim();
    if (!cleaned) return;
    setRunId(cleaned); setShowStart(false); setSelection(null); setActionError(null);
    window.localStorage.setItem('living-atlas-run', cleaned);
    const url = new URL(window.location.href); url.searchParams.set('run', cleaned); window.history.replaceState({}, '', url);
  };
  const create = async (mode: 'fixture' | 'sources') => {
    setCreating(mode); setActionError(null);
    try { const created = await api.createRun(mode); openRun(created.run_id); }
    catch (error) { setActionError(error instanceof Error ? error.message : 'Unable to create this run.'); }
    finally { setCreating(null); }
  };
  const currentEvent = run.events.find(event => event.sequence === run.cursor);
  const changedIds = currentEvent?.type === 'claim.upserted' ? [String(currentEvent.payload.claim_id)] : [];
  const supportCount = snapshot?.claims.filter(claim => claim.status === 'supported').length ?? 0;
  const reviewCount = snapshot?.claims.filter(claim => ['unsupported', 'needs_review', 'conflicting'].includes(claim.status)).length ?? 0;

  return <div className="atlas-app">
    <header className="topbar"><a className="brand" href={window.location.pathname} onClick={event => { event.preventDefault(); setShowStart(true); }}><span className="brand-symbol"><Icon name="atlas" size={28} /></span><span>Living <strong>Atlas</strong></span><span className="brand-divider" /><span className="brand-caption">SCIENTIFIC MEMORY</span></a><div className="topbar-right"><span className="workspace-label"><span className="signal-dot" />Research workspace</span><button className="button subtle" onClick={() => setShowStart(true)}><Icon name="plus" size={15} />New run</button>{runId && <a className="button secondary" href={api.exportUrl(runId)} download={`living-atlas-${runId}.json`}><Icon name="download" size={15} />Export dossier</a>}</div></header>
    <div className="runbar"><div className="run-breadcrumb"><Icon name="branch" size={16} /><strong>Evidence atlas</strong><span>/</span><span>{runId ? `Run ${runId.slice(0, 12)}` : 'New investigation'}</span></div><div className="runbar-status">{run.loading ? <span>Connecting to the record…</span> : runId ? <><span className={`connection ${run.connected ? '' : 'disconnected'}`}><span className="signal-dot" />{run.connected ? 'Connected' : 'Reconnecting'}</span><span className={`mode-badge ${run.mode.toLowerCase()}`}>{run.mode}</span></> : <span>Evidence first. Always.</span>}</div></div>
    {snapshot && <div className={`run-notice ${snapshot.mode === 'fixture' ? 'fixture-notice' : ''}`}><Icon name={snapshot.mode === 'fixture' ? 'warning' : 'book'} size={14} /><span>{snapshot.mode === 'fixture' ? <><strong>Synthetic engineering fixture</strong><span className="notice-separator">·</span>Demonstrates support dependencies and replay. No biological findings or measured model results.</> : <><strong>Imported scientific sources</strong><span className="notice-separator">·</span>{snapshot.claims.length ? 'Inspect accepted claims and their evidence.' : snapshot.investigations.length ? 'No claims accepted yet. Inspect the recorded investigation state.' : 'Source provenance is available. Real model investigation has not yet run.'}</>}</span></div>}
    {run.error && !showStart && <div className="connection-error" role="alert"><Icon name="warning" size={16} /><span>{run.error}</span><button onClick={() => void run.refresh()}>Retry</button><button onClick={() => setShowStart(true)}>Open another run</button></div>}
    <main className="workspace">
      <section className="graph-region" aria-label="Atlas workspace"><div className="graph-heading"><div><span className="eyebrow">Connected evidence</span><h1>The atlas, in context.</h1></div><div className="graph-counts">{snapshot ? <><span><i className="legend-dot cyan" />{supportCount} supported</span><span><i className="legend-dot amber" />{reviewCount} require review</span></> : <span>{run.loading ? 'Reading recorded state…' : 'No recorded run loaded'}</span>}</div></div>
        {snapshot ? <EvidenceGraph snapshot={snapshot} selection={selection} onSelect={setSelection} changedIds={changedIds} /> : <div className="graph-loading"><div className="atlas-watermark"><Icon name="atlas" size={120} /></div><p>{run.loading ? 'Reconstructing the recorded atlas…' : run.error ? 'The atlas will appear when the run reconnects.' : 'A living map of what the evidence says.'}</p></div>}
        <div className="graph-legend"><span><i className="legend-line" />Supported relation</span><span><i className="legend-line dotted" />Unresolved / unavailable</span><span><Icon name="book" size={12} />Original source</span></div>
      </section>
      {snapshot ? <Inspector snapshot={snapshot} selection={selection} onSelect={setSelection} mode={run.mode} onChanged={run.refresh} /> : <aside className="inspector empty-inspector"><span className="eyebrow">Traceable by design</span><h2>Evidence gives<br />the map meaning.</h2><p>Inspect a claim to see the experiment, the passage, and the source behind it.</p><div className="small-note"><Icon name="shield" size={20} /><p>Original evidence remains available through every change.</p></div></aside>}
    </main>
    <Timeline events={run.events} cursor={run.cursor} lastSequence={run.lastSequence} mode={run.mode} playing={run.playing} seek={run.seek} goLive={run.goLive} togglePlay={run.togglePlay} />
    {showStart && <dialog ref={startDialog} className="start-overlay" aria-labelledby="start-title" onCancel={() => setShowStart(false)}><section className="start-dialog"><div className="dialog-top"><span className="brand-symbol"><Icon name="atlas" size={30} /></span><button className="icon-button" aria-label="Close new run dialog" onClick={() => setShowStart(false)}><Icon name="close" /></button></div><span className="eyebrow">Welcome to Living Atlas</span><h1 id="start-title">Science leaves a trail.<br /><em>Keep it connected.</em></h1><p className="start-intro">Explore an inspectable evidence graph, follow support back to its source, and replay how the record changed.</p><div className="start-options"><button className="start-option" disabled={Boolean(creating)} onClick={() => void create('fixture')}><span className="option-icon cyan"><Icon name="branch" size={23} /></span><strong>Explore dependency demo <Icon name="arrow" size={18} /></strong><p>A labeled synthetic run with three claims. Withdraw a source and watch only its dependents change.</p><span className="option-label">{creating === 'fixture' ? 'Creating run…' : 'SYNTHETIC ENGINEERING FIXTURE'}</span></button><button className="start-option" disabled={Boolean(creating)} onClick={() => void create('sources')}><span className="option-icon violet"><Icon name="book" size={23} /></span><strong>Open scientific sources <Icon name="arrow" size={18} /></strong><p>Inspect imported papers, immutable source versions, and article rights. Model investigation is pending.</p><span className="option-label">{creating === 'sources' ? 'Importing sources…' : 'REAL SOURCE PROVENANCE'}</span></button></div><form className="open-run-form" onSubmit={event => { event.preventDefault(); openRun(openId); }}><label htmlFor="run-id">Resume an existing record</label><div><input id="run-id" placeholder="Paste a run ID" value={openId} onChange={event => setOpenId(event.target.value)} /><button className="button secondary" disabled={!openId.trim()}>Open run <Icon name="arrow" size={14} /></button></div></form>{actionError && <p className="inline-error" role="alert">{actionError}</p>}<div className="start-footer"><Icon name="shield" size={14} />No invented findings. Every visible change has a recorded event.</div></section></dialog>}
  </div>;
}
