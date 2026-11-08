import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router';
import { examApi } from '../api/examApi';
import { Mascot } from '@/components/shared/Mascot';
import { Confetti } from '@/components/shared/Confetti';
import { Spinner } from '@/components/ui/Spinner';
import { Icon } from '@/components/ui/Icon';
import { buttonClass } from '@/components/ui/Button';
import { ErrorState } from '@/components/feedback/ErrorState';

export default function ExamCompletePage() {
  const { attemptId = '' } = useParams();
  // The result may take a moment to be calculated by the backend — poll until it's ready.
  const query = useQuery({
    queryKey: ['examination', 'attempt', attemptId, 'completion'],
    queryFn: () => examApi.getAttempt(attemptId),
    refetchInterval: (q) => (q.state.data?.session.resultId ? false : 2500),
  });
  const resultId = query.data?.session.resultId ?? null;

  if (query.isError) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;

  return (
    <div className="relative">
      <Confetti />
      <div className="flex min-h-[70dvh] flex-col items-center justify-center text-center">
        <Mascot mood="xursand" size={140} />
        <p className="t-over mt-3 text-brand-ink">Imtihon yakunlandi</p>
        <h1 className="t-hero mt-1">Barakalla! Sen imtihonni yakunlading!</h1>
        <p className="t-sm muted mt-1 max-w-[300px]">Javoblaring saqlandi. Endi natijangni koʻrib, nimalarni yaxshi bilishingni bilib olishing mumkin.</p>

        <div className="mt-8 flex w-full max-w-sm flex-col gap-2">
          {resultId ? (
            <Link to={`/results/${resultId}`} replace className={buttonClass('primary', { fullWidth: true })}>
              Natijani koʻrish
              <Icon name="arrowR" />
            </Link>
          ) : (
            <p className="bd-btn bd-btn--secondary bd-btn--block h-12!" role="status">
              <Spinner className="size-5" />
              Natija tayyorlanmoqda…
            </p>
          )}
          <Link to="/" className={buttonClass('ghost', { fullWidth: true })}>
            <Icon name="home" />
            Bosh sahifaga qaytish
          </Link>
        </div>
      </div>
    </div>
  );
}
