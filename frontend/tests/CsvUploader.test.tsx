/**
 * T041 — Failing component tests for CsvUploader.
 * Written before implementation (TDD red phase).
 * CsvUploader does not exist yet.
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CsvUploader } from '../src/components/CsvUploader'

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

describe('CsvUploader', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('renders a file input', () => {
    render(<CsvUploader onImportComplete={vi.fn()} />, { wrapper })
    expect(screen.getByRole('button', { name: /upload/i })).toBeInTheDocument()
  })

  it('shows an error when a non-CSV file is selected', async () => {
    const user = userEvent.setup()
    render(<CsvUploader onImportComplete={vi.fn()} />, { wrapper })
    const file = new File(['not csv'], 'data.txt', { type: 'text/plain' })
    const input = screen.getByTestId('csv-file-input')
    await user.upload(input, file)
    expect(screen.getByText(/csv file/i)).toBeInTheDocument()
  })

  it('calls upload API when a CSV file is selected', async () => {
    const user = userEvent.setup()
    const mockFetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => ({ batch_id: 'test-batch-123', status: 'processing', message: 'Started' }),
    } as Response)
    vi.stubGlobal('fetch', mockFetch)

    render(<CsvUploader onImportComplete={vi.fn()} />, { wrapper })
    const file = new File(['title,address\nFlat,Berlin'], 'listings.csv', { type: 'text/csv' })
    const input = screen.getByTestId('csv-file-input')
    await user.upload(input, file)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/listings/import'),
        expect.objectContaining({ method: 'POST' })
      )
    })
  })

  it('shows processing status after upload starts', async () => {
    const user = userEvent.setup()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ batch_id: 'abc', status: 'processing', message: 'Started' }),
    } as Response))

    render(<CsvUploader onImportComplete={vi.fn()} />, { wrapper })
    const file = new File(['col\nval'], 'listings.csv', { type: 'text/csv' })
    await userEvent.upload(screen.getByTestId('csv-file-input'), file)

    await waitFor(() => {
      expect(screen.getByText(/processing/i)).toBeInTheDocument()
    })
  })

  it('calls onImportComplete when batch status is completed', async () => {
    const onComplete = vi.fn()
    let pollCount = 0
    vi.stubGlobal('fetch', vi.fn().mockImplementation(async (url: string) => {
      if (String(url).includes('/import/')) {
        pollCount++
        return {
          ok: true,
          json: async () => ({
            batch_id: 'abc',
            status: 'completed',
            geocoding_status: 'pending',
            total_rows: 5,
            imported_rows: 5,
            skipped_rows: 0,
            uploaded_at: new Date().toISOString(),
          }),
        } as Response
      }
      return {
        ok: true,
        json: async () => ({ batch_id: 'abc', status: 'processing', message: 'Started' }),
      } as Response
    }))

    render(<CsvUploader onImportComplete={onComplete} />, { wrapper })
    const file = new File(['col\nval'], 'listings.csv', { type: 'text/csv' })
    await userEvent.upload(screen.getByTestId('csv-file-input'), file)

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalled()
    }, { timeout: 5000 })
  })
})
