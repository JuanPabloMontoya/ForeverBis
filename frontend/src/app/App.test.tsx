import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const healthyResponse = {
  status: 'healthy',
  database: 'healthy',
  checked_at: '2026-11-07T12:00:00Z',
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Forever BIS shell', () => {
  it('renders the planner shell and all 17 empty equipment slots', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => healthyResponse }))
    render(<App />)
    expect(screen.getByRole('heading', { name: /plan your journey/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Gear slots' })).toBeInTheDocument()
    expect(screen.getAllByText('No item data')).toHaveLength(17)
    expect(await screen.findByText('Backend connected')).toBeInTheDocument()
  })

  it('shows the backend loading state', async () => {
    let resolveRequest!: (value: { ok: boolean; json: () => Promise<typeof healthyResponse> }) => void
    const pendingRequest = new Promise<{ ok: boolean; json: () => Promise<typeof healthyResponse> }>(
      (resolve) => { resolveRequest = resolve },
    )
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(pendingRequest))
    render(<App />)
    expect(screen.getByRole('status', { name: 'Backend connection loading' })).toBeInTheDocument()
    await act(async () => {
      resolveRequest({ ok: true, json: async () => healthyResponse })
    })
    expect(screen.getByText('Backend connected')).toBeInTheDocument()
  })

  it('shows an error state when the backend cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network unavailable')))
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Backend unavailable')
    expect(screen.getByRole('alert')).toHaveTextContent('Network unavailable')
  })

  it('shows database degradation while retaining backend connectivity', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ...healthyResponse, status: 'degraded', database: 'unavailable' }),
    }))
    render(<App />)
    expect(await screen.findByLabelText('Backend connected, database unavailable')).toBeInTheDocument()
    expect(screen.getByText('Database unavailable')).toBeInTheDocument()
  })

  it('keeps the selected level in application state', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => healthyResponse }))
    render(<App />)
    const slider = screen.getByRole('slider', { name: 'Character level' })
    fireEvent.change(slider, { target: { value: '42' } })
    expect(screen.getByText('42', { selector: 'output' })).toBeInTheDocument()
    expect(screen.getByText('17 slots · Level 42')).toBeInTheDocument()
    expect(await screen.findByText('Backend connected')).toBeInTheDocument()
  })
})
