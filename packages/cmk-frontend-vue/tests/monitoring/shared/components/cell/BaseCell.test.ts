/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { type Ref, defineComponent, h, provide, ref } from 'vue'

import {
  type BreakpointValue,
  type CellBreakpoints,
  MONITORING_TABLE_WIDTH
} from '@/monitoring/shared/components/MonitoringTableContext'
import BaseCell from '@/monitoring/shared/components/cell/BaseCell.vue'

type CellProps = {
  hideBelow?: BreakpointValue
  breakpoints?: CellBreakpoints
}

function mountCell(
  props: CellProps = {},
  options: { containerWidth?: number; slots?: Record<string, () => unknown> } = {}
) {
  const slots = options.slots ?? { default: () => 'cell content' }
  return render(
    defineComponent({
      components: { BaseCell },
      setup() {
        if (options.containerWidth !== undefined) {
          const width: Ref<number> = ref(options.containerWidth)
          provide(MONITORING_TABLE_WIDTH, width)
        }
      },
      render() {
        return h('table', [h('tbody', [h('tr', [h(BaseCell, props, slots)])])])
      }
    })
  )
}

test('renders a <td> with default slot content', () => {
  const { container } = mountCell()
  const td = container.querySelector('td')
  expect(td).not.toBeNull()
  expect(td).toHaveTextContent('cell content')
})

test('hides the cell when the container width is below hide-below threshold', () => {
  const { container } = mountCell({ hideBelow: 'l' }, { containerWidth: 500 })
  expect(container.querySelector('td')).toBeNull()
})

test('renders the cell when the container width meets the hide-below threshold', () => {
  const { container } = mountCell({ hideBelow: 'l' }, { containerWidth: 900 })
  expect(container.querySelector('td')).not.toBeNull()
})

test('renders the cell when no container width is provided (default Infinity)', () => {
  const { container } = mountCell({ hideBelow: 'xl' })
  expect(container.querySelector('td')).not.toBeNull()
})

test('hide-below accepts a raw pixel value', () => {
  const { container } = mountCell({ hideBelow: 600 }, { containerWidth: 500 })
  expect(container.querySelector('td')).toBeNull()
})

test('renders the largest-fitting named slot from breakpoints', () => {
  const { container } = mountCell(
    { breakpoints: { short: 's', long: 'l', verbose: 'xl' } },
    {
      containerWidth: 900,
      slots: {
        short: () => 'short',
        long: () => 'long',
        verbose: () => 'verbose'
      }
    }
  )
  expect(container.querySelector('td')).toHaveTextContent('long')
})

test('falls back to the default slot when no breakpoint slot matches the current width', () => {
  const { container } = mountCell(
    { breakpoints: { long: 'l', verbose: 'xl' } },
    {
      containerWidth: 200,
      slots: {
        default: () => 'fallback',
        long: () => 'long',
        verbose: () => 'verbose'
      }
    }
  )
  expect(container.querySelector('td')).toHaveTextContent('fallback')
})

test('skips named slots that the consumer did not provide', () => {
  const { container } = mountCell(
    { breakpoints: { short: 's', long: 'l' } },
    {
      containerWidth: 1000,
      slots: {
        short: () => 'short',
        default: () => 'default'
        // `long` slot intentionally not provided
      }
    }
  )
  expect(container.querySelector('td')).toHaveTextContent('short')
})
