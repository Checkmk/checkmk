/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type * as intl from '@internationalized/date'
import { render, screen, waitFor } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'
import { afterEach, describe, expect, it, vi } from 'vitest'

import DashboardContentTimeline from '@/dashboard/components/DashboardContent/DashboardContentTimeline.vue'
import type { TimelineContent } from '@/dashboard/types/widget'

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

const ENDPOINT = `${location.protocol}//${location.host}/api/internal/domain-types/dashboard/actions/compute-timeline/invoke`

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

interface TimelineRequest {
  source: unknown
  time_range: { start: string; end: string }
  step: number
}

let requests: TimelineRequest[] = []
function countsOnGrid(request: TimelineRequest, step: number): Response {
  const start = Date.parse(request.time_range.start) / 1000
  const end = Date.parse(request.time_range.end) / 1000
  return HttpResponse.json({
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
  })
}

function countsPerStep(request: TimelineRequest): Response {
  return countsOnGrid(request, request.step)
}

let respond: (request: TimelineRequest) => Response = countsPerStep

useMswServer(
  http.post(ENDPOINT, async ({ request }) => {
    const body = (await request.json()) as TimelineRequest
    requests.push(body)
    return respond(body)
  })
)

afterEach(() => {
  respond = countsPerStep
  requests = []
})

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

  it('draws the counts as one bar series binned by the configured unit', async () => {
    render(DashboardContentTimeline, { props: makeContentProps(HOURLY) })

    expect(await screen.findByTestId('shape')).toHaveTextContent('bar')
    expect(screen.getByTestId('bin-unit')).toHaveTextContent('hour')
    expect(screen.getByTestId('title')).toHaveTextContent('Host notifications')
    expect(screen.getByTestId('counts')).toHaveTextContent(/^0,1,2,3/)
  })

  it('draws on the grid that the backend answers, not on the one it asked for', async () => {
    respond = (request) => countsOnGrid(request, HOUR / 2)

    render(DashboardContentTimeline, { props: makeContentProps(HOURLY) })

    expect(await screen.findByTestId('data-step')).toHaveTextContent(String(HOUR / 2))
  })

  it('zooms no deeper than one bin', async () => {
    render(DashboardContentTimeline, { props: makeContentProps(HOURLY) })

    expect(await screen.findByTestId('min-time-range')).toHaveTextContent(String(HOUR))
  })

  it('shows the no-data notice when the backend finds no data', async () => {
    respond = () => HttpResponse.json({ title: 'No data available', status: 404 }, { status: 404 })

    render(DashboardContentTimeline, { props: makeContentProps(HOURLY) })

    expect(await screen.findByText('No data available')).toBeInTheDocument()
  })

  it('states a failed fetch', async () => {
    respond = () =>
      HttpResponse.json({ title: 'Bad request', status: 400, detail: 'Too long' }, { status: 400 })

    render(DashboardContentTimeline, { props: makeContentProps(HOURLY) })

    expect(await screen.findByText('Graph data could not be loaded.')).toBeInTheDocument()
  })

  it('explains a window that follows the dashboard instead of fetching', async () => {
    const followsDashboard: TimelineContent = {
      ...HOURLY,
      render_mode: { type: 'bar_chart', time_range: 'dashboard', time_resolution: 'day' }
    }

    render(DashboardContentTimeline, { props: makeContentProps(followsDashboard) })

    expect(
      await screen.findByText('This widget follows the dashboard time range')
    ).toBeInTheDocument()
    expect(requests).toHaveLength(0)
  })
})
