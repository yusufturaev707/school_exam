import { cn } from '@/lib/cn';
import { Mascot } from './Mascot';

/** Dizayn: kompyuter yon panelidagi logo — maskot + “Bilimdon” (20px/900, brand-ink). */
export function Logo({ className, light, withMascot = true }: { className?: string; light?: boolean; withMascot?: boolean }) {
  return (
    <span className={cn('inline-flex items-center gap-2.5 text-[20px] font-black tracking-tight', light ? 'text-on-hero' : 'text-brand-ink', className)}>
      {withMascot && <Mascot mood="salom" size={36} />}
      Bilimdon
    </span>
  );
}
