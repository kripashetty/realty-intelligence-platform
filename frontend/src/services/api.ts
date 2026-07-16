const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export interface ImportBatchResponse {
  batch_id: string
  status: string
  message: string
}

export interface SkipReason {
  row_number: number
  reason: string
}

export interface BatchStatusResponse {
  batch_id: string
  status: 'processing' | 'completed' | 'failed'
  geocoding_status: 'pending' | 'in_progress' | 'completed'
  uploaded_at: string
  total_rows: number
  imported_rows: number
  skipped_rows: number
  skip_reasons: SkipReason[] | null
}

export interface LatestBatchInfo {
  batch_id: string
  imported_rows: number
  uploaded_at: string
  geocoding_status: string
}

export interface ListingsStatusResponse {
  total_listings: number
  last_upload_at: string | null
  latest_batch: LatestBatchInfo | null
}

export interface ApartmentRequest {
  address: string
  size_m2: number
  rooms: number
  floor?: number
  amenities?: string[]
}

export interface ConfidenceRange {
  low: number
  high: number
}

export interface Factor {
  name: string
  description: string
  value: string
}

export interface DataFreshness {
  last_upload_at: string | null
  total_listings: number
  is_stale: boolean
}

export interface RecommendationResponse {
  recommendation_id: string
  recommended_price_eur: number
  confidence_range: ConfidenceRange
  confidence_level: 'high' | 'medium' | 'low'
  comparable_count: number
  percentile_rank: number
  explanation: string | null
  factors: Factor[]
  explanation_available: boolean
  data_freshness: DataFreshness
  generated_at: string
}

export async function uploadCsv(file: File): Promise<ImportBatchResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}/listings/import`, { method: 'POST', body: form })
  if (!res.ok) throw await res.json()
  return res.json()
}

export async function getBatchStatus(batchId: string): Promise<BatchStatusResponse> {
  const res = await fetch(`${API_BASE}/listings/import/${batchId}`)
  if (!res.ok) throw await res.json()
  return res.json()
}

export async function getListingsStatus(): Promise<ListingsStatusResponse> {
  const res = await fetch(`${API_BASE}/listings/status`)
  if (!res.ok) throw await res.json()
  return res.json()
}

export async function getRecommendation(
  request: ApartmentRequest
): Promise<RecommendationResponse> {
  const res = await fetch(`${API_BASE}/recommendations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!res.ok) throw await res.json()
  return res.json()
}
