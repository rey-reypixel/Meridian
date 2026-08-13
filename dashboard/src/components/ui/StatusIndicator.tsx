import { cn } from '@/lib/cn'

type Status = 'healthy' | 'warning' | 'error'

const statusStyles: Record<Status, string> = {
  healthy: 'bg-accent-green',
  warning: 'bg-accent-gold',
  error: 'bg-red-400',
}

export function StatusIndicator({ status, label }: { status: Status; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className={cn('h-1.5 w-1.5 rounded-full', statusStyles[status])} />
      <span className="font-mono-heading text-xs text-ink-secondary">{label}</span>
    </div>
  )
}
