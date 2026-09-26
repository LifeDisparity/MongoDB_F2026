import { useState } from 'react';
import { api, type SearchMatch, type SourceSpan } from '../api/client';
import type { EvidenceDetail, RunSnapshot, SourceSnapshot } from '../contracts';
import { Icon } from '../app/Icon';

export function PassageBrowser({ source, snapshot, mode, onChanged }: { source: SourceSnapshot; snapshot: RunSnapshot; mode: 'LIVE' | 'REPLAY'; onChanged: () => Promise<void> }) {
  const [geneId, setGeneId] = useState(source.gene_ids?.[0] ?? '');
  const [query, setQuery] = useState('');
  const [matches, setMatches] = useState<SearchMatch[]>([]);
  const [searched, setSearched] = useState(false);
  const [searching, setSearching] = useState(false);
  const [searchCursor, setSearchCursor] = useState<string | null>(null);
  const [activeQuery, setActiveQuery] = useState({ geneId: '', query: '' });
  const [activeChunk, setActiveChunk] = useState<SearchMatch | null>(null);
  const [spans, setSpans] = useState<SourceSpan[]>([]);
  const [chunkCursor, setChunkCursor] = useState<string | null>(null);
  const [reading, setReading] = useState(false);
  const [pinning, setPinning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [acceptedDetail, setAcceptedDetail] = useState<EvidenceDetail | null>(null);
  const [openingEvidence, setOpeningEvidence] = useState<string | null>(null);
  const available = snapshot.source_state.find(row => row.source_id === source.source_id && row.source_version === source.source_version)?.available ?? false;
  const pinned = snapshot.evidence.filter(row => row.source_id === source.source_id && row.source_version === source.source_version);
  const visibleDetail = acceptedDetail && pinned.some(row => row.evidence_id === acceptedDetail.evidence_id) ? acceptedDetail : null;
  const inspect = async (evidenceId: string) => {
    setOpeningEvidence(evidenceId); setError(null); setAcceptedDetail(null);
    try { setAcceptedDetail(await api.evidence(snapshot.run_id, evidenceId)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to inspect this accepted evidence.'); }
    finally { setOpeningEvidence(null); }
  };
  const search = async (continuation = false) => {
    setSearching(true); setError(null);
    if (!continuation) { setMatches([]); setSpans([]); setActiveChunk(null); setSearchCursor(null); }
    const nextQuery = continuation ? activeQuery : { geneId: geneId.trim(), query: query.trim() };
    try {
      const page = await api.search(snapshot.run_id, nextQuery.geneId, nextQuery.query, continuation ? searchCursor ?? undefined : undefined);
      const selectedSource = page.matches.filter(row => row.source_id === source.source_id && row.source_version === source.source_version);
      setMatches(previous => continuation ? [...previous, ...selectedSource.filter(row => !previous.some(item => item.chunk_id === row.chunk_id))] : selectedSource);
      setSearchCursor(page.next_cursor); setActiveQuery(nextQuery); setSearched(true);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to search this source.'); }
    finally { setSearching(false); }
  };
  const read = async (match: SearchMatch, continuation = false) => {
    setReading(true); setError(null);
    if (!continuation) { setActiveChunk(match); setSpans([]); setChunkCursor(null); }
    try {
      const page = await api.chunk(snapshot.run_id, match.chunk_id, source.source_version, continuation ? chunkCursor ?? undefined : undefined);
      setSpans(previous => continuation ? [...previous, ...page.spans.filter(row => !previous.some(item => item.span_id === row.span_id))] : page.spans);
      setChunkCursor(page.next_cursor);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to read this source section.'); }
    finally { setReading(false); }
  };
  const pin = async (span: SourceSpan) => {
    setPinning(span.span_id); setError(null);
    try { await api.pinEvidence(snapshot.run_id, span.span_id, source.source_version); await onChanged(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to record this evidence.'); }
    finally { setPinning(null); }
  };

  return <section className="inspector-section passage-browser"><div className="section-title"><h3>Read original passages</h3><span>{pinned.length} pinned</span></div><p className="muted">Search this imported source and pin exact server-held spans. Reading or pinning a passage does not establish a scientific claim.</p>
    {!!pinned.length && <div className="accepted-evidence"><span className="eyebrow">Accepted evidence</span>{pinned.map((evidence, index) => <button className="source-list-row" key={evidence.evidence_id} onClick={() => void inspect(evidence.evidence_id)} disabled={Boolean(openingEvidence)}><Icon name="book" size={14} /><span><strong>{openingEvidence === evidence.evidence_id ? 'Opening passage…' : `Inspect pinned passage ${index + 1}`}</strong><small>Characters {evidence.start_offset}–{evidence.end_offset} · {available ? 'available' : 'source withdrawn'}</small></span><Icon name="chevron" size={12} /></button>)}{visibleDetail && <div className="read-span accepted-passage"><span className="passage-label"><Icon name="shield" size={12} />Canonical accepted passage · {mode === 'REPLAY' ? 'historical record' : 'immutable record'}</span><blockquote>{visibleDetail.quote}</blockquote><div><code>Characters {visibleDetail.start_offset}–{visibleDetail.end_offset}</code><span className="pinned-label">Server-reconstructed</span></div></div>}</div>}
    {mode === 'REPLAY' ? <div className="small-note"><Icon name="clock" size={14} /><p>Return to live to retrieve or pin new evidence. Accepted evidence above reflects this point in the recorded history.</p></div> : !available ? <div className="small-note"><Icon name="warning" size={14} /><p>This source is withdrawn. Accepted passages remain available above. Restore availability before retrieving new passages.</p></div> : <>
      <form className="passage-search" onSubmit={event => { event.preventDefault(); void search(); }}><label htmlFor={`gene-${source.source_id}`}>Gene identity</label><input id={`gene-${source.source_id}`} value={geneId} onChange={event => setGeneId(event.target.value)} placeholder="FlyBase gene ID" /><label htmlFor={`query-${source.source_id}`}>Decision-relevant search</label><div><input id={`query-${source.source_id}`} value={query} onChange={event => setQuery(event.target.value)} placeholder="e.g. matching or expression" /><button className="icon-button" type="submit" disabled={searching || !query.trim() || !geneId.trim()} aria-label="Search source passages"><Icon name="search" size={17} /></button></div></form>
      {searching && <p className="loading-passage">Searching the imported source…</p>}
      {searched && !searching && !matches.length && <p className="muted">No matching passages in this source{searchCursor ? ' on this page' : ''}. Refine the question or search a different term.</p>}
      <div className="passage-matches">{matches.map(match => <button key={match.chunk_id} className={`passage-match ${activeChunk?.chunk_id === match.chunk_id ? 'active' : ''}`} disabled={reading} onClick={() => void read(match)}><span className="eyebrow">{match.section_type} · {match.section_title}</span><span>{match.preview}{match.preview_truncated ? '…' : ''}</span><small>Read exact spans <Icon name="arrow" size={11} /></small></button>)}</div>
      {searchCursor && <button className="button secondary full" disabled={searching} onClick={() => void search(true)}>More matching sections</button>}
      {activeChunk && <div className="read-section"><div className="section-title"><h3>{activeChunk.section_title || activeChunk.section_type}</h3><span>Exact source spans</span></div>{spans.map(span => { const saved = pinned.some(row => row.span_id === span.span_id); return <div className="read-span" key={span.span_id}><blockquote>{span.text}</blockquote><div><code>Characters {span.char_start}–{span.char_end}</code><button className={`pin-button ${saved ? 'pinned' : ''}`} disabled={Boolean(pinning) || saved} onClick={() => void pin(span)}><Icon name={saved ? 'check' : 'plus'} size={12} />{saved ? 'Pinned evidence' : pinning === span.span_id ? 'Pinning…' : 'Pin evidence'}</button></div></div>; })}{reading && <p className="loading-passage">Reading canonical spans…</p>}{chunkCursor && <button className="button secondary full" disabled={reading} onClick={() => void read(activeChunk, true)}>Continue reading <Icon name="arrow" size={12} /></button>}</div>}
    </>}
    {error && <p className="inline-error" role="alert">{error}</p>}
  </section>;
}
