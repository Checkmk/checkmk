/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDateTime, type ZonedDateTime, toZoned } from '@internationalized/date'
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import type { CmkTimeSeriesGraph } from 'cmk-shared-typing/typescript/cmk_time_series_graph'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { nextTick } from 'vue'

import { useGlobalTimeRange } from '@/graphing/GlobalTimePicker/useGlobalTimeRange'
import GraphGroup from '@/graphing/components/GraphGroup.vue'

// Stub keeps the test independent of the panel's rendering; the buttons simulate local
// time range interactions reported back to the group: "pan" keeps the span,
// "zoom" changes it.
vi.mock('@/graphing/components/GraphPanel.vue', () => ({
  default: {
    props: ['metrics', 'dataTimeRange', 'requestedTimeRange', 'title'],
    emits: ['update:requestedTimeRange', 'update:consolidationFn'],
    template: `<div data-testid="graph-panel">
      <span>{{ title }}</span>
      <button @click="$emit('update:requestedTimeRange', { start: 1500, end: 2500 }, 'translated_timerange')">
        pan
      </button>
      <button @click="$emit('update:requestedTimeRange', { start: 100, end: 200 }, 'changed_timerange_span')">
        zoom
      </button>
    </div>`
  }
}))

const TZ = 'Europe/Berlin'
const zoned = (day: number): ZonedDateTime =>
  toZoned(new CalendarDateTime(2026, 3, day, 0, 0), TZ, 'compatible')
const range = (fromDay: number, toDay: number): DateTimeRange => ({
  from: zoned(fromDay),
  to: zoned(toDay)
})
const epochSeconds = (value: ZonedDateTime): number => Math.floor(value.toDate().getTime() / 1000)

const UNIT: components['schemas']['ApiUnitFormat'] = {
  notation: 'decimal',
  symbol: '',
  precision: { type: 'auto', digits: 2 },
  convertible: true
}

function makeGraphDefinition(title: string): CmkTimeSeriesGraph {
  return {
    size: { width: 70, height: 16, mode: 'fixed' },
    options: {
      header: { title, show_graph_time: true },
      name: title.toLowerCase(),
      x_axis: null,
      y_axis: null,
      font_size_pt: 8
    },
    interaction: {
      brush: 'enabled',
      burger: 'enabled',
      zoom: 'enabled',
      panning: 'enabled',
      hover: 'enabled',
      pin: 'enabled'
    },
    internal: '{"graphs": []}'
  }
}

