import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import LevelSlider from './LevelSlider'

describe('LevelSlider', () => {
  it('renders level 1 with the full supported range', () => {
    render(<LevelSlider value={1} onChange={vi.fn()} />)
    const slider = screen.getByRole('slider', { name: 'Character level' })
    expect(slider).toHaveAttribute('min', '1')
    expect(slider).toHaveAttribute('max', '60')
    expect(slider).toHaveAttribute('step', '1')
    expect(slider).toHaveValue('1')
    expect(screen.getByText('1', { selector: 'output' })).toBeInTheDocument()
  })

  it('reports integer level changes to its parent', () => {
    const onChange = vi.fn()
    render(<LevelSlider value={1} onChange={onChange} />)
    fireEvent.change(screen.getByRole('slider', { name: 'Character level' }), {
      target: { value: '37' },
    })
    expect(onChange).toHaveBeenCalledWith(37)
  })

  it('accepts the minimum and maximum boundary values', () => {
    const onChange = vi.fn()
    const { rerender } = render(<LevelSlider value={2} onChange={onChange} />)
    const slider = screen.getByRole('slider', { name: 'Character level' })
    fireEvent.change(slider, { target: { value: '1' } })
    rerender(<LevelSlider value={59} onChange={onChange} />)
    fireEvent.change(slider, { target: { value: '60' } })
    expect(onChange).toHaveBeenNthCalledWith(1, 1)
    expect(onChange).toHaveBeenNthCalledWith(2, 60)
    rerender(<LevelSlider value={60} onChange={onChange} />)
    expect(screen.getByText('60', { selector: 'output' })).toBeInTheDocument()
  })
})
