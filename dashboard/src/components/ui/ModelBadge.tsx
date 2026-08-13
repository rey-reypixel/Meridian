import { Badge } from './Badge'
import { truncateModelName } from '@/lib/format'

const modelTone: Record<string, 'blue' | 'purple' | 'silver'> = {
  'claude-haiku': 'blue',
  'claude-sonnet': 'purple',
  'claude-opus': 'silver',
}

export function ModelBadge({ model }: { model: string }) {
  return <Badge tone={modelTone[model] ?? 'neutral'}>{truncateModelName(model)}</Badge>
}
