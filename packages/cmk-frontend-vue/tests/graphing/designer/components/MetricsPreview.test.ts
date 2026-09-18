/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'

import type { Metric } from '@/graphing/components/TimeSeriesGraph'
import MetricsPreview from '@/graphing/designer/components/MetricsPreview.vue'

function metric(name: string, color = '#123456'): Metric {
  return {
    metadata: {
      name,
      title: name,
      unit: {
        notation: 'decimal',
        symbol: '',
        precision: { type: 'auto', digits: 2 },
        convertible: false
      },
      color,
      attributes: []
    },
    render: { stack: null, inverse: false, hidden: false },
    data_points: [1]
  }
}

function backendMetric(name: string): Metric {
  const base = metric(name)
  return {
    ...base,
    metadata: {
      ...base.metadata,
      attributes: [
        { kind: 'resource', name: 'host.arch', value: 'x64' },
        { kind: 'data_point', name: 'status', value: '304' }
      ]
    }
  }
}

function renderPreview(metrics: Metric[]) {
  return render(MetricsPreview, { props: { metrics } })
}

function rowOf(title: string): HTMLElement {
  return screen.getByText(title).closest('tr')!
}

test('lists every series the query resolved to', () => {
  renderPreview([metric('first'), metric('second')])

  expect(screen.getByText('first')).toBeInTheDocument()
  expect(screen.getByText('second')).toBeInTheDocument()
})

test('a series expands into its attribute table', async () => {
  renderPreview([backendMetric('line one')])

  expect(screen.queryByText('host.arch')).not.toBeInTheDocument()

  await fireEvent.click(screen.getByRole('button', { name: 'Toggle attributes of line one' }))

  const archRow = screen.getByText('host.arch').closest('tr')!
  expect(archRow).toHaveTextContent('x64')
  expect(archRow).toHaveTextContent('Resource')
})

test('a series without attributes offers no toggle', () => {
  renderPreview([metric('plain')])

  expect(
    screen.queryByRole('button', { name: 'Toggle attributes of plain' })
  ).not.toBeInTheDocument()
})

test('hovering a series emits its name', async () => {
  const { emitted } = renderPreview([metric('first'), metric('second')])

  await fireEvent.mouseEnter(rowOf('second'))

  expect(emitted()['hoverMetrics']).toEqual([[['second']]])
})

test('leaving a series clears the highlight', async () => {
  const { emitted } = renderPreview([metric('first')])

  await fireEvent.mouseEnter(rowOf('first'))
  await fireEvent.mouseLeave(rowOf('first'))

  expect(emitted()['hoverMetrics']).toEqual([[['first']], [[]]])
})

test('hovering the attributes of a series keeps that series highlighted', async () => {
  const { emitted } = renderPreview([backendMetric('line one')])
  await fireEvent.click(screen.getByRole('button', { name: 'Toggle attributes of line one' }))

  const attributesRow = screen.getByText('Attribute name').closest('table')!.closest('tr')!
  await fireEvent.mouseEnter(attributesRow)

  expect(emitted()['hoverMetrics']).toEqual([[['line one']]])
})
