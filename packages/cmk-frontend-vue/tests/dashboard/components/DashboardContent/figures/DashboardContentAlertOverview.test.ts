/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromDate } from '@internationalized/date'
import { render, screen, waitFor } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import DashboardContentAlertOverview from '@/dashboard/components/DashboardContent/figures/DashboardContentAlertOverview.vue'
import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import type { AlertOverview, AlertOverviewContent } from '@/dashboard/types/widget'

import { makeContentProps } from '@tests/dashboard/contentProps'
import { FakeResizeObserver, deliverSize } from '@tests/lib/fakeResizeObserver'

const ENDPOINT = `${location.protocol}//${location.host}/api/internal/domain-types/dashboard/actions/compute-alert-overview/invoke`

const OTHER_RANGE = {
  from: fromDate(new Date('2026-01-02T00:00:00Z'), 'UTC'),
  to: fromDate(new Date('2026-01-02T01:00:00Z'), 'UTC')
}

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

let answer: () => Response = () => HttpResponse.json({ domainType: 'widget-compute', value: VALUE })
let requests: unknown[] = []

const server = setupServer(
  http.post(ENDPOINT, async ({ request }) => {
    requests.push(await request.json())
    return answer()
  })
)

async function renderWidget(
  props: ContentProps<AlertOverviewContent> = makeContentProps(FOLLOWS_DASHBOARD)
) {
  const rendered = render(DashboardContentAlertOverview, { props })
  await nextTick()
  deliverSize(400, 200)
  return rendered
}

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
beforeEach(() => {
  vi.stubGlobal('ResizeObserver', FakeResizeObserver)
})
afterEach(() => {
  answer = () => HttpResponse.json({ domainType: 'widget-compute', value: VALUE })
  requests = []
  server.resetHandlers()
  FakeResizeObserver.instances = []
  vi.unstubAllGlobals()
})
afterAll(() => server.close())

describe('DashboardContentAlertOverview', () => {
  it('requests the explicit widget with the dashboard time range', async () => {
    await renderWidget()

    await waitFor(() =>
      expect(requests).toEqual([
        {
          source: { type: 'explicit', content: FOLLOWS_DASHBOARD, context: {} },
          time_range: { start: '2026-01-01T00:00:00.000Z', end: '2026-01-01T01:00:00.000Z' }
        }
      ])
    )
  })

  it('draws the alerts as delivered by the backend', async () => {
    await renderWidget()

    expect(await screen.findByRole('figure', { name: '1 object with alerts' })).toBeInTheDocument()
  })

  it('fetches again on a refresh tick', async () => {
    const { rerender } = await renderWidget()
    await screen.findByRole('figure')

    await rerender(makeContentProps(FOLLOWS_DASHBOARD, { tick: 1 }))

    await waitFor(() => expect(requests).toHaveLength(2))
  })

  it('fetches again when the dashboard range changes and the widget follows it', async () => {
    const { rerender } = await renderWidget(makeContentProps(FOLLOWS_DASHBOARD))

    await rerender(makeContentProps(FOLLOWS_DASHBOARD, { range: OTHER_RANGE }))

    await waitFor(() => expect(requests).toHaveLength(2))
  })

  it('does not fetch again when the dashboard range changes under a fixed window', async () => {
    const { rerender } = await renderWidget(makeContentProps(FIXED_WINDOW))

    await rerender(makeContentProps(FIXED_WINDOW, { range: OTHER_RANGE }))
    await rerender(makeContentProps(FIXED_WINDOW, { range: OTHER_RANGE, tick: 1 }))

    await waitFor(() => expect(requests).toHaveLength(2))
  })

  it('shows the no-data notice on a 404', async () => {
    answer = () => HttpResponse.json({ title: 'No data available', status: 404 }, { status: 404 })

    await renderWidget()

    expect(await screen.findByText('No data available')).toBeInTheDocument()
  })
})
