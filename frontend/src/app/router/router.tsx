import { lazy, Suspense, type ReactNode } from 'react';
import { createBrowserRouter, Link, useRouteError } from 'react-router';
import { AppLayout, FocusLayout } from '../layouts/AppLayout';
import { GuestRoute, ProtectedRoute } from './ProtectedRoute';
import { AuthLayout } from '@/features/auth/components/AuthLayout';
import { FullPageLoader } from '@/components/feedback/FullPageLoader';
import { EmptyState } from '@/components/feedback/EmptyState';
import { ErrorState } from '@/components/feedback/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';

const LoginPage = lazy(() => import('@/features/auth/pages/LoginPage'));
const JshshirLoginPage = lazy(() => import('@/features/auth/pages/JshshirLoginPage'));
const QrLoginPage = lazy(() => import('@/features/auth/pages/QrLoginPage'));
const QrLinkPage = lazy(() => import('@/features/auth/pages/QrLinkPage'));
const DashboardPage = lazy(() => import('@/features/dashboard/pages/DashboardPage'));
const ExamListPage = lazy(() => import('@/features/examination/pages/ExamListPage'));
const ExamIntroPage = lazy(() => import('@/features/examination/pages/ExamIntroPage'));
const ExamAgreementPage = lazy(() => import('@/features/examination/pages/ExamAgreementPage'));
const ExamPage = lazy(() => import('@/features/examination/pages/ExamPage'));
const ExamCompletePage = lazy(() => import('@/features/examination/pages/ExamCompletePage'));
const ResultPage = lazy(() => import('@/features/results/pages/ResultPage'));
const ResultsHistoryPage = lazy(() => import('@/features/results/pages/ResultsHistoryPage'));
const LabHomePage = lazy(() => import('@/features/brain-games/pages/LabHomePage'));
const GameCategoryPage = lazy(() => import('@/features/brain-games/pages/CategoryPage'));
const GamePage = lazy(() => import('@/features/brain-games/pages/GamePage'));
const GameResultPage = lazy(() => import('@/features/brain-games/pages/GameResultPage'));
const GameStatsPage = lazy(() => import('@/features/brain-games/pages/StatsPage'));
const AchievementsPage = lazy(() => import('@/features/brain-games/pages/AchievementsPage'));
const ProfilePage = lazy(() => import('@/features/profile/pages/ProfilePage'));
const HelpPage = lazy(() => import('@/features/profile/pages/HelpPage'));

const page = (node: ReactNode) => <Suspense fallback={<Skeleton className="h-64" />}>{node}</Suspense>;
const full = (node: ReactNode) => <Suspense fallback={<FullPageLoader />}>{node}</Suspense>;

function RouteError() {
  const error = useRouteError();
  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <ErrorState error={error} onRetry={() => window.location.reload()} />
    </div>
  );
}

function NotFound() {
  return (
    <EmptyState
      mood="think"
      title="Bu sahifa topilmadi"
      description="Balki manzil notoʻgʻri yozilgandir."
      action={
        <Link to="/" className="inline-flex min-h-12 items-center rounded-[var(--radius-control)] bg-primary px-6 font-bold text-white">
          Bosh sahifaga
        </Link>
      }
    />
  );
}

export const router = createBrowserRouter([
  {
    errorElement: <RouteError />,
    children: [
      // The link printed in ticket QR codes (/qr#t=…). Outside GuestRoute on purpose: it must also
      // work when someone else is still signed in on the phone.
      { path: '/qr', element: <AuthLayout />, children: [{ index: true, element: page(<QrLinkPage />) }] },
      {
        element: <GuestRoute />,
        children: [
          {
            path: '/login',
            element: <AuthLayout />,
            children: [
              { index: true, element: page(<LoginPage />) },
              { path: 'jshshir', element: page(<JshshirLoginPage />) },
              { path: 'qr', element: page(<QrLoginPage />) },
            ],
          },
        ],
      },
      {
        element: <ProtectedRoute />,
        children: [
          // Distraction-free exam: no app navigation at all.
          { path: '/exam/attempt/:attemptId', element: full(<ExamPage />) },
          // Games are full-screen too: the game itself gets the screen.
          { path: '/activities/play/:slug', element: full(<GamePage />) },
          {
            element: <FocusLayout />,
            children: [
              { path: '/exam/:examId', element: page(<ExamIntroPage />) },
              { path: '/exam/:examId/agreement', element: page(<ExamAgreementPage />) },
              { path: '/exam/attempt/:attemptId/done', element: page(<ExamCompletePage />) },
              { path: '/activities/result/:sessionId', element: page(<GameResultPage />) },
            ],
          },
          {
            element: <AppLayout />,
            children: [
              { path: '/', element: page(<DashboardPage />) },
              { path: '/exam', element: page(<ExamListPage />) },
              { path: '/results', element: page(<ResultsHistoryPage />) },
              { path: '/results/:resultId', element: page(<ResultPage />) },
              { path: '/activities', element: page(<LabHomePage />) },
              { path: '/activities/category/:category', element: page(<GameCategoryPage />) },
              { path: '/activities/stats', element: page(<GameStatsPage />) },
              { path: '/activities/achievements', element: page(<AchievementsPage />) },
              { path: '/profile', element: page(<ProfilePage />) },
              { path: '/help', element: page(<HelpPage />) },
              { path: '*', element: <NotFound /> },
            ],
          },
        ],
      },
    ],
  },
]);
