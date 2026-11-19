/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type * as intl from '@internationalized/date'
import { render, screen, waitFor } from '@testing-library/vue'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'
import {
  resizeObserverReporting,
  useFakeResizeObserver
} from 'cmk-ui-library/vitest.resize-observer'
import { describe, expect, it, vi } from 'vitest'

import DashboardContentTimeline from '@/dashboard/components/DashboardContent/DashboardContentTimeline.vue'
import type { TimelineContent } from '@/dashboard/types/widget'

import { useRequestRecords } from '@tests/dashboard/apiHandlers'
import { makeContentProps } from '@tests/dashboard/contentProps'

vi.mock('@/graphing/components/TimeSeriesGraph', () => ({
  default: {
    inheritAttrs: false,
    props: ['metrics', 'data_time_range', 'binUnit', 'minTimeRange'],
    template: `<div data-testid="time-series-graph">
      <span data-testid="data-step">{{ data_time_range.step }}</span>
      <span data-testid="bin-unit">{{ binUnit }}</span>
      <span data-testid="min-time-range">{{ minTimeRange }}</span>
      <span data-testid="shape">{{ metrics[0]?.render.shape }}</span>
      <span data-testid="title">{{ metrics[0]?.metadata.title }}</span>
      <span data-testid="counts">{{ metrics[0]?.data_points.join(',') }}</span>
    </div>`
  }
}))

vi.mock('@internationalized/date', async (importOriginal) => {
  const actual = await importOriginal<typeof intl>()
  return { ...actual, getLocalTimeZone: () => 'UTC' }
})

const HOUR = 3600

const HOURLY: TimelineContent = {
  type: 'notification_timeline',
  log_target: 'host',
  render_mode: {
    type: 'bar_chart',
    time_range: { type: 'age', hours: 4 },
    time_resolution: 'hour'
  }
}

type TimelineRequest = components['schemas']['TimelineRequest']
type TimelineResponse = components['schemas']['ComputedWidgetResponse_GraphFetchResponse_']

const requests = useRequestRecords<TimelineRequest>()
function countsOnGrid(request: TimelineRequest, step: number): TimelineResponse {
  const start = Date.parse(request.time_range.start) / 1000
  const end = Date.parse(request.time_range.end) / 1000
  return {
    domainType: 'widget-compute',
    value: {
      title: '',
      time_range: { start, end, step },
      metrics: [
        {
          metadata: {
            name: 'notification',
            title: 'Host notifications',
            unit: {
              notation: 'decimal',
              symbol: '',
              precision: { type: 'strict', digits: 0 },
              convertible: false
            },
            color: '#00b9ff',
            attributes: []
          },
          render: { shape: 'bar', stack: null, aggregation: 'sum', inverse: false, hidden: false },
          data_points: Array.from({ length: (end - start) / step }, (_, index) => index)
        }
      ],
      horizontal_lines: [],
      shaded_regions: [],
      warnings: [],
      errors: []
    }
  }
}

const server = useMswServer(
  restApiHttp.post(
    '/domain-types/dashboard/actions/compute-timeline/invoke',
    async ({ request, response }) => {
      const body = await request.json()
      requests.push(body)
      return response(200).json(countsOnGrid(body, body.step))
    }
  )
)

useFakeResizeObserver(resizeObserverReporting(800, 200))

describe('DashboardContentTimeline', () => {
  it('requests whole local hours on the hour grid', async () => {
    render(DashboardContentTimeline, { props: makeContentProps(HOURLY) })

    await waitFor(() => expect(requests).toHaveLength(1))
    const [request] = requests
    const start = Date.parse(request!.time_range.start) / 1000
    const end = Date.parse(request!.time_range.end) / 1000
    expect(request!.source).toEqual({ type: 'explicit', content: HOURLY, context: {} })
    expect(request!.step).toBe(HOUR)
    expect(start % HOUR).toBe(0)
    expect(end % HOUR).toBe(0)
  })

  it('cancels its pending request when it unmounts', async () => {
    const signals: AbortSignal[] = []
    server.use(
      restApiHttp.post('/domain-types/dashboard/actions/compute-timeline/invoke', ({ request }) => {
        signals.push(request.signal)
        return new Promise<never>(() => {})
      })
    )

    const view = render(DashboardContentTimeline, { props: makeContentProps(HOURLY) })
    await waitFor(() => expect(signals).toHaveLength(1))
    view.unmount()

    expect(signals[0]!.aborted).toBe(true)
  })

  it('draws the counts as one bar series binned by the configured unit', async () => {
    render(DashboardContentTimeline, { props: makeContentProps(HOURLY) })

    expect(await screen.findByTestId('shape')).toHaveTextContent('bar')
    expect(screen.getByTestId('bin-unit')).toHaveTextContent('hour')
    expect(screen.getByTestId('title')).toHaveTextContent('Host notifications')
    expect(screen.getByTestId('counts')).toHaveTextContent(/^0,1,2,3/)
  })

  it('draws on the grid that the backend answers, not on the one it asked for', async () => {
    server.use(
      restApiHttp.post(
        '/domain-types/dashboard/actions/compute-timeline/invoke',
        async ({ request, response }) =>
          response(200).json(countsOnGrid(await request.json(), HOUR / 2))
      )
    )

    render(DashboardContentTimeline, { props: makeContentProps(HOURLY) })

    expect(await screen.findByTestId('data-step')).toHaveTextContent(String(HOUR / 2))
  })

  it('zooms no deeper than one bin', async () => {
    render(DashboardContentTimeline, { props: makeContentProps(HOURLY) })

    expect(await screen.findByTestId('min-time-range')).toHaveTextContent(String(HOUR))
  })

  it('shows the no-data notice when the backend finds no data', async () => {
    server.use(
      restApiHttp.post('/domain-types/dashboard/actions/compute-timeline/invoke', ({ response }) =>
        response(404).json({
          title: 'No data available',
          status: 404,
          detail: 'The time range has no events.'
        })
      )
    )

    render(DashboardContentTimeline, { props: makeContentProps(HOURLY) })

    expect(await screen.findByText('No data available')).toBeInTheDocument()
  })

  it('states a failed fetch', async () => {
    server.use(
      restApiHttp.post('/domain-types/dashboard/actions/compute-timeline/invoke', ({ response }) =>
        response(400).json({ title: 'Bad request', status: 400, detail: 'Too long' })
      )
    )

    render(DashboardContentTimeline, { props: makeContentProps(HOURLY) })

    expect(await screen.findByText('Graph data could not be loaded.')).toBeInTheDocument()
  })

  it("fetches the dashboard's range while it follows the dashboard", async () => {
    const followsDashboard: TimelineContent = {
      ...HOURLY,
      render_mode: { type: 'bar_chart', time_range: 'dashboard', time_resolution: 'hour' }
    }

    render(DashboardContentTimeline, { props: makeContentProps(followsDashboard) })

    await waitFor(() => expect(requests).toHaveLength(1))
    expect(requests[0]!.time_range).toEqual({
      start: '2026-01-01T00:00:00.000Z',
      end: '2026-01-01T01:00:00.000Z'
    })
  })
})
