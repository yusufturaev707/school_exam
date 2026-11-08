import { z } from 'zod';

/*
 * API shapes for "Bilimlar laboratoriyasi". Field names follow the platform's existing camelCase
 * contract (docs/api-contract.md) rather than the snake_case suggestion in the module brief.
 * Every response is validated with these schemas before the UI touches it.
 */

export const gameCategorySchema = z.enum(['memory', 'logic', 'math', 'attention', 'spatial', 'language']);
export type GameCategory = z.infer<typeof gameCategorySchema>;

export const gameDifficultySchema = z.enum(['easy', 'medium', 'hard']);
export type GameDifficulty = z.infer<typeof gameDifficultySchema>;

/** Which client engine renders a game. New games add a kind + an engine folder. */
export const gameKindSchema = z.enum(['memory', 'missing-number', 'pattern', 'odd-one-out', 'quick-math', 'maze', 'word-search']);
export type GameKind = z.infer<typeof gameKindSchema>;

export const gameSchema = z.object({
  id: z.string(),
  slug: z.string(),
  kind: gameKindSchema,
  title: z.string(),
  description: z.string(),
  category: gameCategorySchema,
  difficulties: z.array(gameDifficultySchema).min(1),
  durationMinutes: z.number().positive(),
  isActive: z.boolean(),
  /** Admin-managed copy, so instructions can change without a frontend release. */
  intro: z.object({ title: z.string(), text: z.string() }),
  instructions: z.array(z.string()),
  /** How many times *this* student completed it (never other students' data). */
  completedCount: z.number().int().nonnegative(),
});
export type Game = z.infer<typeof gameSchema>;

export const gameCategoryInfoSchema = z.object({
  id: gameCategorySchema,
  title: z.string(),
  description: z.string(),
  gameCount: z.number().int().nonnegative(),
  activeCount: z.number().int().nonnegative(),
});
export type GameCategoryInfo = z.infer<typeof gameCategoryInfoSchema>;

/* ---------- game-specific content (each game keeps its own shape) ---------- */

export const memoryContentSchema = z.object({
  kind: z.literal('memory'),
  pairs: z.number().int().positive(),
  cards: z.array(z.object({ id: z.string(), face: z.string() })),
});
export type MemoryContent = z.infer<typeof memoryContentSchema>;

export const missingNumberContentSchema = z.object({
  kind: z.literal('missing-number'),
  questions: z.array(
    z.object({
      id: z.string(),
      /** `null` marks the hidden value. */
      sequence: z.array(z.number().nullable()),
      options: z.array(z.object({ id: z.string(), value: z.number() })).length(4),
    }),
  ),
});
export type MissingNumberContent = z.infer<typeof missingNumberContentSchema>;
export type MissingNumberQuestion = MissingNumberContent['questions'][number];

export const shapeTypeSchema = z.enum(['circle', 'square', 'triangle', 'star', 'diamond', 'hexagon', 'arrow']);
export const shapeColorSchema = z.enum(['teal', 'yellow', 'pink', 'blue', 'orange', 'purple']);
export const shapeSchema = z.object({
  type: shapeTypeSchema,
  color: shapeColorSchema,
  rotation: z.number(),
  count: z.number().int().min(1).max(4),
});
export type Shape = z.infer<typeof shapeSchema>;
export type ShapeType = z.infer<typeof shapeTypeSchema>;
export type ShapeColor = z.infer<typeof shapeColorSchema>;

export const patternContentSchema = z.object({
  kind: z.literal('pattern'),
  questions: z.array(
    z.object({
      id: z.string(),
      sequence: z.array(shapeSchema.nullable()),
      options: z.array(z.object({ id: z.string(), shape: shapeSchema })).length(4),
    }),
  ),
});
export type PatternContent = z.infer<typeof patternContentSchema>;
export type PatternQuestion = PatternContent['questions'][number];

export const gameContentSchema = z.discriminatedUnion('kind', [memoryContentSchema, missingNumberContentSchema, patternContentSchema]);
export type GameContent = z.infer<typeof gameContentSchema>;

/* ---------- sessions ---------- */

export const gameSessionSchema = z.object({
  id: z.string(),
  gameId: z.string(),
  gameSlug: z.string(),
  difficulty: gameDifficultySchema,
  isDaily: z.boolean(),
  startedAt: z.string(),
  completedAt: z.string().nullable(),
  status: z.enum(['in_progress', 'completed', 'abandoned']),
  score: z.number().int().nonnegative(),
  correctAnswers: z.number().int().nonnegative(),
  totalQuestions: z.number().int().nonnegative(),
});
export type GameSession = z.infer<typeof gameSessionSchema>;

