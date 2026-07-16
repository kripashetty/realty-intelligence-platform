/**
 * T040 — Failing component tests for ApartmentForm.
 * Written before implementation (TDD red phase).
 * ApartmentForm does not exist yet.
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { ApartmentForm } from '../src/components/ApartmentForm'

describe('ApartmentForm', () => {
  it('renders address field', () => {
    render(<ApartmentForm onSubmit={vi.fn()} isLoading={false} />)
    expect(screen.getByLabelText(/address/i)).toBeInTheDocument()
  })

  it('renders size_m2 field', () => {
    render(<ApartmentForm onSubmit={vi.fn()} isLoading={false} />)
    expect(screen.getByLabelText(/size/i)).toBeInTheDocument()
  })

  it('renders rooms field', () => {
    render(<ApartmentForm onSubmit={vi.fn()} isLoading={false} />)
    expect(screen.getByLabelText(/rooms/i)).toBeInTheDocument()
  })

  it('renders floor field', () => {
    render(<ApartmentForm onSubmit={vi.fn()} isLoading={false} />)
    expect(screen.getByLabelText(/floor/i)).toBeInTheDocument()
  })

  it('renders amenities checkboxes', () => {
    render(<ApartmentForm onSubmit={vi.fn()} isLoading={false} />)
    expect(screen.getByLabelText(/balcony/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/parking/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/elevator/i)).toBeInTheDocument()
  })

  it('shows validation error when address is empty on submit', async () => {
    const user = userEvent.setup()
    render(<ApartmentForm onSubmit={vi.fn()} isLoading={false} />)
    await user.click(screen.getByRole('button', { name: /get recommendation/i }))
    await waitFor(() => {
      expect(screen.getByText(/address is required/i)).toBeInTheDocument()
    })
  })

  it('shows validation error when size is below minimum', async () => {
    const user = userEvent.setup()
    render(<ApartmentForm onSubmit={vi.fn()} isLoading={false} />)
    await user.type(screen.getByLabelText(/address/i), 'Invalidenstraße 50, Berlin')
    await user.clear(screen.getByLabelText(/size/i))
    await user.type(screen.getByLabelText(/size/i), '3')
    await user.click(screen.getByRole('button', { name: /get recommendation/i }))
    await waitFor(() => {
      expect(screen.getByText(/at least 5/i)).toBeInTheDocument()
    })
  })

  it('calls onSubmit with correct payload when form is valid', async () => {
    const user = userEvent.setup()
    const mockSubmit = vi.fn()
    render(<ApartmentForm onSubmit={mockSubmit} isLoading={false} />)

    await user.type(screen.getByLabelText(/address/i), 'Invalidenstraße 50, 10115 Berlin')
    await user.clear(screen.getByLabelText(/size/i))
    await user.type(screen.getByLabelText(/size/i), '72')
    await user.clear(screen.getByLabelText(/rooms/i))
    await user.type(screen.getByLabelText(/rooms/i), '3')
    await user.click(screen.getByLabelText(/balcony/i))
    await user.click(screen.getByRole('button', { name: /get recommendation/i }))

    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          address: 'Invalidenstraße 50, 10115 Berlin',
          size_m2: 72,
          rooms: 3,
          amenities: expect.arrayContaining(['balcony']),
        })
      )
    })
  })

  it('disables submit button when isLoading is true', () => {
    render(<ApartmentForm onSubmit={vi.fn()} isLoading={true} />)
    expect(screen.getByRole('button', { name: /loading/i })).toBeDisabled()
  })
})
