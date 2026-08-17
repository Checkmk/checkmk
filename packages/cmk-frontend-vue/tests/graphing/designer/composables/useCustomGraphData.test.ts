/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { effectScope, nextTick, ref } from 'vue'

import {
  type ApiGraphOptions,
  useCustomGraphData
} from '@/graphing/designer/composables/useCustomGraphData'
import type { GraphItem } from '@/graphing/designer/types'
import type { RequestedTimeRange } from '@/graphing/types'

import { constantItem, rrdMetricItem, rrdQueryItem } from '../fixtures'

const FETCH_PATH = '/domain-types/custom_graph/actions/fetch_data/invoke'
const GRAPH_OPTIONS: ApiGraphOptions = {
  unit: { type: 'first_entry_with_unit' },
  explicit_vertical_range: { type: 'auto' },
  omit_zero_metrics: false
}
const RANGE: RequestedTimeRange = { start: 0, end: 3600 }

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

beforeEach(() => {
  vi.useFakeTimers()
  postSpy = vi.spyOn(client, 'POST')
  postSpy.mockImplementation(async () => ({
    data: fetchResponse(),
    error: undefined,
    response: new Response(null, { status: 200 })
  }))
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

function fetchResponse(
  sourceIds: string[] = ['A'],
  groupTitles: { source_id: string; title: string }[] = []
): unknown {
  return {
    time_range: { start: 0, end: 3600, step: 60 },
    metrics: sourceIds.map((sourceId) => ({
      source_id: sourceId,
      metadata: {
        name: `metric-${sourceId}`,
        source_id: sourceId,
        title: sourceId,
        unit: {
          notation: 'decimal',
          symbol: '',
          precision: { type: 'auto', digits: 2 },
          convertible: false
        },
        color: '#123456'
      },
      render: { stack: null, inverse: false, hidden: false },
      data_points: [1.0, 2.0]
    })),
    group_titles: groupTitles,
    horizontal_lines: [],
    warnings: [],
    errors: []
  }
}

interface Harness {
  items: ReturnType<typeof ref<GraphItem[]>>
  data: ReturnType<typeof useCustomGraphData>
  overviewEnabled: ReturnType<typeof ref<boolean>>
}

function mount(initialItems: GraphItem[], withOverview = false, fetchHidden = false): Harness {
  const items = ref<GraphItem[]>(initialItems)
  const overviewEnabled = ref<boolean>(withOverview)
  const data = useCustomGraphData({
    getItems: () => items.value ?? [],
    getGraphOptions: () => GRAPH_OPTIONS,
    getRequestedTimeRange: () => RANGE,
    getConsolidationFn: () => 'max',
    getFigureWidth: () => 860,
    withOverview: () => overviewEnabled.value ?? false,
    getFetchHidden: () => fetchHidden,
    debounceMs: 400
  })
  return { items, data, overviewEnabled }
}

async function flush(): Promise<void> {
  await vi.runAllTimersAsync()
  await nextTick()
}

test('fetches immediately on mount and exposes the mapped response', async () => {
  const { data } = mount([rrdMetricItem('A')])
  await flush()

  expect(postSpy).toHaveBeenCalledTimes(1)
  const [path, options] = postSpy.mock.calls[0]!
  expect(path).toBe(FETCH_PATH)
  expect(options.body.consolidation_function).toBe('max')
  expect(options.body.requested_time_range).toEqual({ start: 0, end: 3600, step: 60 })
  expect(options.body.content.data_sources.map((source: { id: string }) => source.id)).toEqual([
    'A'
  ])

  expect(data.metrics.value).toHaveLength(1)
  expect(data.dataTimeRange.value).toEqual({ start: 0, end: 3600, step: 60 })
  expect(data.metricsBySource.value.get('A')).toHaveLength(1)
  expect(data.overview.value).toBeUndefined()
})

test('resolves a single-line source to its series title and a fan-out to its group title', async () => {
  postSpy.mockImplementation(async () => ({
    data: fetchResponse(['A', 'B'], [{ source_id: 'B', title: 'CPU load - <HOST_NAME>' }]),
    error: undefined,
    response: new Response(null, { status: 200 })
  }))
  const { data } = mount([rrdMetricItem('A'), rrdQueryItem('B')])
  await flush()

  expect(data.resolvedTitles.value.get('A')).toBe('A')
  expect(data.resolvedTitles.value.get('B')).toBe('CPU load - <HOST_NAME>')
})

test('keeps the resolved titles of the last fetch until the one an edit triggers lands', async () => {
  postSpy.mockImplementation(async () => ({
    data: fetchResponse(['A'], [{ source_id: 'A', title: 'CPU load - <HOST_NAME>' }]),
    error: undefined,
    response: new Response(null, { status: 200 })
  }))
  const { items, data } = mount([rrdQueryItem('A')])
  await flush()
  expect(data.resolvedTitles.value.get('A')).toBe('CPU load - <HOST_NAME>')

  items.value = [rrdMetricItem('A')]
  await nextTick()
  expect(data.resolvedTitles.value.get('A')).toBe('CPU load - <HOST_NAME>')

  await flush()
  expect(data.resolvedTitles.value.get('A')).toBe('A')
})

test('fetches hidden rows as visible so their stats are available', async () => {
  postSpy.mockImplementation(async () => ({
    data: fetchResponse(['A', 'B']),
    error: undefined,
    response: new Response(null, { status: 200 })
  }))
  const { data } = mount([rrdMetricItem('A'), rrdMetricItem('B', { visible: false })], false, true)
  await flush()

  const sent = postSpy.mock.calls[0]![1].body.content.data_sources
  expect(
    sent.map((source: { id: string; visible: boolean }) => [source.id, source.visible])
  ).toEqual([
    ['A', true],
    ['B', true]
  ])
  expect(data.metricsBySource.value.get('B')).toHaveLength(1)
})

test('toggling visibility does not refetch when hidden lines are fetched', async () => {
  postSpy.mockImplementation(async () => ({
    data: fetchResponse(['A', 'B']),
    error: undefined,
    response: new Response(null, { status: 200 })
  }))
  const { items } = mount([rrdMetricItem('A'), rrdMetricItem('B')], false, true)
  await flush()
  expect(postSpy).toHaveBeenCalledTimes(1)

  items.value = [rrdMetricItem('A'), rrdMetricItem('B', { visible: false })]
  await flush()
  expect(postSpy).toHaveBeenCalledTimes(1)
})

test('posts the real visibility when not fetching hidden lines', async () => {
  const { items } = mount([rrdMetricItem('A')])
  await flush()
  expect(postSpy.mock.calls[0]![1].body.content.data_sources[0].visible).toBe(true)

  items.value = [rrdMetricItem('A', { visible: false })]
  await flush()
  expect(postSpy).toHaveBeenCalledTimes(2)
  expect(postSpy.mock.calls[1]![1].body.content.data_sources[0].visible).toBe(false)
})

test('skips the request entirely once there is nothing left to draw', async () => {
  const { data, items } = mount([rrdMetricItem('A')])
  await flush()
  expect(postSpy).toHaveBeenCalledTimes(1)
  expect(
    postSpy.mock.calls[0]![1].body.content.data_sources.map((source: { id: string }) => source.id)
  ).toEqual(['A'])

  items.value = []
  await flush()
  expect(postSpy).toHaveBeenCalledTimes(1)
  expect(data.metrics.value).toEqual([])
  expect(data.dataTimeRange.value).toBeUndefined()
})

test('debounces edits into a single request', async () => {
  const { items } = mount([rrdMetricItem('A')])
  await flush()
  expect(postSpy).toHaveBeenCalledTimes(1)

  items.value = [rrdMetricItem('A'), constantItem('B')]
  await vi.advanceTimersByTimeAsync(200)
  items.value = [rrdMetricItem('A'), constantItem('B', { value: 7 })]
  await vi.advanceTimersByTimeAsync(200)
  expect(postSpy).toHaveBeenCalledTimes(1)

  await flush()
  expect(postSpy).toHaveBeenCalledTimes(2)
})

test('refetch bypasses a pending debounce', async () => {
  const { items, data } = mount([rrdMetricItem('A')])
  await flush()
  expect(postSpy).toHaveBeenCalledTimes(1)

  items.value = [rrdMetricItem('A'), constantItem('B')]
  await nextTick()
  data.refetch()
  await vi.advanceTimersByTimeAsync(0)
  expect(postSpy).toHaveBeenCalledTimes(2)

  // The debounced call was cancelled: nothing further fires.
  await flush()
  expect(postSpy).toHaveBeenCalledTimes(2)
})

test('disposing the owning scope cancels a pending debounce', async () => {
  const scope = effectScope()
  const harness = scope.run(() => mount([rrdMetricItem('A')]))!
  await flush()
  expect(postSpy).toHaveBeenCalledTimes(1)

  harness.items.value = [rrdMetricItem('B')]
  await nextTick()
  scope.stop()
  await flush()
  expect(postSpy).toHaveBeenCalledTimes(1)
})

test('fetches the wider overview domain only when enabled', async () => {
  const { data, overviewEnabled } = mount([rrdMetricItem('A')], true)
  await flush()

  expect(postSpy).toHaveBeenCalledTimes(2)
  const overviewBody = postSpy.mock.calls[1]![1].body
  const span = overviewBody.requested_time_range.end - overviewBody.requested_time_range.start
  expect(span).toBeGreaterThan(RANGE.end - RANGE.start)
  expect(data.overview.value).toBeDefined()

  overviewEnabled.value = false
  await flush()
  expect(postSpy).toHaveBeenCalledTimes(3)
  expect(data.overview.value).toBeUndefined()
})

test('a stale response does not overwrite a newer one', async () => {
  let resolveFirst: (value: unknown) => void = () => {}
  postSpy.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        resolveFirst = resolve
      })
  )
  const { items, data } = mount([rrdMetricItem('A')])
  await nextTick()

  items.value = [rrdMetricItem('B')]
  await flush()
  expect(data.metricsBySource.value.has('A')).toBe(true)

  resolveFirst({
    data: fetchResponse(['STALE']),
    error: undefined,
    response: new Response(null, { status: 200 })
  })
  await flush()
  expect(data.metricsBySource.value.has('STALE')).toBe(false)
})

