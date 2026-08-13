import { useNavigate } from 'react-router-dom'
import { DollarSign, Percent, ListChecks, Gauge, Inbox, PieChart as PieChartIcon } from 'lucide-react'
import { Panel } from '@/components/ui/Panel'
import { MetricCard } from '@/components/ui/MetricCard'
import { MetricCardSkeleton, PanelSkeleton } from '@/components/ui/LoadingState'
import { ErrorState } from '@/components/ui/ErrorState'
import { EmptyState } from '@/components/ui/EmptyState'
import { DataTable, type Column } from '@/components/ui/DataTable'
import { ModelBadge } from '@/components/ui/ModelBadge'
import { Button } from '@/components/ui/Button'
import { DonutChart } from '@/components/charts/DonutChart'
import { useDashboardSummary, useDashboardModels } from '@/api/dashboard'
import { useRequestsList } from '@/api/requests'
import { formatCurrency, formatPercent, formatDate, formatTime } from '@/lib/format'
import type { RequestDetail } from '@/api/types'

const recentRequestsColumns: Column<RequestDetail>[] = [
  {
    key: 'created_at',
    header: 'TIME',
    render: (row) => (
      <span className="font-mono text-xs text-ink-secondary">
        {formatDate(row.created_at)} {formatTime(row.created_at)}
      </span>
    ),
  },
  {
    key: 'routed_model',
    header: 'MODEL',
    render: (row) => <ModelBadge model={row.routed_model} />,
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
]

export function Overview() {
  const navigate = useNavigate()
  const summary = useDashboardSummary()
  const models = useDashboardModels()
  const recentRequests = useRequestsList({ page: 1, page_size: 5 })

  return (
    <div className="flex flex-col gap-6">
      {summary.isPending ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <MetricCardSkeleton key={i} />
          ))}
        </div>
      ) : summary.isError ? (
        <ErrorState
          title="COULD NOT LOAD SUMMARY"
          detail="The dashboard summary failed to load. This may be a transient backend or network issue."
          onRetry={() => summary.refetch()}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="TOTAL SAVINGS"
            value={formatCurrency(summary.data.total_savings)}
            icon={<DollarSign size={14} />}
            tone="green"
          />
          <MetricCard
            label="SAVINGS RATE"
            value={formatPercent(summary.data.savings_percentage)}
            icon={<Percent size={14} />}
            tone="blue"
          />
          <MetricCard
            label="REQUESTS OPTIMIZED"
            value={summary.data.requests_optimized.toLocaleString()}
            icon={<ListChecks size={14} />}
            tone="purple"
          />
          <MetricCard
            label="AVG QUALITY SCORE"
            value={`${summary.data.avg_quality_score.toFixed(1)}/10`}
            icon={<Gauge size={14} />}
            tone="gold"
          />
        </div>
      )}

      <Panel title="MODEL MIX" subtitle="Cost distribution across routed models">
        {models.isPending ? (
          <PanelSkeleton />
        ) : models.isError ? (
          <ErrorState
            title="COULD NOT LOAD MODEL MIX"
            detail="The model cost breakdown failed to load."
            onRetry={() => models.refetch()}
          />
        ) : models.data.models.length === 0 ? (
          <EmptyState
            icon={<PieChartIcon size={18} />}
            title="NO MODEL DATA YET"
            description="Model cost distribution will appear here once Meridian routes and processes requests."
          />
        ) : (
          <DonutChart data={models.data.models} />
        )}
      </Panel>

      <Panel
        title="RECENT REQUESTS"
        subtitle="Last 5 processed requests"
        actions={
          <Button size="sm" variant="ghost" onClick={() => navigate('/requests')}>
            View all
          </Button>
        }
        bodyClassName="px-0 py-0"
      >
        {recentRequests.isError ? (
          <div className="px-5 py-4">
            <ErrorState
              title="COULD NOT LOAD REQUESTS"
              detail="The recent requests list failed to load."
              onRetry={() => recentRequests.refetch()}
            />
          </div>
        ) : (
          <div className="px-5 py-4">
            <DataTable
              columns={recentRequestsColumns}
              data={recentRequests.data?.items ?? []}
              isLoading={recentRequests.isPending}
              getRowKey={(row) => row.id}
              onRowClick={(row) => navigate(`/requests/${row.id}`)}
              emptyState={
                <EmptyState
                  icon={<Inbox size={18} />}
                  title="NO REQUESTS YET"
                  description="Processed requests will appear here once Meridian starts optimizing traffic."
                />
              }
            />
          </div>
        )}
      </Panel>
    </div>
  )
}
