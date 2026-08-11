/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { defineComponent, h } from 'vue'

import PerfometerCell, {
  type PerfometerCellProps
} from '@/monitoring/shared/components/cell/PerfometerCell.vue'

function mountCell(props: PerfometerCellProps) {
  return render(
    defineComponent({
      render() {
        return h('table', [h('tbody', [h('tr', [h(PerfometerCell, props)])])])
      }
    })
  )
}

test('renders the perfometer with its label, fill percentage and color', () => {
  const { container } = mountCell({
    data: {
      value: 70,
      value_range: { min: 40, max: 100 },
      formatted: '70%',
      color: 'rgb(0, 128, 0)'
    }
  })

  const progressbar = screen.getByRole('progressbar', { name: 'Perf-O-Meter' })
  expect(progressbar).toHaveAttribute('aria-valuenow', '50')
  expect(progressbar).toHaveTextContent('70%')

  const bar = container.querySelector('.cmk-perfometer__bar') as HTMLElement
  expect(bar.style.backgroundColor).toBe('rgb(0, 128, 0)')
})

test('renders an empty cell when no perfometer data is present', () => {
  const { container } = mountCell({ data: undefined })

  const cell = container.querySelector('td')
  expect(cell).not.toBeNull()
  expect(container.querySelector('.cmk-perfometer')).toBeNull()
})

test('marks the perfometer as stale', () => {
  const { container } = mountCell({
    stale: true,
    data: {
      value: 10,
      value_range: { min: 0, max: 100 },
      formatted: '10%',
      color: 'rgb(0, 128, 0)'
    }
  })

  expect(container.querySelector('.monitoring-perfometer-cell--stale')).toBeInTheDocument()
})

test('wraps the perfometer in a link when linkedTo is set', () => {
  const { container } = mountCell({
    linkedTo: { href: 'graph.py?host=web-1', target: '_top' },
    data: {
      value: 10,
      value_range: { min: 0, max: 100 },
      formatted: '10%',
      color: 'rgb(0, 128, 0)'
    }
  })

  const link = container.querySelector('a')
  expect(link).not.toBeNull()
  expect(link).toHaveAttribute('href', 'graph.py?host=web-1')
})