const FETCHED = {
  metrics: [
    {
      metadata: { name: 'cpu', title: 'CPU', unit: UNIT, color: '#ff0000' },
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

const requestedRanges = (): { start: number; end: number; step: number }[] =>
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  postSpy.mock.calls.map((call: any) => call[1].body.requested_time_range)

beforeEach(() => {
  useGlobalTimeRange().setActiveTimeRange(null)
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

const skeletons = (): NodeListOf<Element> => document.querySelectorAll('.graphing-graph-skeleton')

const group = (): Element | null => document.querySelector('.graphing-graph-group')

function renderGroup(graphs: CmkTimeSeriesGraph[] = [makeGraphDefinition('CPU utilization')]) {
  return render(GraphGroup, {
    props: {
      initial_time_range_start: 1_000,
      initial_time_range_end: 2_000,
      graphs
    }
  })
}

test('holds the skeletons back for a second, then shows one per graph definition', async () => {
  vi.useFakeTimers()
  postSpy.mockReturnValue(new Promise(() => {}))
  renderGroup([makeGraphDefinition('CPU utilization'), makeGraphDefinition('Memory')])

  await nextTick()
  expect(skeletons()).toHaveLength(0)

  vi.advanceTimersByTime(1_000)
  await nextTick()

  expect(skeletons()).toHaveLength(2)
  // The skeletons are aria-hidden; the announcement comes from the group's live region.
  expect(screen.getByRole('status')).toBeInTheDocument()
})

test('reports the busy state from the first moment, ahead of the skeletons', async () => {
  vi.useFakeTimers()
  postSpy.mockReturnValue(new Promise(() => {}))
  renderGroup()

  await nextTick()
  expect(skeletons()).toHaveLength(0)
  expect(group()).toHaveAttribute('aria-busy', 'true')
})

test('stays clear of the busy state while refetching with panels on screen', async () => {
  renderGroup()
  // Waiting on the request count would be too early: it is still an initial load until data lands.
  expect(await screen.findAllByTestId('graph-panel')).toHaveLength(1)
  expect(group()).toHaveAttribute('aria-busy', 'false')

  postSpy.mockReturnValue(new Promise(() => {}))
  await fireEvent.click(await screen.findByText('pan'))
  await nextTick()

  expect(document.querySelectorAll('[data-testid="graph-panel"]')).toHaveLength(1)
  expect(group()).toHaveAttribute('aria-busy', 'false')
})

test('an error arriving after the skeletons are up replaces them', async () => {
  vi.useFakeTimers()
  let fail!: (reason: Error) => void
  postSpy.mockReturnValue(
    new Promise((_resolve, reject) => {
      fail = reject
    })
  )
  renderGroup()

  vi.advanceTimersByTime(1_000)
  await nextTick()
  expect(skeletons()).toHaveLength(1)

  fail(new Error('crash'))
  await vi.advanceTimersByTimeAsync(0)

  expect(skeletons()).toHaveLength(0)
  expect(screen.getByText('crash')).toBeInTheDocument()
  expect(group()).toHaveAttribute('aria-busy', 'false')
})

test('a fast load resolves straight into the panels without a skeleton', async () => {
  vi.useFakeTimers()
  renderGroup()

  // Flush the already-resolved fetch without reaching the one-second threshold.
  await vi.advanceTimersByTimeAsync(999)
  expect(document.querySelectorAll('[data-testid="graph-panel"]')).toHaveLength(1)
  expect(skeletons()).toHaveLength(0)
  expect(group()).toHaveAttribute('aria-busy', 'false')

  // The pending delay must have been cancelled, not merely outrun by the data.
  await vi.advanceTimersByTimeAsync(1_000)
  expect(skeletons()).toHaveLength(0)
})

test('renders one panel per graph definition once data arrives', async () => {
  renderGroup([makeGraphDefinition('CPU utilization'), makeGraphDefinition('Memory')])

  expect(await screen.findAllByTestId('graph-panel')).toHaveLength(2)
  expect(screen.getByText('CPU utilization')).toBeInTheDocument()
  expect(screen.getByText('Memory')).toBeInTheDocument()
})

test('shows the error message when fetching fails', async () => {
  postSpy.mockRejectedValue(new Error('crash'))
  renderGroup()
  expect(await screen.findByText('crash')).toBeInTheDocument()
})

test('fetches the graph with the initial range and the overview with the multiplied domain', async () => {
  renderGroup()

  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(2))
  const body = postSpy.mock.calls[0][1].body
  expect(body.internal).toBe('{"graphs": []}')
  expect(body.consolidation_function).toBe('avg')
  const ranges = requestedRanges()
  expect(ranges).toContainEqual({ start: 1_000, end: 2_000, step: 60 })
  // 1000s active span → 7× multiplier → 7000s overview domain centered on the range.
  expect(ranges).toContainEqual({ start: -2_000, end: 5_000, step: 60 })
})

test('fetches graph and overview with the combination mode from props', async () => {
  render(GraphGroup, {
    props: {
      initial_time_range_start: 1_000,
      initial_time_range_end: 2_000,
      graphs: [makeGraphDefinition('CPU utilization')],
      combination_mode: 'stacked' as const
    }
  })

  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(2))
  expect(postSpy.mock.calls[0][1].body.combination_mode).toBe('stacked')
  expect(postSpy.mock.calls[1][1].body.combination_mode).toBe('stacked')
})

test('refetches graph and overview when the global picker publishes a range', async () => {
  renderGroup()
  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(2))

  const published = range(9, 10)
  useGlobalTimeRange().setActiveTimeRange(published)

  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(4))
  const start = epochSeconds(published.from)
  const end = epochSeconds(published.to)
  const ranges = requestedRanges().slice(2)
  expect(ranges).toContainEqual(expect.objectContaining({ start, end }))
  // 24h active span → 7× multiplier → the overview reseeds symmetrically around it.
  expect(ranges).toContainEqual(
    expect.objectContaining({ start: start - 3 * 86_400, end: end + 3 * 86_400 })
  )
})

test('a same-span panel commit (move) refetches the graph but keeps the overview fixed', async () => {
  renderGroup()
  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(2))

  await fireEvent.click(await screen.findByText('pan'))

  // Only the main graph refetches; the moved window {1500, 2500} sits well inside
  // the overview domain {-2000, 5000}, so the overview must not be requested again.
  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(3))
  expect(requestedRanges()[2]).toEqual({ start: 1_500, end: 2_500, step: 60 })
  expect(postSpy).toHaveBeenCalledTimes(3)
})

test('a span-changing panel commit (resize/zoom) reseeds the overview domain', async () => {
  renderGroup()
  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(2))

  await fireEvent.click(await screen.findByText('zoom'))

  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(4))
  const ranges = requestedRanges().slice(2)
  expect(ranges).toContainEqual({ start: 100, end: 200, step: 60 })
  // 100s span → 7× multiplier → 700s overview domain centered on the new range.
  expect(ranges).toContainEqual({ start: -200, end: 500, step: 60 })
})
