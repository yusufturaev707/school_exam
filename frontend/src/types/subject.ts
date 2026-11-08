import { z } from 'zod';

export const subjectCodeSchema = z.enum(['math', 'iq', 'language']);
export type SubjectCode = z.infer<typeof subjectCodeSchema>;
