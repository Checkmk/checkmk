/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'

import ProfilingFlamegraphApp from '@/profiling/ProfilingFlamegraphApp.vue'
import type { HotspotData, ProfilingFlamegraphData } from '@/profiling/types'

import { FakeResizeObserver } from '@tests/lib/fakeResizeObserver'

const DATA_URL = 'http://localhost/profile_data.py'

const originalOffsetHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight')
const originalOffsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth')

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

const PAYLOAD: ProfilingFlamegraphData = {
  metadata: null,
  hotspots: [
    makeHotspot('alpha_func', 'a.py'),
    makeHotspot('beta_func', 'b.py'),
    makeHotspot('gamma_func', 'c.py'),
    makeHotspot('delta_func', 'd.py')
  ],
  flamegraph_tree: {
    name: 'root',
    value: 0,
    total: 100,
    children: [{ name: 'alpha_func', value: 50, total: 100, children: [] }]
  },
  function_paths: {},
  total_time: 0.1,
  total_calls: 20,
  total_functions: 4
}

const server = setupServer(http.get(DATA_URL, () => HttpResponse.json(PAYLOAD)))

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' })
  vi.stubGlobal('ResizeObserver', FakeResizeObserver)
  Object.defineProperty(HTMLElement.prototype, 'offsetHeight', { configurable: true, value: 600 })
  Object.defineProperty(HTMLElement.prototype, 'offsetWidth', { configurable: true, value: 800 })
})
afterEach(() => server.resetHandlers())
afterAll(() => {
  server.close()
  if (originalOffsetHeight) {
    Object.defineProperty(HTMLElement.prototype, 'offsetHeight', originalOffsetHeight)
  }
  if (originalOffsetWidth) {
    Object.defineProperty(HTMLElement.prototype, 'offsetWidth', originalOffsetWidth)
  }
})

test('typing in the table filter narrows the rendered hotspot rows', async () => {
  const user = userEvent.setup()
  render(ProfilingFlamegraphApp, {
    props: { profile_id: 'p1', data_url: DATA_URL }
  })

  // Wait for the async payload to load and the table to render all rows.
  await waitFor(() => {
    expect(screen.getAllByLabelText(/^Select function/)).toHaveLength(4)
  })

  const filterInput = screen.getByPlaceholderText('Filter table...')
  await user.type(filterInput, 'beta')

  // Debounced (120 ms) — poll until the filtered list settles.
  await waitFor(
    () => {
      expect(screen.getAllByLabelText(/^Select function/)).toHaveLength(1)
    },
    { timeout: 1000 }
  )
  expect(screen.getByLabelText('Select function beta_func')).toBeInTheDocument()
})
