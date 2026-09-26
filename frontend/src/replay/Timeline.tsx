import type { RunEvent } from '../contracts';
import { Icon } from '../app/Icon';
import { eventLabel } from './events';

export function Timeline({ events, cursor, lastSequence, mode, playing, seek, goLive, togglePlay }: { events: RunEvent[]; cursor: number; lastSequence: number; mode: 'LIVE' | 'REPLAY'; playing: boolean; seek: (value: number) => void; goLive: () => void; togglePlay: () => void }) {
  const first = events.at(0);
  const last = events.at(-1);
  const duration = first && last ? Math.max(0, (Date.parse(last.occurred_at) - Date.parse(first.occurred_at)) / 1000) : 0;
  const elapsed = !first || !last ? 'not recorded' : duration < 60 ? `${Math.round(duration)}s` : `${Math.floor(duration / 60)}m ${Math.round(duration % 60)}s`;
  const selectedEvent = events.find(event => event.sequence === cursor);
  return <footer className="timeline" aria-label="Event replay controls">
    <div className="timeline-heading"><Icon name="clock" size={17} /><strong>Event history</strong><span>{events.length} recorded events</span><span className="original-time">Original duration {elapsed}</span></div>
    <div className="timeline-controls">
      <button className="icon-button play-button" onClick={togglePlay} disabled={!events.length} aria-label={playing ? 'Pause replay' : 'Play replay'}><Icon name={playing ? 'pause' : 'play'} size={18} /></button>
      <button className="icon-button" onClick={() => seek(Math.min(lastSequence, cursor + 1))} disabled={cursor >= lastSequence} aria-label="Next event"><Icon name="step" size={17} /></button>
      <div className="timeline-track"><input aria-label="Replay event" type="range" min={0} max={Math.max(lastSequence, 1)} value={cursor} onChange={event => seek(Number(event.target.value))} disabled={!events.length} /><div className="timeline-track-labels"><span>START</span><span>{eventLabel(selectedEvent)}</span><span>{cursor} / {lastSequence}</span></div></div>
      <button className={`live-button ${mode === 'LIVE' ? 'is-live' : ''}`} onClick={goLive}><span className="signal-dot" />{mode === 'LIVE' ? 'LIVE' : 'Return to live'}</button>
    </div>
  </footer>;
}
