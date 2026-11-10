import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router';
import { useExamEngine } from '../hooks/useExamEngine';
import { useSwipeNavigation } from '../hooks/useSwipeNavigation';
import { countAnswered } from '../store/examStore';
import { Timer } from '../components/Timer';
import { QuestionCard } from '../components/QuestionCard';
import { QuestionNavigator } from '../components/QuestionNavigator';
import { SaveStatus } from '../components/SaveStatus';
import { ConnectionBanner } from '../components/ConnectionBanner';
import { SubmitDialog } from '../components/SubmitDialog';
import { Button } from '@/components/ui/Button';
import { Icon } from '@/components/ui/Icon';
import { IconButton } from '@/components/ui/IconButton';
import { Modal } from '@/components/ui/Modal';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { Skeleton } from '@/components/ui/Skeleton';
import { Spinner } from '@/components/ui/Spinner';
import { Card } from '@/components/ui/Card';
import { ErrorState } from '@/components/feedback/ErrorState';
import { Mascot } from '@/components/shared/Mascot';
import { SUBJECTS } from '@/components/shared/subjects';

function ExamSkeleton({ waitingForConnection = false }: { waitingForConnection?: boolean }) {
  return (
    <div className="safe-top">
      <ConnectionBanner
        visible={waitingForConnection}
        message="Internet aloqasi uzildi. Aloqa tiklanishi bilan savollar oʻzi yuklanadi. Imtihon vaqti toʻxtamaydi, shuning uchun internetni tekshirib koʻring."
      />
      <div className="mx-auto w-full max-w-6xl px-4 py-5" aria-busy="true" aria-label="Imtihon yuklanmoqda">
        <Skeleton className="h-12 w-full" />
        <div className="mt-5 lg:grid lg:grid-cols-[1fr_340px] lg:gap-6">
          <div className="space-y-3">
            <Skeleton className="h-40 w-full" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
          <Skeleton className="hidden h-96 lg:block" />
        </div>
      </div>
    </div>
  );
}

