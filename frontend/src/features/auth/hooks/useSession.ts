import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import { authApi } from '../api/authApi';
import { studentSchema, type Student } from '../types';
import { clearExamSessionStorage } from '@/features/examination/services/attemptPersistence';
import { clearGameSessionStorage } from '@/features/brain-games/utils/activeGame';

export const sessionQueryKey = ['auth', 'me'] as const;

/*
 * Instant first paint: the last known profile (name, class, school — no JSHSHIR, no token) is kept
 * in sessionStorage, so pages render right away while /auth/me revalidates in the background.
 * The HttpOnly cookie stays the only proof of identity: if /auth/me says “no session”, the cache is
 * dropped and ProtectedRoute redirects to /login; every data request is still authorised server-side.
 */
const SESSION_CACHE = 'bilimdon:session';

function readCachedStudent(): Student | undefined {
  try {
    const parsed = studentSchema.safeParse(JSON.parse(sessionStorage.getItem(SESSION_CACHE) ?? 'null'));
    return parsed.success ? parsed.data : undefined;
  } catch {
    return undefined;
  }
}

export function cacheStudent(student: Student | null) {
  try {
    if (student) sessionStorage.setItem(SESSION_CACHE, JSON.stringify(student));
    else sessionStorage.removeItem(SESSION_CACHE);
  } catch {
    /* storage unavailable — falls back to waiting for /auth/me */
  }
}

export function useSession() {
  return useQuery({
    queryKey: sessionQueryKey,
    queryFn: async () => {
      const student = await authApi.me();
      cacheStudent(student);
      return student;
    },
    initialData: readCachedStudent,
    initialDataUpdatedAt: 0, // always revalidate the cached profile on first use
    staleTime: 5 * 60_000,
    retry: 1,
  });
}

/** The authenticated student. Only call inside protected routes. */
export function useStudent(): Student {
  const { data } = useSession();
  if (!data) throw new Error('useStudent() used outside an authenticated route');
  return data;
}

function useOnLoggedIn() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  return (student: Student, redirectTo = '/') => {
    cacheStudent(student);
    queryClient.setQueryData(sessionQueryKey, student);
    navigate(redirectTo, { replace: true });
  };
}

export function useJshshirLogin(redirectTo?: string) {
  const onLoggedIn = useOnLoggedIn();
  return useMutation({
    mutationFn: authApi.loginWithJshshir,
    onSuccess: (student) => onLoggedIn(student, redirectTo),
  });
}

export function useQrLogin(redirectTo?: string) {
  const onLoggedIn = useOnLoggedIn();
  return useMutation({
    mutationFn: authApi.loginWithQr,
    onSuccess: (student) => onLoggedIn(student, redirectTo),
  });
}

/**
 * Login from a ticket link (/qr#t=…). Unlike the login pages, this one can run while another
 * pupil is signed in on the device: the backend then replaces the session, and the previous
 * pupil's cached data and unfinished exam/game state must not leak into the new one.
 */
export function useQrLinkLogin() {
  const queryClient = useQueryClient();
  const onLoggedIn = useOnLoggedIn();
  return useMutation({
    mutationFn: authApi.loginWithQr,
    onSuccess: (student) => {
      const previous = queryClient.getQueryData<Student | null>(sessionQueryKey);
      if (previous && previous.id !== student.id) {
        clearExamSessionStorage();
        clearGameSessionStorage();
        queryClient.removeQueries();
      }
      onLoggedIn(student, '/');
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  return useMutation({
    mutationFn: authApi.logout,
    onSettled: () => {
      clearExamSessionStorage();
      clearGameSessionStorage();
      cacheStudent(null);
      queryClient.clear();
      queryClient.setQueryData(sessionQueryKey, null);
      navigate('/login', { replace: true });
    },
  });
}
