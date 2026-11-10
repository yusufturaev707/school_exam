import { Suspense, useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { useGame, useDailyChallenge } from '../hooks/useGames';
import { useGameSession } from '../hooks/useGameSession';
import { GameInstructions } from '../components/GameInstructions';
import { ENGINES } from '../engines/registry';
import { DIFFICULTY_META } from '../utils/meta';
import { loadActiveGame, loadLevel, type ActiveGame } from '../utils/activeGame';
import { ConfirmationDialog } from '@/components/ui/ConfirmationDialog';
import { Button, buttonClass } from '@/components/ui/Button';
import { Icon } from '@/components/ui/Icon';
import { FullPageLoader } from '@/components/feedback/FullPageLoader';
import { ErrorState } from '@/components/feedback/ErrorState';
import { EmptyState } from '@/components/feedback/EmptyState';
import { Mascot } from '@/components/shared/Mascot';
import { TopBar } from '@/components/shared/design';
import { ApiError } from '@/lib/http';

function startError(error: unknown): string | null {
  if (!error) return null;
  if (error instanceof ApiError) {
    if (error.kind === 'network') return 'Internet aloqasi yoʻq. Ulanib, qayta urinib koʻring.';
    if (error.code === 'GAME_NOT_AVAILABLE') return 'Bu oʻyin hozircha yopiq. Boshqa oʻyinni tanlab koʻring!';
  }
  return 'Oʻyinni boshlab boʻlmadi. Birozdan soʻng qayta urinib koʻring.';
}

function finishError(error: unknown): string | null {
  if (!error) return null;
  if (error instanceof ApiError && error.kind === 'network') return 'Internet aloqasi uzildi. Ulangach, “Qayta urinish” tugmasini bosing — natijangiz yoʻqolmaydi.';
  return 'Server javob bermadi. Birozdan soʻng qayta urinib koʻring — natijangiz yoʻqolmaydi.';
}

/** Full-screen shell for states outside gameplay: always a way back to the lab. */
function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-[640px] px-4 pt-[env(safe-area-inset-top)] pb-10">
      <TopBar title="Laboratoriya" back="/activities" />
      {children}
    </div>
  );
}

const backToLab = (
  <Link to="/activities" className={buttonClass('primary')}>
    Laboratoriyaga qaytish
    <Icon name="arrowR" />
  </Link>
);

