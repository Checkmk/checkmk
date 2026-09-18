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
import { useGlobalPin } from '@/graphing/composables/useGlobalPin'

// The mock stands in for the view-only renderer: the buttons replay its zoom/pan/reset/pin
// intent emits so the tests can drive the figure's interaction wiring.
vi.mock('@/graphing/components/TimeSeriesGraph', () => ({
  default: {
    inheritAttrs: false,
    props: ['panEnabled', 'time_range', 'valueRange', 'options', 'pinEnabled', 'pinTime'],
    emits: ['zoom', 'pan', 'reset', 'pinCreate', 'pinAction'],
    template: `<div data-testid="time-series-graph">
      <span data-testid="pan-enabled">{{ panEnabled }}</span>
      <span data-testid="value-range">{{ valueRange === null ? 'none' : valueRange.max }}</span>
      <span data-testid="y-axis">{{ options?.y_axis === null ? 'null' : 'set' }}</span>
      <span data-testid="y-axis-range">{{ options?.y_axis?.explicit_range?.max ?? 'none' }}</span>
      <span data-testid="y-axis-unit">{{ options?.y_axis?.unit?.notation ?? 'none' }}</span>
      <span data-testid="pin-enabled">{{ pinEnabled }}</span>
      <span data-testid="pin-time">{{ pinTime }}</span>
      <button
        data-testid="emit-pan"
        @click="$emit('pan', { timeRange: { start: 500, end: 900, step: 60 } })"
      />
      <button
        data-testid="emit-value-zoom"
        @click="$emit('zoom', { timeRange: time_range, valueRange: { min: 0, max: 10 } })"
      />
      <button data-testid="emit-reset" @click="$emit('reset')" />
      <button data-testid="emit-pin-create" @click="$emit('pinCreate', { time: 1234 })" />
      <button data-testid="emit-pin-action" @click="$emit('pinAction', { time: 1234 })" />
    </div>`
  }
}))

// A figure that arms the pin loads and persists it; stubbed to keep these tests off the network.
vi.mock('@/graphing/composables/useGlobalPin', async () => {
  const { computed, ref } = await import('vue')
  const pinTimeState = ref<number | null>(null)
  const globalPin = {
    pinTime: computed(() => pinTimeState.value),
    ensurePinLoaded: vi.fn(),
    setPin: vi.fn((time: number) => {
      pinTimeState.value = time
    }),
    clearPin: vi.fn(() => {
      pinTimeState.value = null
    })
  }
  return { useGlobalPin: () => globalPin }
})

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

const REFRESH_INTERVAL_MS = 60_000
const LEADING_STEPS_FETCHED_PAST_VIEW = 2
const TRAILING_STEPS_FETCHED_PAST_VIEW = 1

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
  horizontal_lines: [],
  warnings: [],
  errors: []
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

