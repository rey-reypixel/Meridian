import { Search } from 'lucide-react'
import { type InputHTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

export function SearchInput({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className="relative">
      <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-muted" />
      <input
        className={cn(
          'w-full rounded border border-line bg-surface-2 pl-8 pr-3 py-1.5',
          'text-sm text-ink-primary placeholder:text-ink-muted',
          'focus:outline-none focus:border-accent-blue',
          className,
        )}
        {...props}
      />
    </div>
  )
}
