import { request, http, ApiError } from '@/lib/http';
import { authResponseSchema, type Student } from '../types';

/**
 * Auth endpoints. The backend sets an HttpOnly, Secure, SameSite session cookie on success;
 * nothing secret ever passes through JavaScript-accessible storage.
 */
export const authApi = {
  async loginWithJshshir(jshshir: string): Promise<Student> {
    const res = await request(authResponseSchema, { method: 'POST', url: '/auth/jshshir', data: { jshshir } });
    return res.student;
  },

  async loginWithQr(token: string): Promise<Student> {
    const res = await request(authResponseSchema, { method: 'POST', url: '/auth/qr', data: { token } });
    return res.student;
  },

  /** Returns the current student, or null when there is no valid session. */
  async me(): Promise<Student | null> {
    try {
      const res = await request(authResponseSchema, { method: 'GET', url: '/auth/me' });
      return res.student;
    } catch (e) {
      if (e instanceof ApiError && e.kind === 'unauthorized') return null;
      throw e;
    }
  },

  async logout(): Promise<void> {
    await http.post('/auth/logout');
  },
};