beforeEach(() => {
  // The mocked pin is a module-level singleton, so it has to be cleared between tests.
  useGlobalPin().clearPin()
  vi.clearAllMocks()
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

test('states a readable headline over the technical detail when the fetch fails', async () => {
  postSpy.mockRejectedValue(new Error('crash'))
  renderFigure()

  expect(await screen.findByText('Graph data could not be loaded.')).toBeInTheDocument()
  expect(screen.getByText('crash')).toBeInTheDocument()
  expect(loadingIcon()).not.toBeInTheDocument()
})

test('retrying after a failure refetches and restores the graph', async () => {
  postSpy.mockRejectedValue(new Error('crash'))
  renderFigure()
  await screen.findByRole('button', { name: 'Retry' })

  postSpy.mockResolvedValue({
    data: FETCHED,
    error: undefined,
    response: new Response('{}', { status: 200 })
  } as never)
  await fireEvent.click(screen.getByRole('button', { name: 'Retry' }))

  expect(await screen.findByTestId('time-series-graph')).toBeInTheDocument()
  expect(screen.queryByText('Graph data could not be loaded.')).not.toBeInTheDocument()
})

test('keeps the graph on screen when a refetch fails, stating the error over it', async () => {
  renderFigure()
  expect(await screen.findByTestId('time-series-graph')).toBeInTheDocument()

  postSpy.mockRejectedValue(new Error('gone'))
  await fireEvent.click(screen.getByTestId('emit-pan'))
  await waitFor(() => expect(screen.getByText('gone')).toBeInTheDocument())

  expect(screen.getByTestId('time-series-graph')).toBeInTheDocument()
})

test("reports the response's own per-metric errors alongside the graph", async () => {
  postSpy.mockResolvedValue({
    data: { ...FETCHED, errors: ['Metrics backend is unavailable.'] },
    error: undefined,
    response: new Response('{}', { status: 200 })
  } as never)
  renderFigure()

  expect(await screen.findByText('Metrics backend is unavailable.')).toBeInTheDocument()
  expect(screen.getByTestId('time-series-graph')).toBeInTheDocument()
})

test("states the response's warnings as advisory, with no retry offered", async () => {
  postSpy.mockResolvedValue({
    data: { ...FETCHED, warnings: ['The query matched more than 100 time series.'] },
    error: undefined,
    response: new Response('{}', { status: 200 })
  } as never)
  renderFigure()

  const message = await screen.findByText('The query matched more than 100 time series.')
  expect(message.closest('.graphing-graph-notice')).toHaveClass('graphing-graph-notice--warning')
  // A retry would only reproduce the truncation, so none is offered.
  expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument()
  expect(screen.getByTestId('time-series-graph')).toBeInTheDocument()
})

test('states errors and warnings together, at the error severity', async () => {
  postSpy.mockResolvedValue({
    data: {
      ...FETCHED,
      errors: ['Metrics backend is unavailable.'],
      warnings: ['The query matched more than 100 time series.']
    },
    error: undefined,
    response: new Response('{}', { status: 200 })
  } as never)
  renderFigure()

  // One pill states both, so the advice is not dropped for arriving next to a failure.
  const message = await screen.findByText(
    'Metrics backend is unavailable. The query matched more than 100 time series.'
  )
  expect(message.closest('.graphing-graph-notice')).toHaveClass('graphing-graph-notice--error')
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
  const { start, end, step } = postSpy.mock.calls[1][1].body.requested_time_range
  expect({
    start: start + LEADING_STEPS_FETCHED_PAST_VIEW * step,
    end: end - TRAILING_STEPS_FETCHED_PAST_VIEW * step
  }).toEqual({ start: 500, end: 900 })
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

test('a peak zoom outlives the refresh timer re-fetching the same window', async () => {
  vi.useFakeTimers()
  renderFigure()
  await vi.advanceTimersByTimeAsync(1)
  await fireEvent.click(screen.getByTestId('emit-value-zoom'))
  expect(screen.getByTestId('value-range')).toHaveTextContent('10')

  await vi.advanceTimersByTimeAsync(REFRESH_INTERVAL_MS)

  expect(postSpy).toHaveBeenCalledTimes(2)
  expect(screen.getByTestId('value-range')).toHaveTextContent('10')
})

test('a peak zoom ends when the dashboard configures another range', async () => {
  const { rerender } = renderFigure()
  await screen.findByTestId('time-series-graph')
  await fireEvent.click(screen.getByTestId('emit-value-zoom'))
  expect(screen.getByTestId('value-range')).toHaveTextContent('10')

  await rerender({ timerange: { type: 'age', hours: 8 } })

  expect(screen.getByTestId('value-range')).toHaveTextContent('none')
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

test('a figure without the pin never arms it', async () => {
  renderFigure()

  await waitFor(() => expect(screen.getByTestId('time-series-graph')).toBeInTheDocument())
  expect(screen.getByTestId('pin-enabled')).toHaveTextContent('false')
  expect(useGlobalPin().ensurePinLoaded).not.toHaveBeenCalled()
})

test('a pin-enabled figure arms the renderer and loads the persisted pin', async () => {
  renderFigure({ showPin: true })

  await waitFor(() => expect(screen.getByTestId('time-series-graph')).toBeInTheDocument())
  expect(screen.getByTestId('pin-enabled')).toHaveTextContent('true')
  expect(useGlobalPin().ensurePinLoaded).toHaveBeenCalled()
})

test('a pin placed in the renderer is persisted and handed back to it', async () => {
  renderFigure({ showPin: true })

  await waitFor(() => expect(screen.getByTestId('time-series-graph')).toBeInTheDocument())
  await fireEvent.click(screen.getByTestId('emit-pin-create'))

  expect(useGlobalPin().setPin).toHaveBeenCalledWith(1234)
  expect(screen.getByTestId('pin-time')).toHaveTextContent('1234')
})

test('acting on the placed pin clears it', async () => {
  renderFigure({ showPin: true })

  await waitFor(() => expect(screen.getByTestId('time-series-graph')).toBeInTheDocument())
  await fireEvent.click(screen.getByTestId('emit-pin-create'))
  await fireEvent.click(screen.getByTestId('emit-pin-action'))

  expect(useGlobalPin().clearPin).toHaveBeenCalled()
  expect(screen.getByTestId('pin-time')).toBeEmptyDOMElement()
})

// The marker stands above the graph area. jsdom lays nothing out, so these assert the rules
// that make the room for it rather than the geometry, which needs a browser.
describe('room for the pin marker', () => {
  const header = (): Element | null => document.querySelector('.graphing-graph-figure__header')
  const figure = (): Element | null => document.querySelector('.graphing-graph-figure')

  test('a header widens its gap so the marker clears it', async () => {
    renderFigure({ showPin: true, showTimestamp: true })

    await waitFor(() => expect(screen.getByTestId('time-series-graph')).toBeInTheDocument())
    expect(header()).toHaveClass('graphing-graph-figure__header--pin-gap')
    expect(figure()).not.toHaveClass('graphing-graph-figure--pin-overhang')
  })

  test('with no header the figure reserves the overhang itself', async () => {
    renderFigure({ showPin: true })

    await waitFor(() => expect(screen.getByTestId('time-series-graph')).toBeInTheDocument())
    expect(header()).not.toBeInTheDocument()
    expect(figure()).toHaveClass('graphing-graph-figure--pin-overhang')
  })

  test('a figure without the pin reserves nothing', async () => {
    renderFigure({ showTimestamp: true })

    await waitFor(() => expect(screen.getByTestId('time-series-graph')).toBeInTheDocument())
    expect(header()).not.toHaveClass('graphing-graph-figure__header--pin-gap')
    expect(figure()).not.toHaveClass('graphing-graph-figure--pin-overhang')
  })
})

test("merges a unit-less y-axis prop's explicit range with the metric-derived unit", async () => {
  // The prop carries only the explicit range; the unit must be filled in from the metric.
  renderFigure({ yAxis: { explicit_range: { min: 1, max: 5 } } })
  await screen.findByTestId('time-series-graph')

  expect(screen.getByTestId('y-axis')).toHaveTextContent('set')
  expect(screen.getByTestId('y-axis-range')).toHaveTextContent('5')
  expect(screen.getByTestId('y-axis-unit')).toHaveTextContent('decimal')
})

test('omits the y-axis entirely when the prop has no unit and no metric supplies one', async () => {
  postSpy.mockResolvedValue({
    data: { ...FETCHED, metrics: [] },
    error: undefined,
    response: new Response('{}', { status: 200 })
  } as never)

  renderFigure({ yAxis: { explicit_range: { min: 1, max: 5 } } })
  await screen.findByTestId('time-series-graph')

  // No unit from the prop and none from a metric: the guard yields null, not a unit-less axis.
  expect(screen.getByTestId('y-axis')).toHaveTextContent('null')
})
