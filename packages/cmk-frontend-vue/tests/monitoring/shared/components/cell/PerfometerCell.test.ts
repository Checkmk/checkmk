/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { defineComponent, h } from 'vue'

import type { Perfometer } from '@/monitoring/shared/api/types'
import PerfometerCell, {
  type PerfometerCellProps
} from '@/monitoring/shared/components/cell/PerfometerCell.vue'

function makePerfometer(bars: Perfometer['bars'], formatted: string): Perfometer {
  return { bars, formatted }
}

const SINGLE_BAR = makePerfometer(
  [
    [
      { share: 70, color: 'rgb(0, 128, 0)' },
      { share: 30, color: null }
    ]
  ],
  '70%'
)

function mountCell(props: PerfometerCellProps & { onClick?: (event: MouseEvent) => void }) {
  return render(
    defineComponent({
      render() {
        return h('table', [h('tbody', [h('tr', [h(PerfometerCell, props)])])])
      }
    })
  )
}

function barWidths(container: Element): string[] {
  return Array.from(container.querySelectorAll<HTMLElement>('.cmk-perfometer__bar')).map(
    (bar) => bar.style.width
  )
}

test('renders the perfometer with its label, fill percentage and color', () => {
  const { container } = mountCell({ data: SINGLE_BAR })

  const progressbar = screen.getByRole('progressbar', { name: 'Perf-O-Meter' })
  expect(progressbar).toHaveAttribute('aria-valuenow', '70')
  expect(progressbar).toHaveTextContent('70%')

  const bar = container.querySelector('.cmk-perfometer__bar') as HTMLElement
  expect(bar.style.backgroundColor).toBe('rgb(0, 128, 0)')
  expect(bar.style.width).toBe('70%')
})

test('renders a stacked perfometer as two bars, the upper one first', () => {
  const { container } = mountCell({
    data: makePerfometer(
      [
        [
          { share: 70, color: 'rgb(0, 128, 0)' },
          { share: 30, color: null }
        ],
        [
          { share: 35, color: 'rgb(255, 165, 0)' },
          { share: 65, color: null }
        ]
      ],
      '70 / 35'
    )
  })

  expect(container.querySelectorAll('.cmk-perfometer__row')).toHaveLength(2)
  expect(barWidths(container)).toEqual(['70%', '30%', '35%', '65%'])
  expect(screen.getByRole('progressbar', { name: 'Perf-O-Meter' })).toHaveTextContent('70 / 35')
})

test('renders a bidirectional perfometer as one bar growing outwards from its centre', () => {
  const { container } = mountCell({
    data: makePerfometer(
      [
        [
          { share: 25, color: null },
          { share: 25, color: 'rgb(0, 128, 0)' },
          { share: 12.5, color: 'rgb(255, 165, 0)' },
          { share: 37.5, color: null }
        ]
      ],
      '50 / 25'
    )
  })

  expect(container.querySelectorAll('.cmk-perfometer__row')).toHaveLength(1)
  expect(barWidths(container)).toEqual(['25%', '25%', '12.5%', '37.5%'])
})

test('leaves the unfilled part of a bar transparent', () => {
  const { container } = mountCell({ data: SINGLE_BAR })

  const bars = container.querySelectorAll<HTMLElement>('.cmk-perfometer__bar')
  expect(bars[1]!.style.backgroundColor).toBe('transparent')
})

test('renders an empty cell when no perfometer data is present', () => {
  const { container } = mountCell({ data: undefined })

  const cell = container.querySelector('td')
  expect(cell).not.toBeNull()
  expect(container.querySelector('.cmk-perfometer')).toBeNull()
})

test('marks the perfometer as stale', () => {
  const { container } = mountCell({ stale: true, data: SINGLE_BAR })

  expect(container.querySelector('.monitoring-perfometer-cell--stale')).toBeInTheDocument()
})

test('wraps the perfometer in a link when linkedTo is set', () => {
  const { container } = mountCell({
    linkedTo: { href: 'view.py?view_name=service_graphs&host=web-1', target: '_top' },
    data: SINGLE_BAR
  })

  const link = container.querySelector('a')
  expect(link).not.toBeNull()
  expect(link).toHaveAttribute('href', 'view.py?view_name=service_graphs&host=web-1')
})

test('reports a click on the perfometer of a button cell', async () => {
  const onClick = vi.fn()
  const { container } = mountCell({ button: true, data: SINGLE_BAR, onClick })

  await userEvent.click(container.querySelector('button')!)

  expect(onClick).toHaveBeenCalled()
})

test('the perfometer sits at the top of its row, as every other cell does', () => {
  const { container } = mountCell({ data: SINGLE_BAR })

  expect(container.querySelector('td')).not.toHaveClass('monitoring-base-cell--vertical-middle')
})