export default function ExamPage() {
  const { attemptId = '' } = useParams();
  const engine = useExamEngine(attemptId);
  const { session, questions, currentIndex, currentQuestion, answers, locked, sync, online, refreshFailing, waitingForConnection, expired, submitPhase } = engine;

  const [navigatorOpen, setNavigatorOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  // Position of each question within its subject ("3-savol / 15").
  const subjectPositions = useMemo(() => {
    const counters: Record<string, number> = {};
    const totals: Record<string, number> = {};
    for (const q of questions) totals[q.subject] = (totals[q.subject] ?? 0) + 1;
    return new Map(questions.map((q) => [q.id, { index: (counters[q.subject] = (counters[q.subject] ?? 0) + 1), total: totals[q.subject] ?? 0 }]));
  }, [questions]);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior });
  }, [currentIndex]);

  // App-like exam screen: no pull-to-refresh / overscroll bounce while answering.
  useEffect(() => {
    document.documentElement.classList.add('exam-mode');
    return () => document.documentElement.classList.remove('exam-mode');
  }, []);

  const swipe = useSwipeNavigation({
    onNext: () => currentIndex < questions.length - 1 && engine.next(),
    onPrev: () => currentIndex > 0 && engine.prev(),
    enabled: !navigatorOpen && !confirmOpen,
  });

  if (engine.query.isPending) return <ExamSkeleton waitingForConnection={waitingForConnection} />;
  if ((engine.query.isError && !refreshFailing) || !session) {
    return (
      <div className="mx-auto max-w-md px-4 py-10">
        <ErrorState error={engine.query.error} onRetry={() => void engine.query.refetch()} />
        <div className="mt-2 text-center">
          <Link to="/" className="font-bold text-primary-dark underline-offset-4 hover:underline">
            Bosh sahifaga qaytish
          </Link>
        </div>
      </div>
    );
  }
  if (!currentQuestion) return <ExamSkeleton />;

  const total = questions.length;
  const answered = countAnswered(answers);
  const isLast = currentIndex === total - 1;
  const unansweredIdx = questions.map((q, i) => ((answers[q.id]?.length ?? 0) > 0 ? -1 : i)).filter((i) => i >= 0);
  const position = subjectPositions.get(currentQuestion.id) ?? { index: currentIndex + 1, total };
  const finishing = submitPhase === 'submitting' || submitPhase === 'retrying' || expired;

  const openFinish = () => {
    setNavigatorOpen(false);
    setConfirmOpen(true);
  };

  return (
    <div className="flex min-h-dvh flex-col">
      {/* ---------- top: title, subject, timer, progress ---------- */}
      <header className="safe-top sticky top-0 z-20 bg-bg/95 shadow-[0_1px_0_var(--line)] backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-6xl items-center gap-3 px-4 pt-3 pb-2">
          <div className="min-w-0 flex-1">
            <p className="t-xs faint truncate">{session.examTitle}</p>
            <p className={`bd-topbar__title truncate ${SUBJECTS[currentQuestion.subject].ink}`}>{SUBJECTS[currentQuestion.subject].title}</p>
          </div>
          <span className="hidden sm:inline-flex">
            <SaveStatus sync={sync} online={online} />
          </span>
          <Timer expiresAt={session.expiresAt} clockOffsetMs={engine.clockOffsetMs} />
        </div>
        <div className="mx-auto w-full max-w-6xl px-4 pb-3">
          <div className="t-xs mb-1.5 flex items-center justify-between">
            <span className="tabular">
              {currentIndex + 1} / {total} savol
            </span>
            <span className="tabular muted">{answered} ta javob belgilangan</span>
          </div>
          <ProgressBar className={SUBJECTS[currentQuestion.subject].tone} value={answered} max={total} size="md" label={`${total} ta savoldan ${answered} tasiga javob berilgan`} />
        </div>
        <ConnectionBanner visible={!online || sync.phase === 'retrying' || refreshFailing} pendingCount={sync.pendingCount} />
      </header>

      {/* ---------- main: question + desktop navigator ---------- */}
      <main
        {...swipe}
        className="swipe-area mx-auto w-full max-w-6xl flex-1 px-3 pt-4 pb-32 sm:px-4 sm:pt-5 lg:grid lg:grid-cols-[minmax(0,1fr)_340px] lg:gap-6 lg:pb-10"
      >
        <div className="mx-auto w-full max-w-3xl">
          <QuestionCard
            question={currentQuestion}
            subjectIndex={position.index}
            subjectTotal={position.total}
            selected={answers[currentQuestion.id] ?? []}
            disabled={locked}
            onSelect={(optionId) => engine.select(currentQuestion.id, optionId)}
          />
          <div className="mt-4 flex items-center justify-between gap-3 px-1 sm:hidden">
            <SaveStatus sync={sync} online={online} />
            {currentIndex === 0 && (
              <span className="t-xs muted inline-flex items-center gap-1">
                <Icon name="hand" size={16} />
                Surib ham oʻtish mumkin
              </span>
            )}
          </div>

          <div className="mt-5 hidden items-center gap-3 lg:flex">
            <Button variant="secondary" size="lg" onClick={engine.prev} disabled={currentIndex === 0} leftIcon={<Icon name="arrowL" />}>
              Oldingi
            </Button>
            <div className="flex-1" />
            {isLast ? (
              <Button size="lg" onClick={openFinish} rightIcon={<Icon name="flag" />}>
                Yakunlash
              </Button>
            ) : (
              <Button size="lg" onClick={engine.next} rightIcon={<Icon name="arrowR" />}>
                Keyingi
              </Button>
            )}
          </div>
        </div>

        <aside className="hidden lg:block">
          <Card className="sticky top-36">
            <QuestionNavigator questions={questions} answers={answers} currentIndex={currentIndex} onSelect={engine.goTo} />
            <Button variant="secondary" fullWidth size="lg" className="mt-5" onClick={openFinish} leftIcon={<Icon name="flag" />}>
              Imtihonni yakunlash
            </Button>
          </Card>
        </aside>
      </main>

      {/* ---------- bottom bar (phones & tablets) ---------- */}
      <nav aria-label="Savollar boʻylab harakat" className="safe-bottom fixed inset-x-0 bottom-0 z-20 bg-card shadow-[0_-1px_0_var(--line),0_-8px_24px_rgba(17,48,42,.06)] lg:hidden">
        <div className="mx-auto grid max-w-3xl grid-cols-[auto_1fr_auto] items-center gap-2 px-3 py-2.5 sm:px-4 sm:py-3">
          <IconButton label="Oldingi savol" icon={<Icon name="arrowL" size={22} />} onClick={engine.prev} disabled={currentIndex === 0} className="bd-iconbtn--soft size-12! rounded-[var(--radius-md)]!" />
          <Button
            variant="secondary"
            size="lg"
            className="min-w-0 px-3!"
            onClick={() => setNavigatorOpen(true)}
            leftIcon={<Icon name="grid" className="hidden min-[380px]:block" />}
          >
            Savollar
          </Button>
          {isLast ? (
            <Button size="lg" onClick={openFinish} className="px-4! min-[380px]:px-5!" rightIcon={<Icon name="flag" />}>
              Yakunlash
            </Button>
          ) : (
            <Button size="lg" onClick={engine.next} className="px-4! min-[380px]:px-5!" rightIcon={<Icon name="arrowR" />}>
              Keyingi
            </Button>
          )}
        </div>
      </nav>

      <Modal
        open={navigatorOpen}
        onClose={() => setNavigatorOpen(false)}
        title="Savollar"
        description={`${answered} / ${total} ta savolga javob berdingiz`}
        footer={
          <Button size="lg" fullWidth variant="secondary" onClick={openFinish} leftIcon={<Icon name="flag" />}>
            Imtihonni yakunlash
          </Button>
        }
      >
        <QuestionNavigator
          questions={questions}
          answers={answers}
          currentIndex={currentIndex}
          onSelect={(i) => {
            engine.goTo(i);
            setNavigatorOpen(false);
          }}
        />
      </Modal>

      <SubmitDialog
        open={confirmOpen && !finishing}
        total={total}
        answered={answered}
        unansweredNumbers={unansweredIdx.map((i) => i + 1)}
        onCancel={() => setConfirmOpen(false)}
        onJumpToUnanswered={() => {
          setConfirmOpen(false);
          if (unansweredIdx[0] !== undefined) engine.goTo(unansweredIdx[0]);
        }}
        onConfirm={() => {
          setConfirmOpen(false);
          void engine.submit('manual');
        }}
      />

      <Modal
        open={submitPhase === 'offline_blocked'}
        onClose={engine.clearSubmitPhase}
        variant="dialog"
        title="Internet aloqasi yoʻq"
        description="Baʼzi javoblaringiz hali serverga yetib bormadi. Internetga ulangach, “Yakunlash” tugmasini qayta bosing. Vaqt tugaguncha ulanishga harakat qiling: serverga yetib bormagan javoblar hisobga olinmaydi."
        footer={
          <Button size="lg" onClick={engine.clearSubmitPhase} leftIcon={<Icon name="check" />}>
            Tushundim
          </Button>
        }
      />

      {finishing && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-bg/97 px-6 text-center" role="alertdialog" aria-live="assertive" aria-label="Imtihon yakunlanmoqda">
          <Mascot mood={expired ? "hayron" : "oylayapti"} size={128} />
          <h2 className="t-hero">{expired ? 'Vaqt tugadi' : 'Imtihon yakunlanmoqda'}</h2>
          <p className="t-sm muted max-w-sm">
            {submitPhase === 'retrying' ? 'Server bilan aloqa tiklanishini kutyapmiz. Iltimos, sahifani yopmang.' : 'Javoblaringizni saqlayapmiz. Biroz kuting…'}
          </p>
          <Spinner className="size-8 text-primary" />
        </div>
      )}
    </div>
  );
}
