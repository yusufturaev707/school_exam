import { cn } from '@/lib/cn';

export interface ProgressBarProps {
  value: number;
  max: number;
  label: string;
  className?: string;
  /** Toʻldirish rangi (masalan `bg-math-solid`). Odatda `is-<x>` klassi orqali beriladi. */
  barClassName?: string;
  trackClassName?: string;
  /** `sm` — 6px (dizayn standarti), `md` — 8px (oʻyin jarayoni). */
  size?: 'sm' | 'md';
}

/** Dizayn: bd-bar — 6px iz (--line), toʻldirish --c (yoki brand). */
export function ProgressBar({ value, max, label, className, barClassName, trackClassName, size = 'sm' }: ProgressBarProps) {
  const pct = max > 0 ? Math.min(100, Math.max(0, (value / max) * 100)) : 0;
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value}
      className={cn('bd-bar block w-full', size === 'md' && 'h-2', trackClassName, className)}
    >
      <i className={cn('transition-[width] duration-500 ease-out', barClassName)} style={{ ['--p' as string]: pct }} />
    </div>
  );
}
