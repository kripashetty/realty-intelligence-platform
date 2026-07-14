/**
 * T042 — Failing component tests for RecommendationResult.
 * Written before implementation (TDD red phase).
 * RecommendationResult does not exist yet.
 */
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { RecommendationResult } from '../src/components/RecommendationResult'
import type { RecommendationResponse } from '../src/services/api'

const MOCK_RESULT: RecommendationResponse = {
  recommendation_id: 'abc-123',
  recommended_price_eur: 1250.0,
  confidence_range: { low: 1100.0, high: 1420.0 },
  confidence_level: 'high',
  comparable_count: 23,
  percentile_rank: 58.3,
  explanation:
    'Based on 23 comparable apartments in Mitte within 2km, the median asking price is €1,250/month.',
  factors: [
    { name: 'Market Median', description: '23 comparables median €1,250', value: '€1,250/month' },
    { name: 'Supply Level', description: '23 active listings', value: '23 listings' },
    { name: 'Price Range', description: 'IQR €1,100–€1,420', value: '€1,100–€1,420' },
  ],
  explanation_available: true,
  data_freshness: {
    last_upload_at: '2026-07-13T10:30:00Z',
    total_listings: 4821,
    is_stale: false,
  },
  generated_at: '2026-07-13T11:05:22Z',
}

describe('RecommendationResult', () => {
  it('renders the recommended price', () => {
    render(<RecommendationResult result={MOCK_RESULT} />)
    expect(screen.getByText(/1.250/i)).toBeInTheDocument()
  })

  it('renders the confidence range', () => {
    render(<RecommendationResult result={MOCK_RESULT} />)
    expect(screen.getByText(/1.100/i)).toBeInTheDocument()
    expect(screen.getByText(/1.420/i)).toBeInTheDocument()
  })

  it('renders the confidence level badge', () => {
    render(<RecommendationResult result={MOCK_RESULT} />)
    expect(screen.getByText(/high/i)).toBeInTheDocument()
  })

  it('renders comparable count', () => {
    render(<RecommendationResult result={MOCK_RESULT} />)
    expect(screen.getByText(/23/)).toBeInTheDocument()
  })

  it('renders percentile rank', () => {
    render(<RecommendationResult result={MOCK_RESULT} />)
    expect(screen.getByText(/58/)).toBeInTheDocument()
  })

  it('renders explanation text', () => {
    render(<RecommendationResult result={MOCK_RESULT} />)
    expect(screen.getByText(/comparable apartments in Mitte/i)).toBeInTheDocument()
  })

  it('renders all three factors', () => {
    render(<RecommendationResult result={MOCK_RESULT} />)
    expect(screen.getByText('Market Median')).toBeInTheDocument()
    expect(screen.getByText('Supply Level')).toBeInTheDocument()
    expect(screen.getByText('Price Range')).toBeInTheDocument()
  })

  it('does not render explanation when explanation_available is false', () => {
    const result = { ...MOCK_RESULT, explanation_available: false, explanation: null }
    render(<RecommendationResult result={result} />)
    expect(screen.queryByText(/comparable apartments in Mitte/i)).not.toBeInTheDocument()
    expect(screen.getByText(/explanation unavailable/i)).toBeInTheDocument()
  })

  it('shows stale data warning when is_stale is true', () => {
    const result = {
      ...MOCK_RESULT,
      data_freshness: { ...MOCK_RESULT.data_freshness, is_stale: true },
    }
    render(<RecommendationResult result={result} />)
    expect(screen.getByText(/stale/i)).toBeInTheDocument()
  })
})
