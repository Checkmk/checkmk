/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render } from '@testing-library/vue'

import CmkTrendChart from '@/network-flow/CmkTrendChart/CmkTrendChart.vue'
import type { CmkTrendChartProps, TrendChartSeries } from '@/network-flow/CmkTrendChart/types'

const POINTS = Array.from({ length: 30 }, (_unused, i) => i)

function series(name: string, overrides: Partial<TrendChartSeries> = {}): TrendChartSeries {
  return {
    name,
    dataPoints: POINTS,
    minimum: 1,
    maximum: 30,
    average: 15,
    last: 29,
    ...overrides
  }
}

function renderChart(props: Partial<CmkTrendChartProps> = {}) {
  return render(CmkTrendChart, {
    props: {
      series: [series('HTTP'), series('TLS')],
      displayMode: 'lines',
      formatValue: (value: number) => `${value} bps`,
      ...props
    }
  })
}

test('draws one line path per series in line mode', () => {
  const { container } = renderChart({ displayMode: 'lines' })

  const lines = [...container.querySelectorAll('path[fill="none"]')]
  expect(lines).toHaveLength(2)
  for (const path of lines) {
    expect(path.getAttribute('d')).toMatch(/^M/)
  }
})

test('draws a filled band and an outline per series in stacked-area mode', () => {
  const { container } = renderChart({ displayMode: 'stacked_area' })

  expect(container.querySelectorAll('path[fill-opacity]')).toHaveLength(2)
  expect(container.querySelectorAll('path[fill="none"]')).toHaveLength(2)
})

test('renders a legend row per series with the min/max/avg/last statistics', () => {
  const { container, getAllByText } = renderChart()

  const rows = container.querySelectorAll('.network-flow-trend-chart-legend__row')
  expect(rows).toHaveLength(2)
  // The formatter is applied to each statistic; "last" (29) appears once per row.
  expect(getAllByText('29 bps')).toHaveLength(2)
})

test('assigns distinct palette colors to the first two series', () => {
  const { container } = renderChart()

  const swatches = [
    ...container.querySelectorAll<HTMLElement>('.network-flow-trend-chart-legend__swatch')
  ]
  expect(swatches).toHaveLength(2)
  expect(swatches[0]!.style.backgroundColor).not.toBe(swatches[1]!.style.backgroundColor)
})

test('emits seriesClick with the series name when a clickable legend name is activated', async () => {
  const { container, emitted } = renderChart({ clickableSeries: true })

  const button = container.querySelector<HTMLButtonElement>(
    '.network-flow-trend-chart-legend__name--link'
  )
  expect(button).not.toBeNull()
  await fireEvent.click(button!)

  expect(emitted()['seriesClick']).toEqual([['HTTP']])
})

test('renders plain (non-clickable) legend names by default', () => {
  const { container } = renderChart()

  expect(container.querySelector('.network-flow-trend-chart-legend__name--link')).toBeNull()
})

test('draws no path when a series has fewer than two points', () => {
  const { container } = renderChart({
    series: [series('HTTP', { dataPoints: [5] })],
    displayMode: 'lines'
  })

  for (const path of container.querySelectorAll('path')) {
    expect(path.getAttribute('d')).toBeFalsy()
  }
})
