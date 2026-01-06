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

test('Perfometer renders correct width, color, and text', async () => {
  // Props
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

  const perfometerDiv = screen.getByLabelText('Perf-O-Meter')
  const valueDiv = perfometerDiv.querySelector('.cmk-perfometer__value')
  const barDiv = perfometerDiv.querySelector('.cmk-perfometer__bar')

  // Bar (width & color)
  expect(barDiv).toBeDefined()
  const barDivStyles = window.getComputedStyle(barDiv!)
  expect(barDivStyles.width).toBe(`${percentage}%`)
  expect(barDivStyles.backgroundColor).toBe(color)

  // Value (text)
  expect(valueDiv).toBeDefined()
  expect(valueDiv!.textContent).toBe(formatted)
})
