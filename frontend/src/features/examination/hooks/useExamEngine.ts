import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import { examApi, type LoadedAttempt } from '../api/examApi';
import { AnswerSyncEngine } from '../services/answerSyncEngine';
import { clearAttemptState, loadAttemptState, newIdempotencyKey, saveAttemptState } from '../services/attemptPersistence';
import { useExamStore } from '../store/examStore';
import { remainingMs } from '../utils/time';
import { ApiError } from '@/lib/http';
import { useOnlineStatus } from '@/hooks/useOnlineStatus';
import { toast } from '@/components/feedback/toastStore';
import type { SubmitReason } from '../types';

export const attemptQueryKey = (attemptId: string) => ['examination', 'attempt', attemptId] as const;

/** Attempt is closed on the server — keep calm and stop writing. */
const isAttemptClosed = (e: unknown) => e instanceof ApiError && (e.kind === 'conflict' || e.kind === 'forbidden' || e.kind === 'not_found');

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function withTimeout<T>(promise: Promise<T>, ms: number, fallback: T): Promise<T> {
  return Promise.race([promise, sleep(ms).then(() => fallback)]);
}

export type SubmitPhase = 'idle' | 'submitting' | 'retrying' | 'offline_blocked';

/**
 * The examination engine: everything about an attempt that is not presentation.
 * Pages render what this returns and call its actions.
 */
