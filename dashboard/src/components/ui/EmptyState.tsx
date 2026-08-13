import { type ReactNode } from 'react'

interface EmptyStateProps {
  icon: ReactNode
  title: string
  description: string
}

// Restrained technical messaging per the design brief - no "nothing here
// yet!" cutesy copy. e.g. title="NO REQUEST DATA YET", description=
// "Optimization activity will appear here once Meridian processes requests."
export function EmptyState({ icon, title, description }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-12 px-6">
      <div className="flex h-10 w-10 items-center justify-center rounded border border-line text-ink-muted mb-4">
        {icon}
      </div>
      <h3 className="font-mono-heading text-sm text-ink-secondary mb-1.5">{title}</h3>
      <p className="text-xs text-ink-muted max-w-xs">{description}</p>
    </div>
  )
}
