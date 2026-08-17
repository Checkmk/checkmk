/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import DashboardContentTimelineCount from '@/dashboard/components/DashboardContent/DashboardContentTimelineCount.vue'
import type { TimelineContent } from '@/dashboard/types/widget'

import { flushPromises } from '../../utils.ts'

const computeTimelineCountData = vi.fn()
vi.mock('@/dashboard/utils.ts', () => ({
  dashboardAPI: {
    computeTimelineCountData: (...args: unknown[]) => computeTimelineCountData(...args)
  }
}))

function props(type: TimelineContent['type'] = 'alert_timeline') {
  return {
    widget_id: 'w1',
    general_settings: {
      title: { text: 'Alert timeline', render_mode: 'with_background' as const },
      render_background: true
    },
    content: {
      type,
      render_mode: {
        type: 'simple_number' as const,
        time_range: { type: 'predefined' as const, value: 'last_25_hours' as const }
      },
      log_target: 'both' as const
    },
    effectiveTitle: 'Problem alerts',
    effective_filter_context: { uses_infos: [], filters: {}, context: {} },
    dashboardKey: { owner: 'cmkadmin', name: 'main' }
  }
}

async function renderWidget(type: TimelineContent['type'] = 'alert_timeline') {
  const rendered = render(DashboardContentTimelineCount, { props: props(type) as never })
  await flushPromises()
  return rendered
}

describe('DashboardContentTimelineCount', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    computeTimelineCountData.mockResolvedValue({ value: { value: '42' } })
  })

  it('shows the count as delivered by the backend', async () => {
    const { container } = await renderWidget()

    expect(container.querySelector('.db-cmk-kpi-stat-card__value')).toHaveTextContent('42')
  })

  it('shows the value alone: a count has no unit, state or spark line', async () => {
    const { container } = await renderWidget()

    expect(container.querySelector('.db-cmk-kpi-stat-card__unit')).toBeNull()
    expect(container.querySelector('.db-cmk-kpi-stat-card__state')).toBeNull()
    expect(container.querySelector('.db-kpi-spark-line')).toBeNull()
    expect(container.querySelector('.db-cmk-kpi-stat-card')).toHaveClass(
      'db-cmk-kpi-stat-card--value-only'
    )
  })

  it('computes the notification timeline through the same endpoint', async () => {
    await renderWidget('notification_timeline')

    expect(computeTimelineCountData).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'notification_timeline' }),
      {}
    )
  })

  it('reloads on its own, as the figure it replaces did', async () => {
    vi.useFakeTimers()
    try {
      await renderWidget()
      expect(computeTimelineCountData).toHaveBeenCalledTimes(1)

      await vi.advanceTimersByTimeAsync(60_000)
      expect(computeTimelineCountData).toHaveBeenCalledTimes(2)
    } finally {
      vi.useRealTimers()
    }
  })
})
