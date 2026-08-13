import { type HTMLAttributes, forwardRef } from 'react'
import { cn } from '@/lib/cn'

export const Card = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn('bg-surface border border-line rounded-lg', className)}
        {...props}
      />
    )
  },
)
Card.displayName = 'Card'
