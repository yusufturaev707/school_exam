import type { ReactNode } from 'react';
import { Mascot, type MascotMood } from '@/components/shared/Mascot';
import { cn } from '@/lib/cn';

export interface EmptyStateProps {
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  mood?: MascotMood;
  className?: string;
  compact?: boolean;
  /** Dizayn: boʻsh holat — krem karta ichida maskot + bitta aniq amal. */
  card?: boolean;
}

export function EmptyState({ title, description, action, mood = 'oylayapti', className, compact, card }: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center text-center',
        card && 'bd-card bd-card--cream px-5! py-6!',
        compact ? 'gap-1 py-3' : 'gap-1 py-6',
        className,
      )}
    >
      <Mascot mood={mood} size={compact ? 88 : 112} />
      <h3 className="t-h2 mt-2">{title}</h3>
      {description && <p className="t-sm muted max-w-sm">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
