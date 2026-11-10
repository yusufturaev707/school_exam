import { Mascot } from '@/components/shared/Mascot';
import { Spinner } from '@/components/ui/Spinner';
import { Button } from '@/components/ui/Button';
import { Icon } from '@/components/ui/Icon';

/** Shown while the backend records the result; a failed save can be retried without replaying. */
export function FinishingOverlay({ finishing, error, onRetry }: { finishing: boolean; error: string | null; onRetry: () => void }) {
  return (
    <div className="fixed inset-0 z-40 flex flex-col items-center justify-center gap-3 bg-bg/95 px-6 text-center backdrop-blur-sm" role="status" aria-live="polite">
      <Mascot mood={error ? 'hayron' : 'xursand'} size={128} />
      {error ? (
        <>
          <h2 className="t-hero">Natijani saqlab boʻlmadi</h2>
          <p className="t-sm muted max-w-sm">{error}</p>
          <Button className="mt-2" onClick={onRetry} disabled={finishing} leftIcon={<Icon name="retry" />}>
            Qayta urinish
          </Button>
        </>
      ) : (
        <>
          <h2 className="t-hero">Barakalla!</h2>
          <p className="t-sm muted max-w-sm">Natijangizni saqlayapmiz…</p>
          <Spinner className="size-8 text-brand" />
        </>
      )}
    </div>
  );
}