export const startGameResponseSchema = z.object({ session: gameSessionSchema, content: gameContentSchema });
export type StartGameResponse = z.infer<typeof startGameResponseSchema>;

/** GET /games/sessions/:id — an unfinished session plus the answers the server already checked. */
export const resumeGameResponseSchema = startGameResponseSchema.extend({
  answers: z.array(
    z.object({ questionId: z.string(), optionId: z.string(), correct: z.boolean(), correctOptionId: z.string(), explanation: z.string() }),
  ),
});
export type ResumeGameResponse = z.infer<typeof resumeGameResponseSchema>;

export const answerResponseSchema = z.object({
  questionId: z.string(),
  correct: z.boolean(),
  correctOptionId: z.string(),
  explanation: z.string(),
  score: z.number().int().nonnegative(),
  correctAnswers: z.number().int().nonnegative(),
});
export type AnswerResponse = z.infer<typeof answerResponseSchema>;

/* ---------- achievements, results, daily, statistics ---------- */

export const achievementSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string(),
  icon: z.string(),
  unlockedAt: z.string().nullable(),
  progress: z.object({ current: z.number().int().nonnegative(), target: z.number().int().positive() }),
  /** No active game can earn it yet — shown locked with a "Tez orada" label. */
  comingSoon: z.boolean().default(false),
});
export type Achievement = z.infer<typeof achievementSchema>;

export const gameResultSchema = z.object({
  sessionId: z.string(),
  game: z.object({ id: z.string(), slug: z.string(), title: z.string(), category: gameCategorySchema }),
  difficulty: gameDifficultySchema,
  score: z.number().int().nonnegative(),
  /** Daily-challenge bonus stars, on top of `score`. */
  bonus: z.number().int().nonnegative().default(0),
  maxScore: z.number().int().nonnegative(),
  correctAnswers: z.number().int().nonnegative(),
  totalQuestions: z.number().int().nonnegative(),
  durationSeconds: z.number().int().nonnegative(),
  moves: z.number().int().nonnegative().nullable(),
  completedAt: z.string(),
  isDaily: z.boolean(),
  newAchievements: z.array(achievementSchema),
});
export type GameResult = z.infer<typeof gameResultSchema>;

export const dailyChallengeSchema = z.object({
  date: z.string(),
  game: gameSchema,
  difficulty: gameDifficultySchema,
  completed: z.boolean(),
  completedAt: z.string().nullable(),
  /** Bonus stars granted on completion (0 = no bonus). */
  bonus: z.number().int().nonnegative().default(0),
});
export type DailyChallenge = z.infer<typeof dailyChallengeSchema>;

/** “Kun savoli”: the server keeps the answer and accepts only the first one per day. */
export const dailyQuestionSchema = z.object({
  date: z.string(),
  question: z.object({ id: z.string(), prompt: z.string(), sequence: z.string(), options: z.array(z.object({ id: z.string(), label: z.string() })) }),
  points: z.number().int().nonnegative(),
  answer: z
    .object({
      selectedOptionId: z.string(),
      correct: z.boolean(),
      correctOptionId: z.string(),
      explanation: z.string(),
      pointsEarned: z.number().int().nonnegative(),
      answeredAt: z.string(),
    })
    .nullable(),
});
export type DailyQuestion = z.infer<typeof dailyQuestionSchema>;

export const gameStatisticsSchema = z.object({
  totalCompleted: z.number().int().nonnegative(),
  totalScore: z.number().int().nonnegative(),
  categories: z.array(z.object({ category: gameCategorySchema, completed: z.number().int().nonnegative() })),
  games: z.array(
    z.object({
      gameId: z.string(),
      slug: z.string(),
      title: z.string(),
      category: gameCategorySchema,
      completed: z.number().int().nonnegative(),
      bestScore: z.number().int().nonnegative().nullable(),
      maxScore: z.number().int().nonnegative().nullable(),
    }),
  ),
  recent: z.array(
    z.object({
      sessionId: z.string(),
      slug: z.string(),
      title: z.string(),
      category: gameCategorySchema,
      score: z.number().int().nonnegative(),
      bonus: z.number().int().nonnegative().default(0),
      maxScore: z.number().int().nonnegative(),
      completedAt: z.string(),
    }),
  ),
});
export type GameStatistics = z.infer<typeof gameStatisticsSchema>;
