import { AlertTriangle } from 'lucide-react'
import { Button } from './Button'

interface ErrorStateProps {
  title: string
  detail?: string
  onRetry?: () => void
}

// Per the brief: explain WHAT failed, WHY it may have failed, WHAT the
// user can do - never a bare "Something went wrong."
export function ErrorState({ title, detail, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-12 px-6">
      <div className="flex h-10 w-10 items-center justify-center rounded border border-red-400/40 bg-red-400/10 text-red-400 mb-4">
        <AlertTriangle size={18} />
      </div>
      <h3 className="font-mono-heading text-sm text-red-400 mb-1.5">{title}</h3>
      {detail && <p className="text-xs text-ink-muted max-w-sm mb-4">{detail}</p>}
      {onRetry && (
        <Button size="sm" variant="secondary" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  )
}
