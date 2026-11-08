import { Navigate, Outlet, useLocation } from 'react-router';
import { useSession } from '@/features/auth/hooks/useSession';
import { FullPageLoader } from '@/components/feedback/FullPageLoader';
import { ErrorState } from '@/components/feedback/ErrorState';

/** Gate for the authenticated area. The session itself lives in an HttpOnly cookie; we only ask the backend who we are. */
export function ProtectedRoute() {
  const { data: student, isPending, isError, error, refetch } = useSession();
  const location = useLocation();

  if (isPending) return <FullPageLoader />;
  // A cached profile keeps the app usable through a flaky /auth/me; data requests are authorised on their own.
  if (isError && !student) {
    return (
      <div className="mx-auto max-w-md px-4 py-16">
        <ErrorState error={error} onRetry={() => void refetch()} />
      </div>
    );
  }
  if (!student) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <Outlet />;
}

/** Keeps signed-in students out of the login screens. */
export function GuestRoute() {
  const { data: student, isPending } = useSession();
  if (isPending) return <FullPageLoader />;
  if (student) return <Navigate to="/" replace />;
  return <Outlet />;
}
