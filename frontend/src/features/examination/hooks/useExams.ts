import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import { examApi } from '../api/examApi';

export const availableExamsKey = ['examination', 'available'] as const;

export function useAvailableExams() {
  return useQuery({ queryKey: availableExamsKey, queryFn: examApi.listAvailable });
}

export function useExam(examId: string) {
  const query = useAvailableExams();
  return { ...query, exam: query.data?.find((e) => e.id === examId) };
}

/** Starts (or resumes) the attempt on the backend; the timer starts only after the backend confirms. */
export function useStartExam() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: examApi.start,
    onSuccess: ({ attemptId }) => {
      // Exam status is now "in_progress": stale "available" data would let a back-swipe land on the agreement again.
      void queryClient.invalidateQueries({ queryKey: availableExamsKey });
      void queryClient.invalidateQueries({ queryKey: ['student', 'dashboard'] });
      navigate(`/exam/attempt/${attemptId}`, { replace: true });
    },
  });
}
