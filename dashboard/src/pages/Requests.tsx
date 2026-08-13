import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Inbox } from 'lucide-react'
import { Panel } from '@/components/ui/Panel'
import { FilterBar, Select } from '@/components/ui/FilterBar'
import { Button } from '@/components/ui/Button'
import { ErrorState } from '@/components/ui/ErrorState'
import { EmptyState } from '@/components/ui/EmptyState'
import { DataTable, type Column } from '@/components/ui/DataTable'
import { ModelBadge } from '@/components/ui/ModelBadge'
import { useRequestsList } from '@/api/requests'
import { formatCurrency, formatDate, formatTime, formatLatency } from '@/lib/format'
import type { RequestDetail } from '@/api/types'

const PAGE_SIZE = 20

// Canonical routing tiers, pulled from backend/app/services/model_router.py's
// MODEL_ORDER - not an arbitrary list, it's the exact set the router chooses from.
const MODEL_OPTIONS = [
  { label: 'Haiku', value: 'claude-haiku' },
  { label: 'Sonnet', value: 'claude-sonnet' },
  { label: 'Opus', value: 'claude-opus' },
]

const columns: Column<RequestDetail>[] = [
  {
    key: 'created_at',
    header: 'TIME',
    render: (row) => (
      <span className="font-mono text-xs text-ink-secondary whitespace-nowrap">
        {formatDate(row.created_at)} {formatTime(row.created_at)}
      </span>
    ),
  },
  {
    key: 'original_model',
    header: 'ORIGINAL',
    render: (row) => <ModelBadge model={row.original_model} />,
  },
  {
    key: 'routed_model',
    header: 'ROUTED',
    render: (row) => <ModelBadge model={row.routed_model} />,
  },
  {
    key: 'optimized_cost',
    header: 'COST',
    render: (row) => <span className="font-mono">{formatCurrency(row.optimized_cost)}</span>,
  },
  {
    key: 'savings',
    header: 'SAVINGS',
    render: (row) => <span className="font-mono text-accent-green">{formatCurrency(row.savings)}</span>,
  },
  {
    key: 'quality_score',
    header: 'QUALITY',
    render: (row) => <span className="font-mono text-ink-secondary">{row.quality_score.toFixed(1)}/10</span>,
  },
  {
    key: 'latency_ms',
    header: 'LATENCY',
    render: (row) => <span className="font-mono text-ink-secondary">{formatLatency(row.latency_ms)}</span>,
  },
]

export function Requests() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [model, setModel] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const { data, isPending, isError, refetch } = useRequestsList({
    page,
    page_size: PAGE_SIZE,
    model: model || undefined,
    start_date: startDate || undefined,
    end_date: endDate || undefined,
  })

  const hasActiveFilters = model || startDate || endDate

  const handleFilterChange = (fn: () => void) => {
    fn()
    setPage(1)
  }

  return (
    <Panel title="REQUESTS" subtitle="All optimized requests" bodyClassName="px-0 py-0">
      <div className="px-5 pt-4">
        <FilterBar>
          <Select
            value={model}
            onChange={(v) => handleFilterChange(() => setModel(v))}
            options={MODEL_OPTIONS}
            placeholder="All models"
          />
          <input
            type="date"
            value={startDate}
            onChange={(e) => handleFilterChange(() => setStartDate(e.target.value))}
            className="rounded border border-line bg-surface-2 px-3 py-1.5 text-sm text-ink-primary focus:outline-none focus:border-accent-blue"
          />
          <span className="text-xs text-ink-muted">to</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => handleFilterChange(() => setEndDate(e.target.value))}
            className="rounded border border-line bg-surface-2 px-3 py-1.5 text-sm text-ink-primary focus:outline-none focus:border-accent-blue"
          />
          {hasActiveFilters && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() =>
                handleFilterChange(() => {
                  setModel('')
                  setStartDate('')
                  setEndDate('')
                })
              }
            >
              Clear filters
            </Button>
          )}
        </FilterBar>
      </div>

      <div className="px-5 pb-4">
        {isError ? (
          <ErrorState
            title="COULD NOT LOAD REQUESTS"
            detail="The requests list failed to load. This may be a transient backend or network issue."
            onRetry={() => refetch()}
          />
        ) : (
          <DataTable
            columns={columns}
            data={data?.items ?? []}
            isLoading={isPending}
            getRowKey={(row) => row.id}
            onRowClick={(row) => navigate(`/requests/${row.id}`)}
            pagination={
              data
                ? { page: data.page, pageSize: data.page_size, total: data.total, onPageChange: setPage }
                : undefined
            }
            emptyState={
              <EmptyState
                icon={<Inbox size={18} />}
                title={hasActiveFilters ? 'NO MATCHING REQUESTS' : 'NO REQUESTS YET'}
                description={
                  hasActiveFilters
                    ? 'No requests match the current filters. Try widening the date range or clearing the model filter.'
                    : 'Processed requests will appear here once Meridian starts optimizing traffic.'
                }
              />
            }
          />
        )}
      </div>
    </Panel>
  )
}
