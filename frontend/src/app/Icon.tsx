import type { CSSProperties } from 'react';

export type IconName = 'atlas' | 'arrow' | 'book' | 'branch' | 'check' | 'chevron' | 'clock' | 'close' | 'download' | 'external' | 'pause' | 'play' | 'plus' | 'search' | 'shield' | 'spark' | 'step' | 'warning';
const paths: Record<IconName, React.ReactNode> = {
  atlas: <><circle cx="12" cy="12" r="3" /><ellipse cx="12" cy="12" rx="10" ry="5" transform="rotate(-35 12 12)" /><path d="M6 4c4-2 11 7 12 13" /></>,
  arrow: <><path d="M5 12h14M13 6l6 6-6 6" /></>,
  book: <><path d="M4 4h7c1 0 1 1 1 1s0-1 1-1h7v15h-7c-1 0-1 1-1 1s0-1-1-1H4zM12 5v15" /></>,
  branch: <><circle cx="6" cy="5" r="2" /><circle cx="18" cy="7" r="2" /><circle cx="6" cy="19" r="2" /><path d="M6 7v10M8 15c7 0 10-2 10-6" /></>,
  check: <path d="m5 12 4 4L19 6" />,
  chevron: <path d="m9 5 7 7-7 7" />,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  close: <path d="m6 6 12 12M6 18 18 6" />,
  download: <><path d="M12 3v12m-5-5 5 5 5-5M4 16v4h16v-4" /></>,
  external: <><path d="M14 3h7v7M21 3l-11 11M11 4H4v16h16v-7" /></>,
  pause: <><path d="M8 5v14M16 5v14" /></>,
  play: <path d="m8 4 12 8-12 8z" />,
  plus: <path d="M12 5v14M5 12h14" />,
  search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></>,
  shield: <><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z" /><path d="m8 11 3 3 5-5" /></>,
  spark: <><path d="m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3z" /></>,
  step: <><path d="m5 5 10 7-10 7zM19 5v14" /></>,
  warning: <><path d="m12 3 10 18H2zM12 9v5M12 17v1" /></>,
};
export function Icon({ name, size = 18, style }: { name: IconName; size?: number; style?: CSSProperties }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={style}>{paths[name]}</svg>;
}
