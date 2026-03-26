/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import CmkPerfometer from '@/components/CmkPerfometer.vue'

function getRandomValueAndRange(): { value: number; min: number; max: number } {
  // Ranges possible between [0, 2000] (widest) and [999, 1000] (most narrow)
  let min = Math.round(Math.random() * 1000)
  min = min === 1000 ? 0 : min
  const max = Math.round(Math.random() * 1000) + 1000
  const value = min + Math.round(Math.random() * (max - min))

  return { value, min, max }
}

test('Perfometer renders correct percentage, color, and text', async () => {
  const { value, min, max } = getRandomValueAndRange()
  const formatted = `${value} bit/s`
  const color = 'rgb(1, 2, 3)'

  render(CmkPerfometer, {
    props: {
      value: value,
      valueRange: [min, max],
      formatted: formatted,
      color: color
    }
  })

  const percentage = Math.round((100 * (value - min)) / (max - min))

  const progressbar = screen.getByRole('progressbar', { name: 'Perf-O-Meter' })
  expect(progressbar).toHaveAttribute('aria-valuenow', `${percentage}`)

  // Bar color
  const barDiv = progressbar.querySelector('.cmk-perfometer__bar')
  expect(window.getComputedStyle(barDiv!).backgroundColor).toBe(color)

  // Value text
  expect(progressbar).toHaveTextContent(formatted)
})

test.each([
  { value: 10, range: [40, 100] as [number, number], expected: 0, desc: 'below minimum' },
  { value: 150, range: [0, 100] as [number, number], expected: 100, desc: 'above maximum' },
  { value: 40, range: [40, 100] as [number, number], expected: 0, desc: 'at minimum' },
  { value: 100, range: [40, 100] as [number, number], expected: 100, desc: 'at maximum' },
  { value: 70, range: [40, 100] as [number, number], expected: 50, desc: 'in normal range' }
])('Perfometer clamps percentage when value is $desc', ({ value, range, expected }) => {
  render(CmkPerfometer, {
    props: {
      value: value,
      valueRange: range,
      formatted: `${value} unit`,
      color: 'rgb(0, 128, 0)'
    }
  })

  const progressbar = screen.getByRole('progressbar', { name: 'Perf-O-Meter' })
  expect(progressbar).toHaveAttribute('aria-valuenow', `${expected}`)
})
