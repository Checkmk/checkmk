/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromDate } from '@internationalized/date'
import { render, screen, waitFor } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'

import DashboardContentTimelineCount from '@/dashboard/components/DashboardContent/DashboardContentTimelineCount.vue'
import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import type { TimelineContent } from '@/dashboard/types/widget'

import { makeContentProps } from '@tests/dashboard/contentProps'
import { FakeResizeObserver, deliverSize } from '@tests/lib/fakeResizeObserver'

const ENDPOINT = `${location.protocol}//${location.host}/api/internal/domain-types/dashboard/actions/compute-timeline-count/invoke`

const OTHER_RANGE = {
  from: fromDate(new Date('2026-01-02T00:00:00Z'), 'UTC'),
  to: fromDate(new Date('2026-01-02T01:00:00Z'), 'UTC')
}

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

let respond: () => Response = () =>
  HttpResponse.json({ domainType: 'widget-compute', value: { count: 42 } })
let requests: unknown[] = []

useMswServer(
  http.post(ENDPOINT, async ({ request }) => {
    requests.push(await request.json())
    return respond()
  })
)

async function renderWidget(props: ContentProps<TimelineContent>) {
  const wrapper = defineComponent({
    props: { widgetProps: { type: Object, required: true } },
    setup(wrapperProps) {
      return () => h(DashboardContentTimelineCount, wrapperProps.widgetProps as never)
    }
  })
  const rendered = render(wrapper, { props: { widgetProps: props } })
  await nextTick()
  deliverSize(400, 200)
  await waitFor(() => expect(requests).toHaveLength(1))
  return {
    ...rendered,
    rerender: async (next: ContentProps<TimelineContent>) => {
      await rendered.rerender({ widgetProps: next })
    }
  }
}

beforeEach(() => {
  vi.stubGlobal('ResizeObserver', FakeResizeObserver)
})
afterEach(() => {
  respond = () => HttpResponse.json({ domainType: 'widget-compute', value: { count: 42 } })
  requests = []
  FakeResizeObserver.instances = []
})

describe('DashboardContentTimelineCount', () => {
  it('requests the explicit widget with the dashboard time range', async () => {
    await renderWidget(makeContentProps(FOLLOWS_DASHBOARD))

    expect(requests).toEqual([
      {
        source: { type: 'explicit', content: FOLLOWS_DASHBOARD, context: {} },
        time_range: { start: '2026-01-01T00:00:00.000Z', end: '2026-01-01T01:00:00.000Z' }
      }
    ])
  })

  it('shows the count as the value of the card', async () => {
    await renderWidget(makeContentProps(FOLLOWS_DASHBOARD))

    expect(await screen.findByText('42')).toBeInTheDocument()
  })

  it('fetches again on a refresh tick', async () => {
    const { rerender } = await renderWidget(makeContentProps(FIXED_WINDOW))

    await rerender(makeContentProps(FIXED_WINDOW, { tick: 1 }))

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

  it('shows the no-data notice when the backend finds no data', async () => {
    respond = () => HttpResponse.json({ title: 'No data available', status: 404 }, { status: 404 })

    await renderWidget(makeContentProps(FOLLOWS_DASHBOARD))

    expect(await screen.findByText('No data available')).toBeInTheDocument()
  })
})
