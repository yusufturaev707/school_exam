import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';
import { request } from '@/lib/http';
import { examResultSchema, resultSummarySchema } from '../types';

export const resultsApi = {
  list: () => request(z.object({ results: z.array(resultSummarySchema) }), { method: 'GET', url: '/student/results' }).then((r) => r.results),
  get: (resultId: string) => request(examResultSchema, { method: 'GET', url: `/student/results/${encodeURIComponent(resultId)}` }),
};

export function useResults() {
  return useQuery({ queryKey: ['student', 'results'], queryFn: resultsApi.list });
}

export function useResult(resultId: string) {
  return useQuery({ queryKey: ['student', 'results', resultId], queryFn: () => resultsApi.get(resultId), staleTime: 5 * 60_000 });
}
