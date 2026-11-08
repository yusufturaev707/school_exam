import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { gamesApi } from '../api/gamesApi';
import { ApiError } from '@/lib/http';

export const gamesKeys = {
  all: ['games'] as const,
  list: ['games', 'list'] as const,
  categories: ['games', 'categories'] as const,
  game: (slug: string) => ['games', 'game', slug] as const,
  daily: ['games', 'daily'] as const,
  dailyQuestion: ['games', 'daily-question'] as const,
  result: (sessionId: string) => ['games', 'result', sessionId] as const,
  statistics: ['games', 'statistics'] as const,
  achievements: ['games', 'achievements'] as const,
};

export const useGamesList = () => useQuery({ queryKey: gamesKeys.list, queryFn: gamesApi.list });
export const useGameCategories = () => useQuery({ queryKey: gamesKeys.categories, queryFn: gamesApi.categories, staleTime: 10 * 60_000 });
export const useGame = (slug: string) => useQuery({ queryKey: gamesKeys.game(slug), queryFn: () => gamesApi.get(slug) });
export const useDailyChallenge = () => useQuery({ queryKey: gamesKeys.daily, queryFn: gamesApi.daily });
export const useDailyQuestion = () => useQuery({ queryKey: gamesKeys.dailyQuestion, queryFn: gamesApi.dailyQuestion });

/** Sends the (single) answer; on success the stored answer replaces the cache and the ⭐ total is refreshed. */
export function useAnswerDailyQuestion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (v: { questionId: string; optionId: string }) => gamesApi.answerDailyQuestion(v.questionId, v.optionId),
    retry: (count, error) => count < 2 && error instanceof ApiError && error.isRetryable,
    onSuccess: (data) => {
      queryClient.setQueryData(gamesKeys.dailyQuestion, data);
      void queryClient.invalidateQueries({ queryKey: gamesKeys.statistics });
    },
  });
}

export const useGameStatistics =() => useQuery({ queryKey: gamesKeys.statistics, queryFn: gamesApi.statistics });
export const useAchievements = () => useQuery({ queryKey: gamesKeys.achievements, queryFn: gamesApi.achievements });
export const useGameResult = (sessionId: string) =>
  useQuery({ queryKey: gamesKeys.result(sessionId), queryFn: () => gamesApi.result(sessionId), staleTime: Infinity });
