import { cn } from '@/lib/cn'

function SkeletonLine({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded bg-surface-2', className)} />
}

// Matches the shape of MetricCard's KPI row
export function MetricCardSkeleton() {
  return (
    <div className="bg-surface border border-line rounded-lg p-4">
      <SkeletonLine className="h-6 w-6 rounded mb-3" />
      <SkeletonLine className="h-7 w-24 mb-2" />
      <SkeletonLine className="h-3 w-16" />
    </div>
  )
}

// Matches DataTable's row shape
export function TableRowSkeleton({ columns = 6 }: { columns?: number }) {
  return (
    <tr className="border-b border-line">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <SkeletonLine className="h-4 w-full" />
        </td>
      ))}
    </tr>
  )
}

export function PanelSkeleton() {
  return (
    <div className="bg-surface border border-line rounded-lg p-5">
      <SkeletonLine className="h-3 w-32 mb-4" />
      <SkeletonLine className="h-40 w-full" />
    </div>
  )
}
