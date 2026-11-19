/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromDate } from '@internationalized/date'
import { render, screen, waitFor } from '@testing-library/vue'
import { restApiHttp } from 'cmk-ui-library/vitest.msw'
import {
  resizeObserverReporting,
  useFakeResizeObserver
} from 'cmk-ui-library/vitest.resize-observer'
import { describe, expect, it } from 'vitest'

import DashboardContentTimelineCount from '@/dashboard/components/DashboardContent/figures/DashboardContentTimelineCount.vue'
import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import type { TimelineContent } from '@/dashboard/types/widget'

import { useComputeWidgetEndpoint } from '@tests/dashboard/computeWidgetEndpoint'
import { makeContentProps } from '@tests/dashboard/contentProps'

const OTHER_RANGE = {
  from: fromDate(new Date('2026-01-02T00:00:00Z'), 'UTC'),
  to: fromDate(new Date('2026-01-02T01:00:00Z'), 'UTC')
}

const HOST_FILTER = { host: { host: 'myhost' } }

const FOLLOWS_DASHBOARD: TimelineContent = {
  type: 'alert_timeline',
  log_target: 'both',
  render_mode: { type: 'simple_number', time_range: 'dashboard' }
}

const FIXED_WINDOW: TimelineContent = {
  ...FOLLOWS_DASHBOARD,
  render_mode: {
    type: 'simple_number',
    time_range: { type: 'predefined', value: 'last_25_hours' }
  }
}

const endpoint = useComputeWidgetEndpoint(
  restApiHttp.post,
  '/domain-types/dashboard/actions/compute-timeline-count/invoke',
  { count: 42 }
)
useFakeResizeObserver(resizeObserverReporting(400, 200))

async function renderWidget(props: ContentProps<TimelineContent>) {
  const rendered = render(DashboardContentTimelineCount, { props })
  await screen.findByText('42')
  return rendered
}

describe('DashboardContentTimelineCount', () => {
  it('requests the explicit widget with the dashboard time range', async () => {
    await renderWidget(makeContentProps(FOLLOWS_DASHBOARD))

    expect(endpoint.requests).toEqual([
      {
        source: { type: 'explicit', content: FOLLOWS_DASHBOARD, context: {} },
        time_range: { start: '2026-01-01T00:00:00.000Z', end: '2026-01-01T01:00:00.000Z' }
      }
    ])
  })

  it('shows the count as the value of the card', async () => {
    await renderWidget(makeContentProps(FOLLOWS_DASHBOARD))

    expect(screen.getByText('42')).toBeInTheDocument()
  })

  it('fetches again when the dashboard range changes and the widget follows it', async () => {
    const { rerender } = await renderWidget(makeContentProps(FOLLOWS_DASHBOARD))

    await rerender(makeContentProps(FOLLOWS_DASHBOARD, { range: OTHER_RANGE }))

    await waitFor(() =>
      expect(endpoint.requests.map((request) => request.time_range)).toEqual([
        { start: '2026-01-01T00:00:00.000Z', end: '2026-01-01T01:00:00.000Z' },
        { start: '2026-01-02T00:00:00.000Z', end: '2026-01-02T01:00:00.000Z' }
      ])
    )
  })

  it('does not fetch again when the dashboard range changes under a fixed window', async () => {
    const { rerender } = await renderWidget(makeContentProps(FIXED_WINDOW))

    await rerender(makeContentProps(FIXED_WINDOW, { range: OTHER_RANGE }))
    // A separate rerender, so that a wrong fetch for the range change comes before this one.
    await rerender(
      makeContentProps(FIXED_WINDOW, {
        range: OTHER_RANGE,
        effective_filter_context: { uses_infos: [], filters: HOST_FILTER, restricted_to_single: [] }
      })
    )

    await waitFor(() =>
      expect(endpoint.requests.map((request) => request.source)).toEqual([
        { type: 'explicit', content: FIXED_WINDOW, context: {} },
        { type: 'explicit', content: FIXED_WINDOW, context: HOST_FILTER }
      ])
    )
  })
})