test('exposes request errors and recovers on the next fetch', async () => {
  postSpy.mockImplementationOnce(async () => ({
    data: undefined,
    error: { title: 'boom' },
    response: new Response('', { status: 500 })
  }))
  const { data } = mount([rrdMetricItem('A')])
  await flush()
  expect(data.error.value).not.toBeNull()

  data.refetch()
  await flush()
  expect(data.error.value).toBeNull()
  expect(data.metrics.value).toHaveLength(1)
})

test("exposes the response's own non-fatal errors and warnings, each apart", async () => {
  postSpy.mockImplementationOnce(async () => ({
    data: {
      ...(fetchResponse(['A']) as object),
      errors: ['Metrics backend is unavailable.'],
      warnings: ['The query for A matched more than 100 time series.']
    },
    error: undefined,
    response: new Response(null, { status: 200 })
  }))
  const { data } = mount([rrdMetricItem('A')])
  await flush()

  expect(data.partialErrors.value).toEqual(['Metrics backend is unavailable.'])
  // Apart from the errors, so a truncation can be stated as advisory rather than as a failure.
  expect(data.warnings.value).toEqual(['The query for A matched more than 100 time series.'])
  // Non-fatal, both of them: the fetch itself succeeded.
  expect(data.error.value).toBeNull()
})

