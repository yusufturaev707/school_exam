import { create } from 'zustand';
import type { Answers } from '../types';
import type { SyncState } from '../services/answerSyncEngine';

/**
 * Client-only exam state: the student's current selections (optimistic, ahead of the server),
 * navigation position, edit lock and autosave status. Server data (questions, deadline)
 * stays in TanStack Query and is never duplicated here.
 */
interface ExamState {
  attemptId: string | null;
  answers: Answers;
  currentIndex: number;
  locked: boolean;
  sync: SyncState;
  init: (attemptId: string, answers: Answers, currentIndex: number) => void;
  setAnswer: (questionId: string, optionIds: string[]) => void;
  setCurrentIndex: (index: number) => void;
  setLocked: (locked: boolean) => void;
  setSync: (sync: SyncState) => void;
  reset: () => void;
}

const initialSync: SyncState = { phase: 'idle', pendingCount: 0, lastSavedAt: null };

export const useExamStore = create<ExamState>((set) => ({
  attemptId: null,
  answers: {},
  currentIndex: 0,
  locked: false,
  sync: initialSync,
  init: (attemptId, answers, currentIndex) => set({ attemptId, answers, currentIndex, locked: false, sync: initialSync }),
  setAnswer: (questionId, optionIds) => set((s) => ({ answers: { ...s.answers, [questionId]: optionIds } })),
  setCurrentIndex: (currentIndex) => set({ currentIndex }),
  setLocked: (locked) => set({ locked }),
  setSync: (sync) => set({ sync }),
  reset: () => set({ attemptId: null, answers: {}, currentIndex: 0, locked: false, sync: initialSync }),
}));

export function countAnswered(answers: Answers): number {
  return Object.values(answers).filter((ids) => ids.length > 0).length;
}
