import { useQuery } from '@tanstack/react-query';
import { request } from '@/lib/http';
import { dashboardSchema } from '../types';

export const dashboardApi = {
  get: () => request(dashboardSchema, { method: 'GET', url: '/student/dashboard' }),
};

export function useDashboard() {
  return useQuery({ queryKey: ['student', 'dashboard'], queryFn: dashboardApi.get });
}