test('keeps a failure visible while the retry is still in flight', async () => {
  postSpy.mockImplementationOnce(async () => ({
    data: undefined,
    error: { title: 'boom' },
    response: new Response('', { status: 500 })
  }))
  const { data } = mount([rrdMetricItem('A')])
  await flush()
  expect(data.error.value).not.toBeNull()

  let release!: () => void
  postSpy.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        release = () =>
          resolve({
            data: fetchResponse(['A']),
            error: undefined,
            response: new Response(null, { status: 200 })
          })
      })
  )
  data.refetch()
  await flush()

  // Still set, so the caller can state the failure until a result supersedes it.
  expect(data.isLoading.value).toBe(true)
  expect(data.error.value).not.toBeNull()

  release()
  await flush()
  expect(data.error.value).toBeNull()
})

test('clears the diagnostics when the last data source is removed', async () => {
  postSpy.mockImplementationOnce(async () => ({
    data: {
      ...(fetchResponse(['A']) as object),
      errors: ['Metrics backend is unavailable.'],
      warnings: ['The query for A matched more than 100 time series.']
    },
    error: undefined,
    response: new Response(null, { status: 200 })
  }))
  const { data, items } = mount([rrdMetricItem('A')])
  await flush()
  expect(data.partialErrors.value).toHaveLength(1)
  expect(data.warnings.value).toHaveLength(1)

  // Removing the last row short-circuits load() through clear(), which never reaches the
  // success path that would otherwise reassign them.
  items.value = []
  await flush()

  expect(data.partialErrors.value).toEqual([])
  expect(data.warnings.value).toEqual([])
  expect(data.metrics.value).toEqual([])
})
