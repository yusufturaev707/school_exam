import { useCallback, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { gamesApi } from '../api/gamesApi';
import type { AnswerResponse, ResumeGameResponse } from '../types';
import { ApiError } from '@/lib/http';

/**
 * Round state for games where each step is checked by the server (Missing Number, Pattern Master…).
 * The client never knows the right answer in advance: it shows the server's verdict + explanation.
 */
export function useQuizRound(sessionId: string, total: number, questionIds: string[] = [], resume?: { answers: ResumeGameResponse['answers']; score: number; correct: number }) {
  // After a reload: continue at the first unanswered question; if all were answered, show the last verdict
  // so "Natijani koʻrish" is one tap away.
  const init = (() => {
    if (!resume || resume.answers.length === 0) return { index: 0, selected: null, feedback: null };
    const answered = new Set(resume.answers.map((a) => a.questionId));
    const firstOpen = questionIds.findIndex((id) => !answered.has(id));
    if (firstOpen >= 0) return { index: firstOpen, selected: null, feedback: null };
    const last = resume.answers.find((a) => a.questionId === questionIds[total - 1]) ?? resume.answers.at(-1)!;
    return {
      index: total - 1,
      selected: last.optionId,
      feedback: { questionId: last.questionId, correct: last.correct, correctOptionId: last.correctOptionId, explanation: last.explanation, score: resume.score, correctAnswers: resume.correct },
    };
  })();
  const [index, setIndex] = useState(init.index);
  const [selected, setSelected] = useState<string | null>(init.selected);
  const [feedback, setFeedback] = useState<AnswerResponse | null>(init.feedback);
  const [score, setScore] = useState(resume?.score ?? 0);
  const [correct, setCorrect] = useState(resume?.correct ?? 0);

  const answer = useMutation({
    mutationFn: (v: { questionId: string; optionId: string }) => gamesApi.answer(sessionId, v.questionId, v.optionId),
    retry: (count, error) => count < 2 && error instanceof ApiError && error.isRetryable,
    onSuccess: (r) => {
      setFeedback(r);
      setScore(r.score);
      setCorrect(r.correctAnswers);
    },
  });

  const choose = useCallback(
    (questionId: string, optionId: string) => {
      if (feedback || answer.isPending) return; // one answer per question, no double taps
      setSelected(optionId);
      answer.mutate({ questionId, optionId });
    },
    [feedback, answer],
  );

  // Ref, not state: a stale closure (e.g. a fading-out panel button) must not skip an unanswered question.
  const answered = useRef(false);
  answered.current = feedback !== null;

  const next = useCallback(() => {
    if (!answered.current) return;
    answered.current = false;
    setIndex((i) => Math.min(total - 1, i + 1));
    setSelected(null);
    setFeedback(null);
    answer.reset();
  }, [total, answer]);

  return {
    index,
    selected,
    feedback,
    pending: answer.isPending,
    error: answer.isError ? answer.error : null,
    score,
    correct,
    answeredCount: index + (feedback ? 1 : 0),
    isLast: index === total - 1,
    choose,
    next,
  };
}
