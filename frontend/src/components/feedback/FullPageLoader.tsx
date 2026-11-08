import { Mascot } from '@/components/shared/Mascot';
import { Spinner } from '@/components/ui/Spinner';

export function FullPageLoader({ label = 'Yuklanmoqda…' }: { label?: string }) {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-canvas" role="status" aria-live="polite">
      <Mascot mood="calm" className="size-28" />
      <div className="flex items-center gap-2 text-[15px] font-semibold text-muted">
        <Spinner className="size-5 text-primary" />
        {label}
      </div>
    </div>
  );
}
