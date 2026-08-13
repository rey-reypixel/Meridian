import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Sparkles, Zap } from 'lucide-react'
import { Panel } from '@/components/ui/Panel'
import { IconButton } from '@/components/ui/IconButton'
import { ModelBadge } from '@/components/ui/ModelBadge'
import { Badge } from '@/components/ui/Badge'
import { PanelSkeleton } from '@/components/ui/LoadingState'
import { ErrorState } from '@/components/ui/ErrorState'
import { EmptyState } from '@/components/ui/EmptyState'
import { useRequestDetail } from '@/api/requests'
import { formatCurrency, formatDate, formatTime, formatLatency, formatTokens } from '@/lib/format'

function formatMechanismName(mechanism: string): string {
  return mechanism.replace(/_/g, ' ').toUpperCase()
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div>
      <div className="font-mono-heading text-xs text-ink-muted mb-1">{label}</div>
      <div className={`font-mono text-lg ${accent ?? 'text-ink-primary'}`}>{value}</div>
    </div>
  )
}

export function RequestDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data, isPending, isError, refetch } = useRequestDetail(id)

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <IconButton onClick={() => navigate('/requests')} aria-label="Back to requests">
          <ArrowLeft size={16} />
        </IconButton>
        <div>
          <h1 className="font-mono-heading text-sm text-ink-primary">REQUEST DETAIL</h1>
          {data && <p className="text-xs text-ink-muted font-mono mt-0.5">{data.id}</p>}
        </div>
      </div>

      {isPending ? (
        <PanelSkeleton />
      ) : isError ? (
        <ErrorState
          title="COULD NOT LOAD REQUEST"
          detail="This request may not exist, or the request failed to load."
          onRetry={() => refetch()}
        />
      ) : (
        <>
          <Panel title="ROUTING" subtitle={`${formatDate(data.created_at)} ${formatTime(data.created_at)}`}>
            <div className="flex items-center gap-4">
              <ModelBadge model={data.original_model} />
              <ArrowRight size={14} className="text-ink-muted shrink-0" />
              <ModelBadge model={data.routed_model} />
            </div>
          </Panel>

          <Panel title="COST & PERFORMANCE">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-6">
              <Stat label="ORIGINAL COST" value={formatCurrency(data.original_cost)} />
              <Stat label="OPTIMIZED COST" value={formatCurrency(data.optimized_cost)} />
              <Stat label="SAVINGS" value={formatCurrency(data.savings)} accent="text-accent-green" />
              <Stat label="QUALITY SCORE" value={`${data.quality_score.toFixed(1)}/10`} />
              <Stat label="LATENCY" value={formatLatency(data.latency_ms)} />
              <Stat
                label="TOKENS (IN / OUT)"
                value={`${formatTokens(data.input_tokens)} / ${formatTokens(data.output_tokens)}`}
              />
            </div>
          </Panel>

          <Panel title="OPTIMIZATIONS APPLIED" subtitle="Mechanisms that fired for this request">
            {data.optimizations_applied.length === 0 ? (
              <EmptyState
                icon={<Zap size={18} />}
                title="NO OPTIMIZATIONS APPLIED"
                description="This request was processed without any active optimization mechanisms."
              />
            ) : (
              <div className="flex flex-wrap gap-2">
                {data.optimizations_applied.map((mechanism) => (
                  <Badge key={mechanism} tone="blue" className="gap-1.5">
                    <Sparkles size={11} />
                    {formatMechanismName(mechanism)}
                  </Badge>
                ))}
              </div>
            )}
          </Panel>
        </>
      )}
    </div>
  )
}
