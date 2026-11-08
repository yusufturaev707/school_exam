import { useEffect, useState, type ReactNode } from 'react';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { Icon } from '@/components/ui/Icon';
import { clock } from '../utils/meta';

/** Elapsed time, shown for information only — no countdown pressure, no penalty. */
export function GameTimer({ startedAt, running = true }: { startedAt: number; running?: boolean }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!running) return;
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, [running]);
  const seconds = Math.max(0, Math.floor((now - startedAt) / 1000));
  return (
    <span className="bd-chip bd-chip--soft tabular">
      <Icon name="clock" size={16} />
      <span aria-label={`Oʻtgan vaqt ${clock(seconds)}`}>{clock(seconds)}</span>
    </span>
  );
}

/** Dizayn: ScreenPlay — 8px progress + “2/6”. */
export function GameProgress({ value, max, label }: { value: number; max: number; label: string }) {
  return (
    <div className="row">
      <ProgressBar value={value} max={max} size="md" label={label} className="flex-1" />
      <span className="t-xs muted tabular shrink-0">
        {value}/{max}
      </span>
    </div>
  );
}

/** Dizayn: ScreenPlay topbar — ✕ yopish, oʻyin nomi, oʻngda ⭐ chip. Oʻyin ekranning oʻzini oladi. */
export function GameHeader({ title, onExit, right, progress }: { title: string; onExit: () => void; right?: ReactNode; progress?: ReactNode }) {
  return (
    <header className="safe-top sticky top-0 z-20 bg-bg/95 backdrop-blur-md">
      <div className="bd-topbar mx-auto w-full max-w-3xl px-2! sm:px-3!">
        <button type="button" className="bd-iconbtn hover:bg-bg-tint" aria-label="Oʻyindan chiqish" onClick={onExit}>
          <Icon name="x" />
        </button>
        <h1 className="bd-topbar__title grow truncate">{title}</h1>
        {right}
      </div>
      {progress && <div className="mx-auto w-full max-w-3xl px-4 pb-3">{progress}</div>}
    </header>
  );
}
