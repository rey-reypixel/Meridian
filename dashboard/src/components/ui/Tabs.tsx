import { cn } from '@/lib/cn'

interface TabsProps {
  options: string[]
  value: string
  onChange: (value: string) => void
}

// Small segmented control - used for DAILY/WEEKLY/MONTHLY-style view toggles
export function Tabs({ options, value, onChange }: TabsProps) {
  return (
    <div className="inline-flex items-center rounded border border-line bg-surface-2 p-0.5">
      {options.map((option) => (
        <button
          key={option}
          onClick={() => onChange(option)}
          className={cn(
            'px-2.5 py-1 text-xs font-mono rounded transition-colors',
            value === option
              ? 'bg-elevated text-ink-primary'
              : 'text-ink-muted hover:text-ink-secondary',
          )}
        >
          {option}
        </button>
      ))}
    </div>
  )
}
