// Mirrors backend/app/db/schemas.py exactly - confirmed against the live
// schema file, not the illustrative shapes in the design brief.

export interface User {
  id: number
  email: string
  name: string
}

export interface DashboardSummary {
  total_spend_month: number
  optimized_spend_month: number
  total_savings: number
  savings_percentage: number
  requests_optimized: number
  avg_quality_score: number
  total_tokens_processed: number
  avg_latency_ms: number
}

export interface ModelCostBreakdown {
  model: string
  usage_count: number
  total_cost: number
  avg_cost_per_request: number
}

export interface DashboardModels {
  models: ModelCostBreakdown[]
}

export interface RequestDetail {
  id: string
  created_at: string
  original_model: string
  routed_model: string
  original_cost: number
  optimized_cost: number
  savings: number
  optimizations_applied: string[]
  quality_score: number
  input_tokens: number
  output_tokens: number
  latency_ms: number
}

export interface RequestListResponse {
  items: RequestDetail[]
  total: number
  page: number
  page_size: number
}

export interface RequestListParams {
  page?: number
  page_size?: number
  model?: string
  start_date?: string
  end_date?: string
}
