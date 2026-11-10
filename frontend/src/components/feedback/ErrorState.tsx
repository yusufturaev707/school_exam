import { Link } from 'react-router';
import { Button, buttonClass } from '@/components/ui/Button';
import { Icon } from '@/components/ui/Icon';
import { EmptyState } from './EmptyState';
import { ApiError, toApiError } from '@/lib/http';

export function describeError(error: unknown): { title: string; description: string } {
  const e = error instanceof ApiError ? error : toApiError(error);
  switch (e.kind) {
    case 'network':
      return { title: 'Internet aloqasi yoʻq', description: 'Internetga ulanganingizni tekshirib, qayta urinib koʻring.' };
    case 'forbidden':
      return { title: 'Bu sahifa siz uchun yopiq', description: 'Bu maʼlumotni koʻrish uchun ruxsat yoʻq.' };
    case 'not_found':
      return { title: 'Hech narsa topilmadi', description: 'Bu sahifa mavjud emas yoki havola notoʻgʻri boʻlishi mumkin.' };
    case 'server':
    case 'invalid_response':
      return { title: 'Nimadir notoʻgʻri ketdi', description: 'Bu sizning aybingiz emas. Birozdan soʻng qayta urinib koʻring.' };
    default:
      return { title: 'Kutilmagan xatolik', description: 'Iltimos, qayta urinib koʻring.' };
  }
}

/** Dev-only: the Vite proxy answers 502/503/504 when the backend at VITE_API_PROXY isn't running. */
function devBackendHint(error: unknown): string | null {
  if (!import.meta.env.DEV) return null;
  const e = error instanceof ApiError ? error : toApiError(error);
  if (e.status === 502 || e.status === 503 || e.status === 504) {
    return 'DEV: backend ishlamayapti (/api proksisi javob olmadi). Backendni ishga tushiring yoki mock rejimdan foydalaning: npm run dev:mock';
  }
  return null;
}

/**
 * “Qayta urinish” only where retrying can help (network, 5xx, rate limit, bad response).
 * For 404 / 403 the `fallback` link is shown instead — retrying a missing page is pointless.
 */
export function ErrorState({ error, onRetry, className, fallback }: { error: unknown; onRetry?: () => void; className?: string; fallback?: { to: string; label: string } }) {
  const { title, description } = describeError(error);
  const hint = devBackendHint(error);
  const e = error instanceof ApiError ? error : toApiError(error);
  const canRetry = !!onRetry && (e.isRetryable || e.kind === 'invalid_response' || e.kind === 'unknown');
  return (
    <EmptyState
      mood="hayron"
      title={title}
      description={
        hint ? (
          <>
            {description}
            <code className="mt-3 block rounded-[var(--radius-sm)] bg-warning-light p-3 text-left text-[13px] text-warning-strong">{hint}</code>
          </>
        ) : (
          description
        )
      }
      className={className}
      action={
        canRetry || fallback ? (
          <div className="flex flex-col items-center gap-2">
            {canRetry && (
              <Button variant="secondary" onClick={onRetry} leftIcon={<Icon name="retry" />}>
                Qayta urinish
              </Button>
            )}
            {fallback && (
              <Link to={fallback.to} className={buttonClass(canRetry ? 'ghost' : 'primary')}>
                {fallback.label}
                {!canRetry && <Icon name="arrowR" />}
              </Link>
            )}
          </div>
        ) : undefined
      }
    />
  );
}
