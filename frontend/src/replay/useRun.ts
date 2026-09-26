import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { RunEvent, RunSnapshot } from '../contracts';
import { api } from '../api/client';
import { appendEvents, replayThrough } from './events';

export function useRun(runId: string | null) {
  const [seed, setSeed] = useState<RunSnapshot | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [playing, setPlaying] = useState(false);
  const refreshRef = useRef<() => Promise<void>>(async () => {});

  useEffect(() => {
    let stopped = false;
    let busy = false;
    let accepted: RunEvent[] = [];
    let snapshot: RunSnapshot | null = null;
    setSeed(null); setEvents([]); setCursor(null); setError(null); setPlaying(false); setConnected(false);
    if (!runId) { setLoading(false); return; }
    setLoading(true);
    const poll = async () => {
      if (busy || stopped) return;
      busy = true;
      try {
        if (!snapshot) snapshot = await api.snapshot(runId);
        let more = true;
        let pages = 0;
        while (more && !stopped && pages++ < 100) {
          const before = accepted.at(-1)?.sequence ?? 0;
          const page = await api.events(runId, before);
          if (page.events.some(event => event.run_id !== runId)) throw new Error('An event belongs to another run.');
          const next = appendEvents(accepted, page.events);
          const after = next.at(-1)?.sequence ?? 0;
          if (after === before && (page.has_more || page.last_sequence > before)) throw new Error(`Waiting to recover missing event ${before + 1}.`);
          accepted = next;
          more = page.has_more || after < page.last_sequence;
        }
        if (stopped) return;
        if ((accepted.at(-1)?.sequence ?? 0) < snapshot.last_sequence) throw new Error('Loading the remaining history before advancing the graph.');
        // Reconstruct once here so invalid event payloads fail visibly, not in render.
        replayThrough(snapshot, accepted, accepted.at(-1)?.sequence ?? 0);
        setSeed(snapshot); setEvents([...accepted]); setError(null); setConnected(true); setLoading(false);
      } catch (reason) {
        if (!stopped) { setError(reason instanceof Error ? reason.message : 'Unable to load this run.'); setConnected(false); setLoading(false); }
      } finally { busy = false; }
    };
    refreshRef.current = poll;
    void poll();
    const timer = window.setInterval(() => void poll(), 1000);
    return () => { stopped = true; window.clearInterval(timer); };
  }, [runId]);

  const lastSequence = events.at(-1)?.sequence ?? 0;
  const sequence = cursor === null ? lastSequence : Math.min(cursor, lastSequence);
  const snapshot = useMemo(() => seed?.run_id === runId ? replayThrough(seed, events, sequence) : null, [seed, events, sequence, runId]);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      setCursor(current => {
        const next = (current ?? 0) + 1;
        if (next >= lastSequence) { setPlaying(false); return lastSequence; }
        return next;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [playing, lastSequence]);

  const seek = useCallback((value: number) => { setPlaying(false); setCursor(Math.max(0, value)); }, []);
  const goLive = useCallback(() => { setCursor(null); setPlaying(false); }, []);
  const togglePlay = useCallback(() => {
    if (!playing && (cursor === null || cursor >= lastSequence)) setCursor(0);
    setPlaying(value => !value);
  }, [playing, cursor, lastSequence]);

  return { snapshot, events, cursor: sequence, lastSequence, mode: cursor === null ? 'LIVE' as const : 'REPLAY' as const, loading, error, connected, playing, seek, goLive, togglePlay, refresh: () => refreshRef.current() };
}
