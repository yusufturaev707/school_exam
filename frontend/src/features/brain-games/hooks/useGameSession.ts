import { useCallback, useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import { gamesApi } from '../api/gamesApi';
import type { Game, GameDifficulty, ResumeGameResponse, StartGameResponse } from '../types';
import { gamesKeys } from './useGames';
import { clearActiveGame, saveActiveGame, saveLevel } from '../utils/activeGame';
import { ApiError } from '@/lib/http';

type Active = StartGameResponse & { resumeAnswers?: ResumeGameResponse['answers'] };

/**
 * Lifecycle shared by every game: intro → start (server creates content) → play → complete.
 * Completion uses one Idempotency-Key per session and retries transient failures, so a flaky
 * connection or a double tap can never submit twice or lose the result.
 * The open session is remembered per tab, so a reload offers “Davom ettirish” instead of losing it;
 * leaving or restarting closes it on the server (`/abandon`), so nothing stays open there.
 */
export function useGameSession(game: Game | undefined) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [active, setActive] = useState<Active | null>(null);
  const completeKey = useRef<string | null>(null);

  const remember = (data: StartGameResponse) => {
    saveActiveGame({ sessionId: data.session.id, slug: data.session.gameSlug, difficulty: data.session.difficulty, daily: data.session.isDaily, startedAt: Date.now() });
  };

  const start = useMutation({
    mutationFn: ({ difficulty, daily }: { difficulty: GameDifficulty; daily: boolean }) => gamesApi.start(game!.id, difficulty, daily),
    onSuccess: (data, v) => {
      completeKey.current = `${data.session.id}-complete`;
      saveLevel(data.session.gameSlug, v.difficulty);
      remember(data);
      setActive(data);
    },
  });

  const resume = useMutation({
    mutationFn: (sessionId: string) => gamesApi.resume(sessionId),
    onSuccess: (data) => {
      // Same key after a reload: a completion sent just before the reload is not counted twice.
      completeKey.current = `${data.session.id}-complete`;
      setActive({ session: data.session, content: data.content, resumeAnswers: data.answers });
    },
    onError: () => clearActiveGame(), // already finished, abandoned or expired — start fresh
  });

  /** Closes the open session on the server (best effort — the server also drops stale ones). */
  const abandon = useCallback(async (sessionId?: string) => {
    clearActiveGame();
    if (!sessionId) return;
    try {
      await gamesApi.abandon(sessionId);
    } catch {
      /* offline: the server sweeps abandoned sessions itself */
    }
  }, []);

  const complete = useMutation({
    mutationFn: (payload: Record<string, unknown>) => gamesApi.complete(active!.session.id, completeKey.current!, payload),
    retry: (count, error) => count < 4 && error instanceof ApiError && error.isRetryable,
    retryDelay: (attempt) => Math.min(8000, 800 * 2 ** attempt),
    onSuccess: (result) => {
      clearActiveGame();
      queryClient.setQueryData(gamesKeys.result(result.sessionId), result);
      void queryClient.invalidateQueries({ queryKey: gamesKeys.all, predicate: (q) => q.queryKey[1] !== 'result' });
      navigate(`/activities/result/${result.sessionId}`, { replace: true });
    },
  });

  const finish = useCallback(
    (payload: Record<string, unknown> = {}) => {
      if (!active || complete.isPending || complete.isSuccess) return; // one completion per session
      complete.mutate(payload);
    },
    [active, complete],
  );

  return { active, start, resume, abandon, complete, finish };
}
