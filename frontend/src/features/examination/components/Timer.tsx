import { useEffect, useState } from 'react';
import { Icon } from '@/components/ui/Icon';
import { formatClock, remainingMs, spokenClock } from '../utils/time';
import { cn } from '@/lib/cn';

/**
 * Countdown that owns its own 1s tick so the rest of the exam screen doesn't re-render every second.
 * Display only — the actual deadline is enforced by the backend and the engine's deadline watcher.
 */
export function Timer({ expiresAt, clockOffsetMs, className }: { expiresAt: string; clockOffsetMs: number; className?: string }) {
  const [left, setLeft] = useState(() => remainingMs(expiresAt, clockOffsetMs));

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const tick = () => {
      const ms = remainingMs(expiresAt, clockOffsetMs);
      setLeft(ms);
      if (ms > 0) timer = setTimeout(tick, (ms % 1000) + 20 || 1000); // align to second boundaries
    };
    tick();
    const onVisible = () => document.visibilityState === 'visible' && tick();
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      clearTimeout(timer);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [expiresAt, clockOffsetMs]);

  const low = left <= 5 * 60_000;
  return (
    <div
      role="timer"
      aria-live="off"
      aria-label={`Qolgan vaqt: ${spokenClock(left)}`}
      className={cn(
        'bd-chip bd-chip--stat tabular h-10! px-3.5! text-[16px]! transition-colors duration-700',
        low ? 'is-streak' : 'is-brand',
        className,
      )}
    >
      <Icon name="clock" size={18} />
      <span aria-hidden="true">{formatClock(left)}</span>
    </div>
  );
}
