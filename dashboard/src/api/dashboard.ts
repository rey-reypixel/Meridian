import { useQuery } from '@tanstack/react-query'
import { api } from './client'
import type { DashboardSummary, DashboardModels } from './types'

export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: () => api.get<DashboardSummary>('/api/dashboard/summary'),
  })
}

export function useDashboardModels() {
  return useQuery({
    queryKey: ['dashboard', 'models'],
    queryFn: () => api.get<DashboardModels>('/api/dashboard/models'),
  })
}
