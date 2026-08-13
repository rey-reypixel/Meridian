import { type ButtonHTMLAttributes, forwardRef } from 'react'
import { cn } from '@/lib/cn'

export const IconButton = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement>>(
  ({ className, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center h-7 w-7 rounded',
          'text-ink-muted hover:text-ink-primary hover:bg-surface-2',
          'border border-transparent hover:border-line',
          'transition-colors',
          'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent-blue',
          className,
        )}
        {...props}
      />
    )
  },
)
IconButton.displayName = 'IconButton'
