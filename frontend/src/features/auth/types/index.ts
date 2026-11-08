import { z } from 'zod';

/** The authenticated student as returned by GET /auth/me. Deliberately excludes JSHSHIR. */
export const studentSchema = z.object({
  id: z.string(),
  firstName: z.string(),
  lastName: z.string(),
  className: z.string().nullable().optional(),
  schoolName: z.string().nullable().optional(),
  photoUrl: z.string().nullable().optional(),
});
export type Student = z.infer<typeof studentSchema>;

export const authResponseSchema = z.object({ student: studentSchema });
export type AuthResponse = z.infer<typeof authResponseSchema>;

/** Backend error codes the auth screens know how to explain. */
export type AuthErrorCode = 'INVALID_CREDENTIALS' | 'QR_INVALID' | 'QR_EXPIRED' | 'QR_ALREADY_USED' | 'RATE_LIMITED';