/** Full-screen game flow: (resume?) → introduction → gameplay → (completion page). No app navigation while playing. */
export default function GamePage() {
  const { slug = '' } = useParams();
  const [params] = useSearchParams();
  const wantsDaily = params.get('daily') === '1';
  const navigate = useNavigate();
  const gameQuery = useGame(slug);
  const dailyQuery = useDailyChallenge();
  const game = gameQuery.data;
  const { active, start, resume, abandon, complete, finish } = useGameSession(game);
  const [confirmExit, setConfirmExit] = useState(false);
  // An unfinished session of this game left in this tab (reload, crash, accidental close).
  const [pending, setPending] = useState<ActiveGame | null>(() => loadActiveGame(slug));

  // Daily reward applies only to today's game at today's level, until it is earned.
  const daily =
    wantsDaily && dailyQuery.data && !dailyQuery.data.completed && dailyQuery.data.game.slug === slug ? { difficulty: dailyQuery.data.difficulty, bonus: dailyQuery.data.bonus } : null;

  const playing = active !== null && !complete.isSuccess;

  useEffect(() => {
    if (!playing) return;
    document.documentElement.classList.add('exam-mode'); // no pull-to-refresh / swipe-back mid-game
    // Reload / tab close mid-game: the browser asks first (progress can still be resumed afterwards).
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', warn);
    return () => {
      document.documentElement.classList.remove('exam-mode');
      window.removeEventListener('beforeunload', warn);
    };
  }, [playing]);

  const onExit = useCallback(() => setConfirmExit(true), []);

  if (gameQuery.isPending || (wantsDaily && dailyQuery.isPending)) return <FullPageLoader />;
  if (gameQuery.isError) {
    if (gameQuery.error instanceof ApiError && gameQuery.error.kind === 'not_found') {
      return (
        <Shell>
          <EmptyState card title="Bunday oʻyin topilmadi" description="Balki havola notoʻgʻri yozilgandir. Laboratoriyadan boshqa oʻyin tanlab koʻring." action={backToLab} />
        </Shell>
      );
    }
    return (
      <Shell>
        <ErrorState error={gameQuery.error} onRetry={() => void gameQuery.refetch()} fallback={{ to: '/activities', label: 'Laboratoriyaga qaytish' }} />
      </Shell>
    );
  }

  if (!game) return <FullPageLoader />;
  const Engine = ENGINES[game.kind];
  if (!game.isActive || !Engine) {
    return (
      <Shell>
        <EmptyState card title={`${game.title} — tez orada!`} description="Bu oʻyin ustida ishlayapmiz. Hozircha boshqa oʻyinlarni sinab koʻring." action={backToLab} />
      </Shell>
    );
  }

  if (!active && pending) {
    return (
      <Shell>
        <div className="bd-card bd-card--cream flex flex-col items-center px-5! py-6! text-center">
          <Mascot mood="oylayapti" size={104} />
          <h1 className="t-h2 mt-2">Tugallanmagan oʻyin bor</h1>
          <p className="t-sm muted mt-1">
            {game.title} · {DIFFICULTY_META[pending.difficulty].label}. Toʻxtagan joyingdan davom ettirasanmi yoki qaytadan boshlaysanmi?
          </p>
          {resume.isError && <p className="t-sm mt-3 text-danger-ink">Bu oʻyinni davom ettirib boʻlmaydi — yangisini boshlaymiz.</p>}
          <div className="mt-5 flex w-full max-w-sm flex-col gap-2">
            <Button fullWidth loading={resume.isPending} disabled={resume.isError} onClick={() => resume.mutate(pending.sessionId)} rightIcon={<Icon name="play" />} aria-label="Oʻyinni davom ettirish">
              Davom ettirish
            </Button>
            <Button
              variant="ghost"
              fullWidth
              disabled={resume.isPending}
              aria-label="Oʻyinni qaytadan boshlash"
              leftIcon={<Icon name="retry" />}
              onClick={() => {
                void abandon(pending.sessionId);
                setPending(null);
              }}
            >
              Qaytadan boshlash
            </Button>
          </div>
        </div>
      </Shell>
    );
  }

  if (!active) {
    return (
      <GameInstructions
        game={game}
        daily={daily}
        initialDifficulty={loadLevel(slug)}
        starting={start.isPending}
        error={startError(start.error)}
        onStart={(difficulty) => !start.isPending && start.mutate({ difficulty, daily: daily !== null })}
      />
    );
  }

  return (
    <>
      <Suspense fallback={<FullPageLoader />}>
        <Engine
          key={active.session.id}
          session={active.session}
          content={active.content}
          resumeAnswers={active.resumeAnswers}
          title={game.title}
          onExit={onExit}
          onFinish={finish}
          finishing={complete.isPending}
          finishError={complete.isError ? finishError(complete.error) : null}
        />
      </Suspense>
      <ConfirmationDialog
        open={confirmExit && !complete.isPending}
        title="Oʻyindan chiqasizmi?"
        description="Bu oʻyindagi natija saqlanmaydi. Xohlagan paytingizda qaytadan boshlashingiz mumkin."
        confirmLabel="Oʻyindan chiqish"
        cancelLabel="Oʻynashda davom etish"
        onCancel={() => setConfirmExit(false)}
        onConfirm={() => {
          void abandon(active.session.id);
          navigate('/activities', { replace: true });
        }}
      />
    </>
  );
}
