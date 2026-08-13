import { type ReactNode } from 'react'
import { Card } from './Card'
import { cn } from '@/lib/cn'

type Tone = 'blue' | 'green' | 'purple' | 'gold'

const iconToneStyles: Record<Tone, string> = {
  blue: 'text-accent-blue border-accent-blue/30 bg-accent-blue/10',
  green: 'text-accent-green border-accent-green/30 bg-accent-green/10',
  purple: 'text-accent-purple border-accent-purple/30 bg-accent-purple/10',
  gold: 'text-accent-gold border-accent-gold/30 bg-accent-gold/10',
}

interface MetricCardProps {
  label: string
  value: string
  icon: ReactNode
  tone: Tone
  /** Only render when a real period-over-period comparison exists - no
   * fabricated deltas. Absent by default since no time-series data exists yet. */
  delta?: { value: string; positive: boolean }
  className?: string
}

export function MetricCard({ label, value, icon, tone, delta, className }: MetricCardProps) {
  return (
    <Card className={cn('p-4', className)}>
      <div className="flex items-center gap-2 mb-3">
        <span className={cn('flex h-6 w-6 items-center justify-center rounded border', iconToneStyles[tone])}>
          {icon}
        </span>
        <span className="font-mono-heading text-xs text-ink-secondary">{label}</span>
      </div>
      <div className="font-mono text-2xl text-ink-primary font-semibold">{value}</div>
      {delta && (
        <div className={cn('mt-1 text-xs font-mono', delta.positive ? 'text-accent-green' : 'text-ink-muted')}>
          {delta.positive ? '↑' : '↓'} {delta.value}
        </div>
      )}
    </Card>
  )
}
