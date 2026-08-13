import { useQuery } from '@tanstack/react-query'
import { api } from './client'
import type { RequestDetail, RequestListResponse, RequestListParams } from './types'

function buildQuery(params: RequestListParams): string {
  const search = new URLSearchParams()
  if (params.page) search.set('page', String(params.page))
  if (params.page_size) search.set('page_size', String(params.page_size))
  if (params.model) search.set('model', params.model)
  if (params.start_date) search.set('start_date', params.start_date)
  if (params.end_date) search.set('end_date', params.end_date)
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

export function useRequestsList(params: RequestListParams) {
  return useQuery({
    queryKey: ['requests', params],
    queryFn: () => api.get<RequestListResponse>(`/api/requests${buildQuery(params)}`),
  })
}

export function useRequestDetail(id: string | undefined) {
  return useQuery({
    queryKey: ['requests', 'detail', id],
    queryFn: () => api.get<RequestDetail>(`/api/requests/${id}`),
    enabled: !!id,
    // A 404 here means the ID doesn't exist - retrying won't change that,
    // so don't burn retries (or risk sitting in a paused retry state) on it.
    retry: false,
  })
}