export function useExamEngine(attemptId: string) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const online = useOnlineStatus();

  const query = useQuery({
    queryKey: attemptQueryKey(attemptId),
    queryFn: () => {
      // After the first load only the small state (deadline, clock, answers, status) is fetched.
      const known = queryClient.getQueryData<LoadedAttempt>(attemptQueryKey(attemptId))?.session;
      const reuse = known?.status === 'in_progress' && known.questions.length > 0;
      return examApi.getAttempt(attemptId, reuse ? known.questions : undefined);
    },
    staleTime: 0,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
    // Periodic resync of deadline / clock offset, and detection of server-side finalisation.
    refetchInterval: 60_000,
    retry: (count, e) => !(e instanceof ApiError && !e.isRetryable) && count < 5,
  });

  const session = query.data?.session;
  const clockOffsetMs = query.data?.clockOffsetMs ?? 0;
  const isActive = session?.status === 'in_progress';

  // The questions and the deadline are already on the device, so a failed background refresh must not end the exam screen.
  const refreshFailing = query.isRefetchError && query.error instanceof ApiError && query.error.isRetryable;
  // The very first load is stuck: the browser reports no network, or the requests keep failing.
  const waitingForConnection = query.isPending && (query.fetchStatus === 'paused' || query.failureCount > 0);

  const answers = useExamStore((s) => s.answers);
  const currentIndex = useExamStore((s) => s.currentIndex);
  const locked = useExamStore((s) => s.locked);
  const sync = useExamStore((s) => s.sync);

  const engineRef = useRef<AnswerSyncEngine | null>(null);
  const submittingRef = useRef(false);
  const [submitPhase, setSubmitPhase] = useState<SubmitPhase>('idle');
  const [expired, setExpired] = useState(false);

  /* ---------- finished attempt → completion screen ---------- */
  const goToDone = useCallback(() => {
    engineRef.current?.dispose();
    clearAttemptState(attemptId);
    void queryClient.invalidateQueries({ queryKey: ['student'] });
    void queryClient.invalidateQueries({ queryKey: ['examination', 'available'] });
    navigate(`/exam/attempt/${attemptId}/done`, { replace: true });
  }, [attemptId, navigate, queryClient]);

  useEffect(() => {
    if (session && session.status !== 'in_progress') goToDone();
  }, [session, goToDone]);

  /* ---------- one-time initialisation per attempt ---------- */
  useEffect(() => {
    if (!session || !isActive || engineRef.current) return;
    const persisted = loadAttemptState(attemptId);

    // Server answers + anything the student picked that the server hasn't confirmed yet.
    const merged = { ...session.answers };
    for (const p of persisted.pending) merged[p.questionId] = p.optionIds;
    const index = Math.min(Math.max(0, persisted.currentIndex), Math.max(0, session.questions.length - 1));
    useExamStore.getState().init(attemptId, merged, index);
    if (!persisted.submitKey) saveAttemptState(attemptId, { submitKey: newIdempotencyKey() });

    engineRef.current = new AnswerSyncEngine({
      initialPending: persisted.pending,
      save: async (a) => {
        await examApi.saveAnswer(attemptId, a.questionId, a.optionIds, a.seq);
      },
      isFatal: isAttemptClosed,
      onState: (s) => useExamStore.getState().setSync(s),
      onPendingChange: (pending) => saveAttemptState(attemptId, { pending }),
      onFatal: () => {
        useExamStore.getState().setLocked(true);
        void query.refetch();
      },
    });
    void engineRef.current.flush();
  }, [session, isActive, attemptId, query]);

  useEffect(
    () => () => {
      engineRef.current?.dispose();
      engineRef.current = null;
      useExamStore.getState().reset();
    },
    [attemptId],
  );

  /* ---------- connectivity ---------- */
  useEffect(() => {
    if (online) void engineRef.current?.flush();
  }, [online]);

  /* ---------- submission (manual or on timeout) ---------- */
  const submit = useCallback(
    async (reason: SubmitReason): Promise<void> => {
      if (submittingRef.current || !engineRef.current) return;
      submittingRef.current = true;
      setSubmitPhase('submitting');
      useExamStore.getState().setLocked(true);

      const engine = engineRef.current;
      const allSaved = await withTimeout(engine.flush(), reason === 'timeout' ? 5_000 : 8_000, false);

      if (!allSaved && reason === 'manual' && !navigator.onLine) {
        // Don't finalise while choices are stuck on the device — let the child reconnect first.
        submittingRef.current = false;
        setSubmitPhase('offline_blocked');
        useExamStore.getState().setLocked(false);
        return;
      }

      const key = loadAttemptState(attemptId).submitKey ?? newIdempotencyKey();
      saveAttemptState(attemptId, { submitKey: key });

      for (let attempt = 0; ; attempt++) {
        try {
          const unsaved = engine.getPending().map((p) => ({ questionId: p.questionId, selectedOptionIds: p.optionIds, clientSeq: p.seq }));
          await examApi.submit(attemptId, reason, key, unsaved);
          goToDone();
          return;
        } catch (e) {
          if (isAttemptClosed(e)) {
            // Already finalised (e.g. by the server deadline policy) — that's a success for the child.
            goToDone();
            return;
          }
          const retryable = e instanceof ApiError && e.isRetryable;
          if (!retryable && reason === 'manual') {
            submittingRef.current = false;
            setSubmitPhase('idle');
            useExamStore.getState().setLocked(false);
            toast('Imtihonni yakunlab boʻlmadi. Birozdan soʻng qayta urinib koʻring.', 'warning');
            return;
          }
          // Timeout submissions keep retrying with the same key; the server will finalise regardless.
          setSubmitPhase('retrying');
          await sleep(Math.min(15_000, 1500 * 2 ** Math.min(attempt, 4)));
        }
      }
    },
    [attemptId, goToDone],
  );

  /* ---------- deadline watcher (server deadline + measured clock offset) ---------- */
  useEffect(() => {
    if (!session || !isActive) return;
    let timer: ReturnType<typeof setTimeout>;
    const check = () => {
      clearTimeout(timer);
      const left = remainingMs(session.expiresAt, clockOffsetMs);
      if (left <= 0) {
        setExpired(true);
        void submit('timeout');
      } else {
        // Wake up at the deadline, but at least every 30s to survive sleeping devices.
        timer = setTimeout(check, Math.min(left + 50, 30_000));
      }
    };
    check();
    document.addEventListener('visibilitychange', check);
    return () => {
      clearTimeout(timer);
      document.removeEventListener('visibilitychange', check);
    };
  }, [session, isActive, clockOffsetMs, submit]);

  /* ---------- gentle time reminders ---------- */
  useEffect(() => {
    if (!session || !isActive) return;
    const marks: Array<[number, string]> = [
      [10 * 60_000, 'Yana 10 daqiqa vaqtingiz bor. Shoshilmasdan davom eting.'],
      [5 * 60_000, '5 daqiqa qoldi. Javobsiz savollarni tekshirib chiqing.'],
      [60_000, '1 daqiqa qoldi. Javoblaringiz avtomatik saqlanadi.'],
    ];
    const timers = marks
      .map(([at, msg]) => {
        const delay = remainingMs(session.expiresAt, clockOffsetMs) - at;
        return delay > 0 ? setTimeout(() => toast(msg, 'info', 6000), delay) : null;
      })
      .filter((t): t is ReturnType<typeof setTimeout> => t !== null);
    return () => timers.forEach(clearTimeout);
  }, [session, isActive, clockOffsetMs]);

  /* ---------- actions ---------- */
  const questions = useMemo(() => session?.questions ?? [], [session]);

  const select = useCallback(
    (questionId: string, optionId: string) => {
      if (useExamStore.getState().locked || !engineRef.current) return;
      useExamStore.getState().setAnswer(questionId, [optionId]);
      engineRef.current.enqueue(questionId, [optionId]);
    },
    [],
  );

  const goTo = useCallback(
    (index: number) => {
      if (index < 0 || index >= questions.length) return;
      useExamStore.getState().setCurrentIndex(index);
      saveAttemptState(attemptId, { currentIndex: index });
    },
    [questions.length, attemptId],
  );

  return {
    query,
    session,
    clockOffsetMs,
    questions,
    currentIndex,
    currentQuestion: questions[currentIndex],
    answers,
    locked,
    sync,
    online,
    refreshFailing,
    waitingForConnection,
    expired,
    submitPhase,
    clearSubmitPhase: () => setSubmitPhase('idle'),
    select,
    goTo,
    next: () => goTo(currentIndex + 1),
    prev: () => goTo(currentIndex - 1),
    submit,
  };
}

export type ExamEngine = ReturnType<typeof useExamEngine>;
