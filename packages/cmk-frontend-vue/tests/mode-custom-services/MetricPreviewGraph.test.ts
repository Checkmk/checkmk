/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import type { Aggregator } from 'cmk-shared-typing/typescript/aggregation'
import type { ConsolidationFunction } from 'cmk-shared-typing/typescript/consolidation'
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'
import { afterEach, beforeEach, expect, test } from 'vitest'

import { resetGlobalTimeState } from '@/graphing/GlobalTimePicker/globalTimeState'
import MetricPreviewGraph from '@/mode-custom-services/steps/MetricPreviewGraph.vue'

const FETCH_DATA_URL = `${location.protocol}//${location.host}/api/internal/domain-types/custom_graph/actions/fetch_data/invoke`

const TIME_PICKER: GlobalTimePickerProps = {
  custom_time_ranges: [
    { title: 'Last 4 h', total_seconds: 4 * 3600 },
    { title: 'Last 25 h', total_seconds: 25 * 3600 }
  ],
  default_time_range: 4 * 3600,
  server_time_zone: 'UTC',
  first_day_of_week: null,
  refresh: {
    interval_seconds: null,
    interval_choices_seconds: [30, 60],
    starts_live: true,
    reloads_page_content: false
  }
}

const GAUGE_LAST: ConsolidationFunction = {
  type: 'gauge',
  function: 'gauge_last',
  lookback_seconds: 120
}

const HOST_SUM: Aggregator = {
  stages: [
    {
      aggregate_by: [{ kind: 'resource', name: 'host.name' }],
      aggregation_fn: { type: 'scalar', name: 'sum' }
    }
  ]
}

interface FetchBody {
  content: { data_sources: Record<string, unknown>[] }
  requested_time_range: { start: number; end: number }
}

function series(title: string): unknown {
  return {
    source_id: 'A',
    metadata: {
      name: title,
      title,
      unit: {
        notation: 'decimal',
        symbol: '',
        precision: { type: 'auto', digits: 2 },
        convertible: false
      },
      color: '#28a2f3',
      attributes: []
    },
    render: { shape: 'line', inverse: false, hidden: false },
    data_points: [1, 2]
  }
}

let fetchBodies: FetchBody[] = []
let responseSeries: unknown[] = []

useMswServer(
  http.post(FETCH_DATA_URL, async ({ request }) => {
    fetchBodies.push((await request.json()) as FetchBody)
    return HttpResponse.json({
      time_range: { start: 0, end: 3600, step: 60 },
      metrics: responseSeries,
      group_titles: [],
      horizontal_lines: [],
      warnings: [],
      errors: [],
      internal: '{"graphs":[]}'
    })
  })
)

beforeEach(() => {
  resetGlobalTimeState()
})

afterEach(() => {
  cleanup()
  resetGlobalTimeState()
  fetchBodies = []
  responseSeries = []
})

function renderPreview(metricName: string | null = 'http.server.duration') {
  return render(MetricPreviewGraph, {
    props: {
      metricName,
      attributeFilter: undefined,
      consolidation: GAUGE_LAST,
      aggregator: undefined,
      timePicker: TIME_PICKER
    },
    global: { stubs: { TimeSeriesGraph: true } }
  })
}

async function lastFetch(): Promise<FetchBody> {
  await waitFor(() => expect(fetchBodies.length).toBeGreaterThan(0))
  return fetchBodies.at(-1)!
}

test('without a metric it asks for one and fetches nothing', async () => {
  renderPreview(null)

  expect(await screen.findByText('No metric selected')).toBeInTheDocument()
  expect(fetchBodies).toEqual([])
})

test('a changed selection is fetched with its filter and group-by', async () => {
  const { rerender } = renderPreview()
  await lastFetch()

  await rerender({
    metricName: 'http.server.duration',
    attributeFilter: {
      type: 'and',
      conjuncts: [
        { type: 'equals', key: { kind: 'resource', name: 'service.name' }, value: 'checkout' }
      ]
    },
    consolidation: GAUGE_LAST,
    aggregator: HOST_SUM,
    timePicker: TIME_PICKER
  })

  await waitFor(() =>
    expect(fetchBodies.at(-1)!.content.data_sources).toEqual([
      expect.objectContaining({
        type: 'telemetry_metrics',
        metric_name: 'http.server.duration',
        attribute_filter: {
          type: 'and',
          conjuncts: [
            { type: 'equals', key: { kind: 'resource', name: 'service.name' }, value: 'checkout' }
          ]
        },
        consolidation_function: GAUGE_LAST,
        aggregator: HOST_SUM
      })
    ])
  )
})

test('shows a legend row per returned series', async () => {
  responseSeries = [series('checkout - web01'), series('checkout - web02')]
  renderPreview()

  expect(await screen.findByText('checkout - web01')).toBeInTheDocument()
  expect(screen.getByText('checkout - web02')).toBeInTheDocument()
})

test('a selection without data says so', async () => {
  renderPreview()

  expect(await screen.findByText('No data available')).toBeInTheDocument()
})

test('picking a time range fetches that window', async () => {
  renderPreview()
  await lastFetch()

  await userEvent.click(screen.getByRole('button', { name: 'Last 25 h' }))

  await waitFor(() => {
    const { start, end } = fetchBodies.at(-1)!.requested_time_range
    expect(end - start).toBe(25 * 3600)
  })
})
