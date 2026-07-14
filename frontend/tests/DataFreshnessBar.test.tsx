/**
 * T043 — Failing component tests for DataFreshnessBar.
 * Written before implementation (TDD red phase).
 * DataFreshnessBar does not exist yet.
 */
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DataFreshnessBar } from '../src/components/DataFreshnessBar'
import type { ListingsStatusResponse } from '../src/services/api'

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

const FRESH_STATUS: ListingsStatusResponse = {
  total_listings: 4821,
  last_upload_at: new Date(Date.now() - 3600_000).toISOString(), // 1 hour ago
  latest_batch: {
    batch_id: 'abc-123',
    imported_rows: 1018,
    uploaded_at: new Date(Date.now() - 3600_000).toISOString(),
    geocoding_status: 'completed',
  },
}

const STALE_STATUS: ListingsStatusResponse = {
  total_listings: 1000,
  last_upload_at: new Date(Date.now() - 72 * 3600_000).toISOString(), // 3 days ago
  latest_batch: {
    batch_id: 'xyz-456',
    imported_rows: 1000,
    uploaded_at: new Date(Date.now() - 72 * 3600_000).toISOString(),
    geocoding_status: 'completed',
  },
}

const EMPTY_STATUS: ListingsStatusResponse = {
  total_listings: 0,
  last_upload_at: null,
  latest_batch: null,
}

describe('DataFreshnessBar', () => {
  it('shows listing count when data is available', () => {
    render(<DataFreshnessBar status={FRESH_STATUS} />, { wrapper })
    expect(screen.getByText(/4.821|4,821/)).toBeInTheDocument()
  })

  it('shows last upload time', () => {
    render(<DataFreshnessBar status={FRESH_STATUS} />, { wrapper })
    expect(screen.getByText(/hour|ago/i)).toBeInTheDocument()
  })

  it('shows stale warning when is_stale is true', () => {
    render(<DataFreshnessBar status={STALE_STATUS} isStale={true} />, { wrapper })
    expect(screen.getByText(/stale|outdated|upload/i)).toBeInTheDocument()
  })

  it('shows empty state prompt when no data uploaded', () => {
    render(<DataFreshnessBar status={EMPTY_STATUS} />, { wrapper })
    expect(screen.getByText(/no data|upload/i)).toBeInTheDocument()
  })

  it('does not show stale warning when data is fresh', () => {
    render(<DataFreshnessBar status={FRESH_STATUS} isStale={false} />, { wrapper })
    expect(screen.queryByText(/stale/i)).not.toBeInTheDocument()
  })
})
