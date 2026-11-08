import { z } from 'zod';
import { examSummarySchema } from '@/features/examination/types';
import { subjectCodeSchema } from '@/types/subject';

export const dashboardSchema = z.object({
  student: z.object({ firstName: z.string() }),
  examinations: z.array(examSummarySchema),
  stats: z.object({
    totalExams: z.number().int().nonnegative(),
    completedExams: z.number().int().nonnegative(),
    /** null until at least one exam has been completed — never fabricated. */
    overallPercent: z.number().min(0).max(100).nullable(),
    subjects: z.array(z.object({ subject: subjectCodeSchema, percent: z.number().min(0).max(100).nullable() })),
  }),
  recentActivity: z.array(
    z.object({
      resultId: z.string(),
      examTitle: z.string(),
      completedAt: z.string(),
      correct: z.number().int().nonnegative(),
      total: z.number().int().positive(),
      status: z.enum(['completed', 'expired']),
    }),
  ),
});
export type Dashboard = z.infer<typeof dashboardSchema>;
