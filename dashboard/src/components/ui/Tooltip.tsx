import { type ReactNode } from 'react'

export function Tooltip({ label, children }: { label: string; children: ReactNode }) {
  return (
    <span className="relative inline-flex group">
      {children}
      <span
        className={[
          'pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2',
          'whitespace-nowrap rounded border border-line bg-elevated px-2 py-1',
          'text-xs text-ink-secondary font-mono opacity-0 group-hover:opacity-100',
          'transition-opacity z-10',
        ].join(' ')}
      >
        {label}
      </span>
    </span>
  )
}
