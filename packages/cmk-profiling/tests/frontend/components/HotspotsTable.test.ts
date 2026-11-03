/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { nextTick } from 'vue'

import HotspotsTable from '../../../frontend/components/HotspotsTable.vue'
import type { HotspotData } from '../../../frontend/types'

const originalOffsetHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight')
const originalOffsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth')

beforeAll(() => {
  Object.defineProperty(HTMLElement.prototype, 'offsetHeight', { configurable: true, value: 600 })
  Object.defineProperty(HTMLElement.prototype, 'offsetWidth', { configurable: true, value: 800 })
})

afterAll(() => {
  if (originalOffsetHeight) {
    Object.defineProperty(HTMLElement.prototype, 'offsetHeight', originalOffsetHeight)
  }
  if (originalOffsetWidth) {
    Object.defineProperty(HTMLElement.prototype, 'offsetWidth', originalOffsetWidth)
  }
})

function makeHotspot(name: string, file: string): HotspotData {
  return {
    function: name,
    file,
    line: 1,
    self_time_ms: 10,
    self_pct: 10,
    cumulative_time_ms: 20,
    cumulative_pct: 20,
    ncalls: 5,
    primitive_calls: 5,
    top_callers: [],
    top_callees: []
  }
}

const HOTSPOTS: HotspotData[] = [
  makeHotspot('alpha_func', 'a.py'),
  makeHotspot('beta_func', 'b.py'),
  makeHotspot('gamma_func', 'c.py'),
  makeHotspot('delta_func', 'd.py')
]

async function flush(): Promise<void> {
  await nextTick()
  await nextTick()
}

test('renders one row per hotspot without a search query', async () => {
  render(HotspotsTable, {
    props: { hotspots: HOTSPOTS, highlightFunction: '', searchQuery: '' }
  })
  await flush()

  expect(screen.getAllByLabelText(/^Select function/)).toHaveLength(4)
})

test('filters the rendered rows by the search query', async () => {
  const { rerender } = render(HotspotsTable, {
    props: { hotspots: HOTSPOTS, highlightFunction: '', searchQuery: '' }
  })
  await flush()

  await rerender({ hotspots: HOTSPOTS, highlightFunction: '', searchQuery: 'beta' })
  await flush()

  const rows = screen.getAllByLabelText(/^Select function/)
  expect(rows).toHaveLength(1)
  expect(rows[0]).toHaveAccessibleName('Select function beta_func')
})

test('filtered match stays visible after the list was scrolled down', async () => {
  const many: HotspotData[] = Array.from({ length: 200 }, (_, i) =>
    makeHotspot(`func_${i}`, `f${i}.py`)
  )
  const { rerender, container } = render(HotspotsTable, {
    props: { hotspots: many, highlightFunction: '', searchQuery: '' }
  })
  await flush()

  // Scroll the virtualized container far down, then filter to a single match.
  const scroller = container.querySelector('.profiling-hotspots-table') as HTMLElement
  Object.defineProperty(scroller, 'scrollTop', { configurable: true, value: 8000, writable: true })
  scroller.dispatchEvent(new Event('scroll'))
  await flush()

  await rerender({ hotspots: many, highlightFunction: '', searchQuery: 'func_137' })
  await flush()

  const rows = screen.getAllByLabelText(/^Select function/)
  expect(rows).toHaveLength(1)
  expect(rows[0]).toHaveAccessibleName('Select function func_137')
})

test('filters by file name too', async () => {
  const { rerender } = render(HotspotsTable, {
    props: { hotspots: HOTSPOTS, highlightFunction: '', searchQuery: '' }
  })
  await flush()

  await rerender({ hotspots: HOTSPOTS, highlightFunction: '', searchQuery: 'c.py' })
  await flush()

  expect(screen.getAllByLabelText(/^Select function/)).toHaveLength(1)
  expect(screen.getByLabelText('Select function gamma_func')).toBeInTheDocument()
})

test('renders recursive calls as total/primitive and plain calls as one number', async () => {
  const recursive = { ...makeHotspot('rec_func', 'r.py'), ncalls: 233, primitive_calls: 32 }
  const plain = { ...makeHotspot('plain_func', 'p.py'), ncalls: 5, primitive_calls: 5 }
  render(HotspotsTable, {
    props: { hotspots: [recursive, plain], highlightFunction: '', searchQuery: '' }
  })
  await flush()

  expect(screen.getByText('233/32')).toBeInTheDocument()
  expect(screen.getByText('5')).toBeInTheDocument()
})
