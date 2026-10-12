/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromDate } from '@internationalized/date'
import { screen, waitFor } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import DashboardContentTimelineCount from '@/dashboard/components/DashboardContent/figures/DashboardContentTimelineCount.vue'
import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import type { TimelineContent, TimelineCount } from '@/dashboard/types/widget'

import {
  renderComputedWidget,
  useComputeWidgetEndpoint
} from '@tests/dashboard/computeWidgetEndpoint'
import { makeContentProps } from '@tests/dashboard/contentProps'

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

const endpoint = useComputeWidgetEndpoint<TimelineCount>('compute-timeline-count', () => ({
  count: 42
}))

async function renderWidget(props: ContentProps<TimelineContent>) {
  const rendered = await renderComputedWidget(DashboardContentTimelineCount, props)
  await waitFor(() => expect(endpoint.requests).toHaveLength(1))
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

    expect(await screen.findByText('42')).toBeInTheDocument()
  })

  it('fetches again when the dashboard range changes and the widget follows it', async () => {
    const { rerender } = await renderWidget(makeContentProps(FOLLOWS_DASHBOARD))

    await rerender(makeContentProps(FOLLOWS_DASHBOARD, { range: OTHER_RANGE }))

    await waitFor(() => expect(endpoint.requests).toHaveLength(2))
  })

  it('does not fetch again when the dashboard range changes under a fixed window', async () => {
    const { rerender } = await renderWidget(makeContentProps(FIXED_WINDOW))

    await rerender(makeContentProps(FIXED_WINDOW, { range: OTHER_RANGE }))
    await rerender(makeContentProps(FIXED_WINDOW, { range: OTHER_RANGE, tick: 1 }))

    await waitFor(() => expect(endpoint.requests).toHaveLength(2))
  })
})
