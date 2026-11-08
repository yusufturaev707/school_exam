import { useDailyQuestion, useGameStatistics } from '@/features/brain-games/hooks/useGames';
import { useDashboard } from '@/features/dashboard/api/dashboardApi';
import dayjs from 'dayjs';

/** Faol kunlar ketma-ketligi: bugun yoki kechadan boshlab orqaga uzilmagan kunlar soni. */
export function streakFromDates(dates: string[], today = dayjs()): number {
  const days = new Set(dates.map((d) => dayjs(d).format('YYYY-MM-DD')));
  let cursor = today.startOf('day');
  if (!days.has(cursor.format('YYYY-MM-DD'))) cursor = cursor.subtract(1, 'day');
  let n = 0;
  while (days.has(cursor.format('YYYY-MM-DD'))) {
    n++;
    cursor = cursor.subtract(1, 'day');
  }
  return n;
}

/**
 * Header chiplari uchun 🔥 seriya va ⭐ ball. Hammasi haqiqiy maʼlumotdan hisoblanadi:
 * ball — serverdagi jami ball (oʻyinlar + kunlik bonus + kun savoli), seriya — oʻyin, imtihon yoki kun savoli bilan oʻtgan ketma-ket kunlar.
 */
export function useMotivation() {
  const stats = useGameStatistics();
  const dashboard = useDashboard();
  const question = useDailyQuestion();
  const dates = [
    ...(stats.data?.recent.map((r) => r.completedAt) ?? []),
    ...(dashboard.data?.recentActivity.map((r) => r.completedAt) ?? []),
    ...(question.data?.answer ? [question.data.answer.answeredAt] : []),
  ];
  return {
    stars: stats.data?.totalScore ?? 0,
    streak: streakFromDates(dates),
    ready: stats.isSuccess,
  };
}
