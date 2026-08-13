import { type ReactNode } from 'react'
import { cn } from '@/lib/cn'

type Tone = 'blue' | 'green' | 'purple' | 'gold' | 'silver' | 'neutral' | 'red'

const toneStyles: Record<Tone, string> = {
  blue: 'text-accent-blue border-accent-blue/40 bg-accent-blue/10',
  green: 'text-accent-green border-accent-green/40 bg-accent-green/10',
  purple: 'text-accent-purple border-accent-purple/40 bg-accent-purple/10',
  gold: 'text-accent-gold border-accent-gold/40 bg-accent-gold/10',
  silver: 'text-silver border-silver/40 bg-silver/10',
  neutral: 'text-ink-secondary border-line bg-surface-2',
  red: 'text-red-400 border-red-400/40 bg-red-400/10',
}

interface BadgeProps {
  children: ReactNode
  tone?: Tone
  className?: string
}

export function Badge({ children, tone = 'neutral', className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded px-2 py-0.5 text-xs font-mono font-medium border',
        toneStyles[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}
