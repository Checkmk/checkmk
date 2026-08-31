/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, waitFor } from '@testing-library/vue'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'

import {
  initGlobalRefresh,
  resetGlobalTimeState,
  useGlobalRefresh
} from '@/graphing/GlobalTimePicker/globalTimeState'
import { timestampAt } from '@/graphing/components/TimeSeriesGraph/axes/timeAxis'
import {
  type GraphDataFetcher,
  type GraphFetchParams,
  useGraphData
} from '@/graphing/composables/useGraphData'
import type { RequestedTimeRange } from '@/graphing/types'

const UNIT: components['schemas']['ApiUnitFormat'] = {
  notation: 'decimal',
  symbol: '',
  precision: { type: 'auto', digits: 2 },
  convertible: true
}

const FETCHED = {
  title: 'CPU load - 8 CPU cores',
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

beforeEach(() => {
  resetGlobalTimeState()
  postSpy = vi.spyOn(client, 'POST')
  postSpy.mockResolvedValue({
    data: FETCHED,
    error: undefined,
    response: new Response('{}', { status: 200 })
  } as never)
})

afterEach(() => {
  resetGlobalTimeState()
  vi.restoreAllMocks()
})

// The resize debounce registers onUnmounted, so this needs a mounted component.
function fetchFor(range: RequestedTimeRange, canvasWidth: number): void {
  const harness = defineComponent({
    setup() {
      useGraphData(
        () => [{ internal: '{"graphs": []}', add_type: null }],
        () => range,
        () => canvasWidth,
        () => ['max']
      )
      return () => h('div')
    }
  })
  render(harness)
}

async function requestedTimeRange(): Promise<{ start: number; end: number; step: number }> {
  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(1))
  return postSpy.mock.calls[0][1].body.requested_time_range
}

test('a resolved graph takes its title from the fetched data, not from the definition', async () => {
  // A plug-in's title expression is only substituted once there is data, so the definition's title
  // still carries the raw marker at render time. The header must not read that one.
  const titles: string[] = []
  const harness = defineComponent({
    setup() {
      const { graphs } = useGraphData(
        () => [
          {
            internal: '{"graphs": []}',
            add_to: null,
            options: {
              header: {
                title: 'CPU load - _EXPRESSION:{"metric":"load1","scalar":"max"} CPU cores',
                show_graph_time: true
              },
              name: 'cpu_load'
            }
          } as never
        ],
        () => ({ start: 0, end: 3_600 }),
        () => 800,
        () => ['max']
      )
      return () => {
        titles.splice(0, titles.length, ...graphs.value.map((graph) => graph.title))
        return h('div')
      }
    }
  })

  render(harness)

  await waitFor(() => expect(titles).toEqual(['CPU load - 8 CPU cores']))
})

// The backend cannot serve a step finer than 60s, and asking for one only buys query load
// and holes in the series.
describe('useGraphData — requested resolution', () => {
  test('never asks for a step below a minute, however narrow the window', async () => {
    const halfMinute = { start: 1_000, end: 1_030 }

    fetchFor(halfMinute, 750)

    expect((await requestedTimeRange()).step).toBe(60)
  })

  test('asks for several samples per plotted column on a wide window', async () => {
    const eightDays = { start: 0, end: 8 * 86_400 }
    const columns = 750

    fetchFor(eightDays, columns)

    const { step } = await requestedTimeRange()
    const samplesPerColumn = (eightDays.end - eightDays.start) / step / columns
    expect(samplesPerColumn).toBeCloseTo(4, 1)
  })

  test('a window reaching past the retained data keeps its full span', async () => {
    const fourHundredDays = { start: 0, end: 400 * 86_400 }

    fetchFor(fourHundredDays, 750)

    const { start, end } = await requestedTimeRange()
    expect(start).toBeLessThanOrEqual(fourHundredDays.start)
    expect(end).toBeGreaterThanOrEqual(fourHundredDays.end)
  })

  test('asks for a sample past the end of the window it will draw', async () => {
    const window = { start: 10_000, end: 20_000 }

    fetchFor(window, 750)

    expect((await requestedTimeRange()).end).toBeGreaterThan(window.end)
  })

  test('asks far enough back that the first sample falls before the window starts', async () => {
    const window = { start: 10_000, end: 20_000 }
    const firstValueIndex = 0

    fetchFor(window, 750)

    expect(timestampAt(await requestedTimeRange(), firstValueIndex)).toBeLessThan(window.start)
  })
})

