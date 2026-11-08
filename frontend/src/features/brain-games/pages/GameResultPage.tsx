import { useParams } from 'react-router';
import { useGameResult } from '../hooks/useGames';
import { GameCompletion } from '../components/GameCompletion';
import { Skeleton } from '@/components/ui/Skeleton';
import { ErrorState } from '@/components/feedback/ErrorState';
import { TopBar } from '@/components/shared/design';

/** Completion screen; also reachable later from "recently played" (result comes from the backend). */
export default function GameResultPage() {
  const { sessionId = '' } = useParams();
  const { data, isPending, isError, error, refetch } = useGameResult(sessionId);
  if (isPending) return <Skeleton className="mt-8 h-[480px]" />;
  if (isError)
    return (
      <>
        <TopBar title="Oʻyin natijasi" back="/activities" preferHistory />
        <ErrorState error={error} onRetry={() => void refetch()} fallback={{ to: '/activities', label: 'Laboratoriyaga qaytish' }} />
      </>
    );
  return <GameCompletion result={data} />;
}
