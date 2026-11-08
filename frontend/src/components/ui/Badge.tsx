import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

type Tone = 'primary' | 'success' | 'warning' | 'neutral' | 'error' | 'onDark' | 'status';

/* Dizayn: Chip (bd-chip). `status` — sariq “Topshirish mumkin”, `onDark` — hero ustidagi shisha chip. */
const tones: Record<Tone, string> = {
  primary: 'bd-chip--soft is-brand',
  success: 'bd-chip--soft bg-success-soft! text-success-ink!',
  warning: 'bd-chip--soft is-logic',
  error: 'bd-chip--soft bg-danger-soft! text-danger-ink!',
  neutral: 'bd-chip--soft',
  onDark: 'bd-chip--glass',
  status: 'bd-chip--status',
};

export function Badge({ tone = 'primary', icon, children, className }: { tone?: Tone; icon?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <span className={cn('bd-chip', tones[tone], className)}>
      {icon}
      {children}
    </span>
  );
}
