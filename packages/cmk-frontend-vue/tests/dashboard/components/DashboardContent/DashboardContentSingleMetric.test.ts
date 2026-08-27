/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import DashboardContentSingleMetric from '@/dashboard/components/DashboardContent/DashboardContentSingleMetric.vue'
import { useProvideIsPublicDashboard } from '@/dashboard/composables/useIsPublicDashboard'
import type { ComputedSingleMetric, SingleMetricContent } from '@/dashboard/types/widget'

import { flushPromises } from '../../utils.ts'

const computeSingleMetricData = vi.fn()
vi.mock('@/dashboard/utils.ts', () => ({
  dashboardAPI: {
    computeSingleMetricData: (...args: unknown[]) => computeSingleMetricData(...args)
  }
}))

function singleMetric(overrides: Partial<ComputedSingleMetric> = {}): ComputedSingleMetric {
  return {
    value: '801.84',
    unit: 'GB',
    color: '#3CC2FF',
    series: [
      { timestamp: 0, value: 10 },
      { timestamp: 60, value: 20 },
      { timestamp: 120, value: 15 },
      { timestamp: 180, value: 30 }
    ],
    stale: false,
    url: 'view.py?view_name=service',
    ...overrides
  }
}

function props(content: Partial<SingleMetricContent> = {}) {
  return {
    widget_id: 'w1',
    general_settings: {
      title: { text: 'Single metric', render_mode: 'with_background' as const },
      render_background: true
    },
    content: {
      type: 'single_metric' as const,
      metric: 'load1',
      time_range: 'current' as const,
      display_range: 'automatic' as const,
      show_display_range_limits: false,
      ...content
    },
    effectiveTitle: 'CPU load',
    effective_filter_context: { uses_infos: [], filters: {}, context: {} },
    dashboardKey: { owner: 'cmkadmin', name: 'main' }
  }
}

async function renderWidget(
  content: Partial<SingleMetricContent> = {},
  { isPublicDashboard = false } = {}
) {
  const componentProps = props(content)
  const wrapper = defineComponent({
    setup() {
      if (isPublicDashboard) {
        useProvideIsPublicDashboard()
      }
      return () => h(DashboardContentSingleMetric, componentProps as never)
    }
  })
  const rendered = render(wrapper)
  await flushPromises()
  return rendered
}

describe('DashboardContentSingleMetric', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    computeSingleMetricData.mockResolvedValue({ value: singleMetric() })
  })

  it('shows the value and its unit as delivered by the backend', async () => {
    const { container } = await renderWidget()

    expect(container.querySelector('.db-cmk-kpi-stat-card__value')).toHaveTextContent('801.84')
    expect(container.querySelector('.db-cmk-kpi-stat-card__unit')).toHaveTextContent('GB')
  })

  it('takes the metric color as the accent color', async () => {
    const { container } = await renderWidget()

    expect(
      container
        .querySelector<HTMLElement>('.db-cmk-kpi-stat-card')
        ?.style.getPropertyValue('--accent-color')
    ).toBe('#3CC2FF')
  })

  it('links the value into the service view', async () => {
    const { container } = await renderWidget()

    expect(container.querySelector('a')).toHaveAttribute('href', 'view.py?view_name=service')
  })

  it('does not link the value on a public dashboard', async () => {
    const { container } = await renderWidget({}, { isPublicDashboard: true })

    expect(container.querySelector('a')).toBeNull()
  })

  it('shows the service state when the backend reports one', async () => {
    computeSingleMetricData.mockResolvedValue({
      value: singleMetric({
        state: { severity: 'warn', tint_background: true }
      })
    })
    const { container } = await renderWidget()

    expect(container.querySelector('.db-cmk-kpi-stat-card__state')).toHaveTextContent('WARN')
    expect(container.querySelector('.db-cmk-kpi-stat-card')).toHaveClass(
      'db-cmk-kpi-stat-card--tinted'
    )
  })

  it('labels the range ends when the backend reports them', async () => {
    computeSingleMetricData.mockResolvedValue({
      value: singleMetric({ range_limits: { minimum: '0 B', maximum: '1.00 TB' } })
    })
    const { container } = await renderWidget()

    expect(container.querySelector('.db-cmk-kpi-stat-card__range--minimum')).toHaveTextContent(
      '0 B'
    )
    expect(container.querySelector('.db-cmk-kpi-stat-card__range--maximum')).toHaveTextContent(
      '1.00 TB'
    )
  })

  it('reloads on its own, as the figure it replaces did', async () => {
    vi.useFakeTimers()
    try {
      await renderWidget()
      expect(computeSingleMetricData).toHaveBeenCalledTimes(1)

      await vi.advanceTimersByTimeAsync(60_000)
      expect(computeSingleMetricData).toHaveBeenCalledTimes(2)
    } finally {
      vi.useRealTimers()
    }
  })

  it('gives the whole widget to the value for the current value alone', async () => {
    computeSingleMetricData.mockResolvedValue({ value: singleMetric({ series: [] }) })
    const { container } = await renderWidget()

    expect(container.querySelector('.db-kpi-spark-line')).toBeNull()
    expect(container.querySelector('.db-cmk-kpi-stat-card')).toHaveClass(
      'db-cmk-kpi-stat-card--value-only'
    )
  })
})
