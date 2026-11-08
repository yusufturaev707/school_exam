import { z } from 'zod';
import { contentSchema } from '@/types/content';
import { subjectCodeSchema } from '@/types/subject';
import { answerOptionSchema } from '@/features/examination/types';

const subjectResultSchema = z.object({
  subject: subjectCodeSchema,
  correct: z.number().int().nonnegative(),
  incorrect: z.number().int().nonnegative(),
  unanswered: z.number().int().nonnegative(),
  total: z.number().int().positive(),
  percent: z.number().min(0).max(100),
});
export type SubjectResult = z.infer<typeof subjectResultSchema>;

const reviewItemSchema = z.object({
  questionId: z.string(),
  number: z.number().int().positive(),
  subject: subjectCodeSchema,
  prompt: contentSchema,
  passage: contentSchema.nullable().optional(),
  options: z.array(answerOptionSchema),
  selectedOptionIds: z.array(z.string()),
  correctOptionIds: z.array(z.string()),
  explanation: contentSchema.nullable().optional(),
});
export type ReviewItem = z.infer<typeof reviewItemSchema>;

/** All values are calculated by the backend; the frontend only displays them. */
export const examResultSchema = z.object({
  id: z.string(),
  attemptId: z.string(),
  examTitle: z.string(),
  completedAt: z.string(),
  finishReason: z.enum(['manual', 'timeout']),
  totals: z.object({
    correct: z.number().int().nonnegative(),
    incorrect: z.number().int().nonnegative(),
    unanswered: z.number().int().nonnegative(),
    total: z.number().int().positive(),
    score: z.number().nonnegative(),
    maxScore: z.number().positive(),
    percent: z.number().min(0).max(100),
  }),
  subjects: z.array(subjectResultSchema),
  /** Question-level review is controlled by backend policy; when disabled, `items` is omitted. */
  review: z.object({ enabled: z.boolean(), items: z.array(reviewItemSchema).optional() }),
});
export type ExamResult = z.infer<typeof examResultSchema>;

export const resultSummarySchema = z.object({
  id: z.string(),
  examTitle: z.string(),
  completedAt: z.string(),
  correct: z.number().int().nonnegative(),
  total: z.number().int().positive(),
  percent: z.number().min(0).max(100),
});
export type ResultSummary = z.infer<typeof resultSummarySchema>;
