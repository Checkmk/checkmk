/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromDate } from '@internationalized/date'
import { render, screen, waitFor } from '@testing-library/vue'
import { restApiHttp } from 'cmk-ui-library/vitest.msw'
import { describe, expect, it } from 'vitest'

import DashboardContentAlertOverview from '@/dashboard/components/DashboardContent/figures/DashboardContentAlertOverview.vue'
import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import type { AlertOverview, AlertOverviewContent } from '@/dashboard/types/widget'

import { useComputeWidgetEndpoint } from '@tests/dashboard/computeWidgetEndpoint'
import { makeContentProps } from '@tests/dashboard/contentProps'
import { resizeObserverReporting, useFakeResizeObserver } from '@tests/lib/fakeResizeObserver'

const OTHER_RANGE = {
  from: fromDate(new Date('2026-01-02T00:00:00Z'), 'UTC'),
  to: fromDate(new Date('2026-01-02T01:00:00Z'), 'UTC')
}

const HOST_FILTER = { host: { host: 'myhost' } }

const VALUE: AlertOverview = {
  elements: [
    {
      site_id: 'heute',
      host_name: 'myhost',
      service_description: 'CPU load',
      num_ok: 1,
      num_warn: 1,
      num_crit: 1,
      num_unknown: 0,
      num_problems: 2,
      links: [],
      link_properties: { links: [] }
    }
  ]
}

const FOLLOWS_DASHBOARD: AlertOverviewContent = { type: 'alert_overview', time_range: 'dashboard' }

const FIXED_WINDOW: AlertOverviewContent = {
  type: 'alert_overview',
  time_range: { type: 'predefined', value: 'last_25_hours' }
}

const endpoint = useComputeWidgetEndpoint(
  restApiHttp.post,
  '/domain-types/dashboard/actions/compute-alert-overview/invoke',
  VALUE
)
useFakeResizeObserver(resizeObserverReporting(400, 200))

async function renderWidget(
  props: ContentProps<AlertOverviewContent> = makeContentProps(FOLLOWS_DASHBOARD)
) {
  const rendered = render(DashboardContentAlertOverview, { props })
  await screen.findByRole('figure', { name: '1 object with alerts' })
  return rendered
}

describe('DashboardContentAlertOverview', () => {
  it('requests the explicit widget with the dashboard time range', async () => {
    await renderWidget()

    expect(endpoint.requests).toEqual([
      {
        source: { type: 'explicit', content: FOLLOWS_DASHBOARD, context: {} },
        time_range: { start: '2026-01-01T00:00:00.000Z', end: '2026-01-01T01:00:00.000Z' }
      }
    ])
  })

  it('draws the alerts as delivered by the backend', async () => {
    await renderWidget()

    expect(screen.getByRole('figure', { name: '1 object with alerts' })).toBeInTheDocument()
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
