import { useEffect, type ReactNode } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MotionConfig } from 'motion/react';
import { queryClient } from '@/lib/queryClient';
import { setUnauthorizedHandler } from '@/lib/http';
import { cacheStudent, sessionQueryKey } from '@/features/auth/hooks/useSession';
import { Toaster } from '@/components/feedback/Toaster';
import { toast } from '@/components/feedback/toastStore';

export function AppProviders({ children }: { children: ReactNode }) {
  useEffect(() => {
    // Centralised session-expiry handling: any 401 drops the cached session → ProtectedRoute redirects to /login.
    setUnauthorizedHandler(() => {
      if (queryClient.getQueryData(sessionQueryKey)) {
        toast('Sessiya tugadi. Iltimos, qaytadan kiring.', 'info');
      }
      cacheStudent(null);
      queryClient.setQueryData(sessionQueryKey, null);
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      {/* Honour the OS "reduce motion" setting for every animation. */}
      <MotionConfig reducedMotion="user">
        {children}
        <Toaster />
      </MotionConfig>
    </QueryClientProvider>
  );
}
