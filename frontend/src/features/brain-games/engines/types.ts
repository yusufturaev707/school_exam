import type { GameSession, ResumeGameResponse } from '../types';

/** Contract every game engine view implements; the page owns intro, exit and completion. */
export interface GameEngineProps<TContent> {
  session: GameSession;
  content: TContent;
  /** Answers the server already checked — set when the session is continued after a reload. */
  resumeAnswers?: ResumeGameResponse['answers'];
  title: string;
  onExit: () => void;
  /** Game-specific evidence for the backend (never a score). Safe to call more than once. */
  onFinish: (payload?: Record<string, unknown>) => void;
  finishing: boolean;
  finishError: string | null;
}
