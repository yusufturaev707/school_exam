import { motion } from 'motion/react';
import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

export interface CircularProgressProps {
  value: number;
  max: number;
  size?: number;
  stroke?: number;
  label: string;
  children?: ReactNode;
  color?: string;
  trackColor?: string;
}

/** Katta natija halqasi (natija sahifalari). Kichik halqalar uchun `Ring` dan foydalaning. */
export function CircularProgress({ value, max, size = 168, stroke = 14, label, children, color = 'var(--brand)', trackColor = 'var(--line)' }: CircularProgressProps) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = max > 0 ? Math.min(1, Math.max(0, value / max)) : 0;
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }} role="img" aria-label={label}>
      <svg width={size} height={size} className="-rotate-90" aria-hidden="true">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={trackColor} strokeWidth={stroke} />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: c * (1 - pct) }}
          transition={{ duration: 0.9, ease: 'easeOut', delay: 0.15 }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">{children}</div>
    </div>
  );
}

/**
 * Dizayn: bd-ring — conic-gradient halqa. `lg` 64px, oddiy 40px; `hero` — hero foni ustida sariq.
 * Rang `is-<x>` klassi orqali (masalan `className="is-brand"`).
 */
export function Ring({ percent, children, size = 'md', hero, label, className }: { percent: number; children: ReactNode; size?: 'md' | 'lg'; hero?: boolean; label?: string; className?: string }) {
  return (
    <span
      className={cn('bd-ring', size === 'lg' && 'bd-ring--lg', hero && 'bd-ring--hero', className)}
      style={{ ['--p' as string]: Math.max(0, Math.min(100, percent)) }}
      role={label ? 'img' : undefined}
      aria-label={label}
    >
      <b aria-hidden={label ? true : undefined}>{children}</b>
    </span>
  );
}
