import { PieChart, Pie, Cell, Tooltip as RechartsTooltip } from 'recharts'
import { colorForModel } from '@/lib/tokens'
import { formatCurrency, truncateModelName } from '@/lib/format'
import type { ModelCostBreakdown } from '@/api/types'

interface DonutChartProps {
  data: ModelCostBreakdown[]
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: ModelCostBreakdown }> }) {
  if (!active || !payload?.length) return null
  const item = payload[0].payload
  return (
    <div className="rounded border border-line bg-elevated px-3 py-2 text-xs font-mono">
      <div className="text-ink-primary font-medium mb-0.5">{truncateModelName(item.model)}</div>
      <div className="text-ink-secondary">{formatCurrency(item.total_cost)}</div>
      <div className="text-ink-muted">{item.usage_count} requests</div>
    </div>
  )
}

export function DonutChart({ data }: DonutChartProps) {
  return (
    <div className="flex items-center gap-6">
      <PieChart width={160} height={160}>
        <Pie
          data={data}
          dataKey="total_cost"
          nameKey="model"
          cx="50%"
          cy="50%"
          innerRadius={50}
          outerRadius={72}
          paddingAngle={data.length > 1 ? 2 : 0}
          stroke="none"
        >
          {data.map((entry) => (
            <Cell key={entry.model} fill={colorForModel(entry.model)} />
          ))}
        </Pie>
        <RechartsTooltip content={<CustomTooltip />} />
      </PieChart>
      <div className="flex flex-col gap-2.5">
        {data.map((entry) => (
          <div key={entry.model} className="flex items-center gap-2 text-xs font-mono">
            <span
              className="h-2 w-2 rounded-full shrink-0"
              style={{ backgroundColor: colorForModel(entry.model) }}
            />
            <span className="text-ink-secondary">{truncateModelName(entry.model)}</span>
            <span className="text-ink-muted">{formatCurrency(entry.total_cost)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