function renderWithFetcher(
  fetchGraph: GraphDataFetcher,
  range: RequestedTimeRange = { start: 0, end: 3_600 }
): ReturnType<typeof useGraphData> {
  let exposed!: ReturnType<typeof useGraphData>
  const harness = defineComponent({
    setup() {
      exposed = useGraphData(
        () => [{ internal: '{"graphs": []}', add_to: null } as never],
        () => range,
        () => 800,
        () => ['max'],
        () => null,
        { fetchGraph }
      )
      return () => h('div')
    }
  })
  render(harness)
  return exposed
}

// The brush pairs its overview data with the strip extent that data covers, and neither end of
// that pairing survives the round trip on its own.
test('a resolved graph reports the range it was asked for, not the window it was fetched with', async () => {
  const asked = { start: 10_000, end: 20_000 }
  const fetchWindows: GraphFetchParams['fetchWindow'][] = []

  const { graphs } = renderWithFetcher(async (_definition, params) => {
    fetchWindows.push(params.fetchWindow)
    return {
      title: 'CPU',
      metrics: [],
      // Deliberately unlike `asked`: the backend answers on its own storage grid.
      timeRange: { start: 9_000, end: 21_000, step: 300 },
      horizontalLines: [],
      errors: [],
      warnings: []
    }
  }, asked)

  await waitFor(() => expect(graphs.value).toHaveLength(1))
  expect(graphs.value[0]!.requestedTimeRange).toEqual(asked)
  // Unrecoverable from either side of the round trip: the request is widened by its edge
  // neighbours, and the response above lands somewhere else again.
  expect(fetchWindows[0]!.start).toBeLessThan(asked.start)
  expect(fetchWindows[0]!.end).toBeGreaterThan(asked.end)
})

test('a fetcher that reports no diagnostics fields leaves them empty', async () => {
  // `GraphDataFetcher` is a public extension point, and one supplied from untyped code can omit the
  // fields. Unguarded, flatMap folds that into a one-element array and the caller states a notice
  // over a fetch that in fact succeeded.
  const { graphs, partialErrors, warnings } = renderWithFetcher((async () => ({
    title: 'CPU',
    metrics: [],
    timeRange: { start: 0, end: 3_600, step: 60 },
    horizontalLines: []
  })) as never)

  // Waiting on the resolved graphs, not on the call: the diagnostics are assigned only after the
  // fetch settles, so asserting earlier would read the initial empty value either way.
  await waitFor(() => expect(graphs.value).toHaveLength(1))
  // Length, not toEqual: that ignores undefined array items and would read [undefined] as empty.
  expect(partialErrors.value).toHaveLength(0)
  expect(warnings.value).toHaveLength(0)
})

test("exposes a fetch's warnings apart from its errors", async () => {
  const { graphs, partialErrors, warnings } = renderWithFetcher(async () => ({
    title: 'CPU',
    metrics: [],
    timeRange: { start: 0, end: 3_600, step: 60 },
    horizontalLines: [],
    errors: [],
    warnings: ['The query for CPU matched more than 100 time series.']
  }))

  await waitFor(() => expect(graphs.value).toHaveLength(1))
  expect(warnings.value).toEqual(['The query for CPU matched more than 100 time series.'])
  // Apart, so a caller can state a truncation as advisory rather than as a failure.
  expect(partialErrors.value).toHaveLength(0)
})

describe('the page refresh', () => {
  const A_RANGE = { start: 0, end: 3_600 }
  const A_CANVAS_WIDTH = 800
  // Never reports back, so the content reload stays in flight for the whole test.
  const RELOADING_CONTENT = { intervalSeconds: 30, live: false, strategy: () => {} }

  const loadsSoFar = (): number => postSpy.mock.calls.length

  test('a refresh re-fetches, even though the window has not moved', async () => {
    fetchFor(A_RANGE, A_CANVAS_WIDTH)
    await waitFor(() => expect(loadsSoFar()).toBe(1))
    const loadsBefore = loadsSoFar()

    useGlobalRefresh().resumeRefresh()

    await waitFor(() => expect(loadsSoFar()).toBe(loadsBefore + 1))
  })

  test('a refresh whose content swap will unmount this graph fetches nothing', async () => {
    initGlobalRefresh(RELOADING_CONTENT)
    fetchFor(A_RANGE, A_CANVAS_WIDTH)
    await waitFor(() => expect(loadsSoFar()).toBe(1))
    const loadsBefore = loadsSoFar()

    useGlobalRefresh().resumeRefresh()
    await nextTick()
    await nextTick()

    expect(loadsSoFar()).toBe(loadsBefore)
  })

  test('a graph mounting while a content reload is in flight still loads', async () => {
    initGlobalRefresh(RELOADING_CONTENT)
    useGlobalRefresh().resumeRefresh()

    fetchFor(A_RANGE, A_CANVAS_WIDTH)

    await waitFor(() => expect(loadsSoFar()).toBe(1))
  })
})
