import { type ReactNode } from 'react'
import { Card } from './Card'
import { cn } from '@/lib/cn'

interface PanelProps {
  title: string
  subtitle?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
  bodyClassName?: string
}

// Instrument-panel-style container: mono uppercase title row, optional
// right-aligned controls (view toggles, filters, a menu icon), body below.
export function Panel({ title, subtitle, actions, children, className, bodyClassName }: PanelProps) {
  return (
    <Card className={cn('flex flex-col', className)}>
      <div className="flex items-start justify-between gap-4 px-5 pt-4 pb-3 border-b border-line">
        <div>
          <h2 className="font-mono-heading text-xs text-ink-secondary">{title}</h2>
          {subtitle && <p className="text-xs text-ink-muted mt-1">{subtitle}</p>}
        </div>
        {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
      </div>
      <div className={cn('px-5 py-4 flex-1', bodyClassName)}>{children}</div>
    </Card>
  )
}
