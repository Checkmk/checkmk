/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type * as intl from '@internationalized/date'
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { nextTick } from 'vue'

import GraphFigure from '@/graphing/components/GraphFigure/GraphFigure.vue'

// The mock stands in for the view-only renderer: the buttons replay its zoom/pan/reset
// intent emits so the tests can drive the figure's interaction wiring.
vi.mock('@/graphing/components/TimeSeriesGraph', () => ({
  default: {
    inheritAttrs: false,
    props: ['panEnabled'],
    emits: ['zoom', 'pan', 'reset'],
    template: `<div data-testid="time-series-graph">
      <span data-testid="pan-enabled">{{ panEnabled }}</span>
      <button
        data-testid="emit-pan"
        @click="$emit('pan', { timeRange: { start: 500, end: 900, step: 60 } })"
      />
      <button data-testid="emit-reset" @click="$emit('reset')" />
    </div>`
  }
}))

vi.mock('@internationalized/date', async (importOriginal) => {
  const actual = await importOriginal<typeof intl>()
  return { ...actual, getLocalTimeZone: () => 'UTC' }
})

const UNIT: components['schemas']['ApiUnitFormat'] = {
  notation: 'decimal',
  symbol: '',
  precision: { type: 'auto', digits: 2 },
  convertible: true
}

const FETCHED = {
  title: 'CPU utilization',
  metrics: [
    {
      metadata: { name: 'cpu', title: 'CPU utilization', unit: UNIT, color: '#ff0000' },
      render: { stack: 'area', inverse: false, hidden: false },
      data_points: [1, 2, 3]
    }
  ],
  time_range: { start: 1_000, end: 2_000, step: 60 },
  horizontal_lines: []
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

beforeEach(() => {
  postSpy = vi.spyOn(client, 'POST')
  postSpy.mockResolvedValue({
    data: FETCHED,
    error: undefined,
    response: new Response('{}', { status: 200 })
  } as never)
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

const loadingIcon = (): Element | null =>
  document.querySelector('.graphing-graph-figure__loading-icon')

function renderFigure(props: Record<string, unknown> = {}) {
  return render(GraphFigure, {
    props: {
      internal: '{"graphs": []}',
      timerange: { type: 'age', hours: 4 },
      ...props
    }
  })
}

test('holds the loading icon back for a second while the fetch is pending', async () => {
  vi.useFakeTimers()
  postSpy.mockReturnValue(new Promise(() => {}))
  renderFigure()

  await nextTick()
  expect(loadingIcon()).not.toBeInTheDocument()
  expect(screen.queryByTestId('time-series-graph')).not.toBeInTheDocument()

  vi.advanceTimersByTime(1_000)
  await nextTick()
  expect(loadingIcon()).toBeInTheDocument()
  expect(screen.queryByTestId('time-series-graph')).not.toBeInTheDocument()
})

test('a fast load renders the graph without ever showing the loading icon', async () => {
  vi.useFakeTimers()
  renderFigure()

  // Flush the already-resolved fetch without reaching the one-second threshold.
  await vi.advanceTimersByTimeAsync(999)
  expect(screen.queryByTestId('time-series-graph')).toBeInTheDocument()
  expect(loadingIcon()).not.toBeInTheDocument()

  // The pending delay must have been cancelled, not merely outrun by the data.
  await vi.advanceTimersByTimeAsync(1_000)
  expect(loadingIcon()).not.toBeInTheDocument()
})

test('renders the graph once data arrives', async () => {
  renderFigure()
  expect(await screen.findByTestId('time-series-graph')).toBeInTheDocument()
})

test('shows the error message when the fetch fails', async () => {
  postSpy.mockRejectedValue(new Error('crash'))
  renderFigure()
  expect(await screen.findByText(/crash/)).toBeInTheDocument()
})

test('fetches the definition via fetch_data with the max consolidation', async () => {
  renderFigure()

  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(1))
  const body = postSpy.mock.calls[0][1].body
  expect(body.internal).toBe('{"graphs": []}')
  expect(body.consolidation_function).toBe('max')
  expect(body.combination_mode).toBeNull()
})

test('forwards the combination mode to fetch_data', async () => {
  renderFigure({ combinationMode: 'stacked' })

  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(1))
  expect(postSpy.mock.calls[0][1].body.combination_mode).toBe('stacked')
})

test('a provided fetchGraph replaces the default fetch', async () => {
  const fetchGraph = vi.fn().mockResolvedValue({
    title: FETCHED.title,
    metrics: FETCHED.metrics,
    timeRange: FETCHED.time_range,
    horizontalLines: []
  })

  renderFigure({ fetchGraph })

  expect(await screen.findByTestId('time-series-graph')).toBeInTheDocument()
  expect(postSpy).not.toHaveBeenCalled()
  expect(fetchGraph).toHaveBeenCalledWith(
    { internal: '{"graphs": []}' },
    expect.objectContaining({ consolidationFunction: 'max', combinationMode: null })
  )
})

test('a pan fetches the panned window', async () => {
  renderFigure()
  await screen.findByTestId('time-series-graph')

  await fireEvent.click(screen.getByTestId('emit-pan'))

  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(2))
  const requestedRange = postSpy.mock.calls[1][1].body.requested_time_range
  expect(requestedRange).toMatchObject({ start: 500, end: 900 })
})

test('a reset after a pan re-resolves the configured range', async () => {
  renderFigure()
  await screen.findByTestId('time-series-graph')
  await fireEvent.click(screen.getByTestId('emit-pan'))
  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(2))

  await fireEvent.click(screen.getByTestId('emit-reset'))

  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(3))
  // The configured range ("last 4 hours") resolves relative to now, far past the panned window.
  const requestedRange = postSpy.mock.calls[2][1].body.requested_time_range
  expect(requestedRange.end).toBeGreaterThan(900)
})

test('carries no context view but keeps panning enabled', async () => {
  renderFigure()
  await screen.findByTestId('time-series-graph')

  expect(document.querySelector('.graphing-graph-brush')).not.toBeInTheDocument()
  expect(screen.getByTestId('pan-enabled')).toHaveTextContent('true')
})

test('shows the timestamp only when requested', async () => {
  const { unmount } = renderFigure({ showTimestamp: true })
  await screen.findByTestId('time-series-graph')
  expect(document.querySelector('.graphing-graph-timestamp')).toBeInTheDocument()
  unmount()

  renderFigure()
  await screen.findByTestId('time-series-graph')
  expect(document.querySelector('.graphing-graph-timestamp')).not.toBeInTheDocument()
})

test('shows the compact legend only when requested', async () => {
  const { unmount } = renderFigure({ showLegend: true })
  await screen.findByTestId('time-series-graph')
  // The compact legend middle-truncates names into head/tail spans; the full title
  // is carried by the series' title attribute.
  expect(screen.getByTitle('CPU utilization')).toBeInTheDocument()
  expect(document.querySelector('.graphing-graph-legend-compact')).toBeInTheDocument()
  unmount()

  renderFigure()
  await screen.findByTestId('time-series-graph')
  expect(document.querySelector('.graphing-graph-legend-compact')).not.toBeInTheDocument()
})

test('shows the burger menu only when requested', async () => {
  const { unmount } = renderFigure({ showBurgerMenu: true })
  await screen.findByTestId('time-series-graph')
  expect(document.querySelector('.graphing-graph-burger-menu')).toBeInTheDocument()
  unmount()

  renderFigure()
  await screen.findByTestId('time-series-graph')
  expect(document.querySelector('.graphing-graph-burger-menu')).not.toBeInTheDocument()
})
