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

import DashboardContentSingleMetric from '@/dashboard/components/DashboardContent/DashboardContentSingleMetric.vue'
import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import { useProvideIsPublicDashboard } from '@/dashboard/composables/useIsPublicDashboard'
import type { ComputedSingleMetric, SingleMetricContent } from '@/dashboard/types/widget'

import { makeContentProps } from '@tests/dashboard/contentProps'
import { FakeResizeObserver, deliverSize } from '@tests/lib/fakeResizeObserver'

const ENDPOINT = `${location.protocol}//${location.host}/api/internal/domain-types/dashboard/actions/compute-single-metric/invoke`

const OTHER_RANGE = {
  from: fromDate(new Date('2026-01-02T00:00:00Z'), 'UTC'),
  to: fromDate(new Date('2026-01-02T01:00:00Z'), 'UTC')
}

function singleMetric(overrides: Partial<ComputedSingleMetric> = {}): ComputedSingleMetric {
  return {
    value: '801.84',
    unit: 'GB',
    unit_format: {
      notation: 'si',
      symbol: 'B',
      precision: { type: 'auto', digits: 2 },
      convertible: false
    },
    color: '#3CC2FF',
    series: [
      { timestamp: 0, value: 10 },
      { timestamp: 60, value: 20 },
      { timestamp: 120, value: 15 },
      { timestamp: 180, value: 30 }
    ],
    stale: false,
    links: [
      {
        title: 'Service',
        location: { type: 'views', name: 'service', owner: null },
        include_context: false,
        include_time_range: false,
        show_filter_form: false
      }
    ],
    link_properties: {
      links: [
        {
          siteopt: { status: 'encoded', variables: { site: 'heute' } },
          host: { status: 'encoded', variables: { host: 'myhost' } },
          service: { status: 'encoded', variables: { service: 'CPU load' } }
        }
      ]
    },
    state: null,
    range_limits: null,
    range: null,
    ...overrides
  }
}

const CURRENT_VALUE: SingleMetricContent = {
  type: 'single_metric',
  metric: 'load1',
  time_range: 'current',
  display_range: 'automatic',
  show_display_range_limits: false,
  show_delta: true
}

const FOLLOWS_DASHBOARD: SingleMetricContent = {
  ...CURRENT_VALUE,
  time_range: { type: 'window', window: 'dashboard', consolidation: 'average' }
}

const FIXED_WINDOW: SingleMetricContent = {
  ...CURRENT_VALUE,
  time_range: {
    type: 'window',
    window: { type: 'predefined', value: 'last_4_hours' },
    consolidation: 'average'
  }
}

let answer: () => ComputedSingleMetric = () => singleMetric()
let requests: unknown[] = []

useMswServer(
  http.post(ENDPOINT, async ({ request }) => {
    requests.push(await request.json())
    return HttpResponse.json({ domainType: 'widget-compute', value: answer() })
  })
)

async function renderWidget(
  props: ContentProps<SingleMetricContent> = makeContentProps(CURRENT_VALUE),
  { isPublicDashboard = false } = {}
) {
  const wrapper = defineComponent({
    props: { widgetProps: { type: Object, required: true } },
    setup(wrapperProps) {
      if (isPublicDashboard) {
        useProvideIsPublicDashboard()
      }
      return () => h(DashboardContentSingleMetric, wrapperProps.widgetProps as never)
    }
  })
  const rendered = render(wrapper, { props: { widgetProps: props } })
  await nextTick()
  deliverSize(400, 200)
  await screen.findByText('801.84')
  return {
    ...rendered,
    rerender: async (next: ContentProps<SingleMetricContent>) => {
      await rendered.rerender({ widgetProps: next })
    }
  }
}

beforeEach(() => {
  vi.stubGlobal('ResizeObserver', FakeResizeObserver)
})
afterEach(() => {
  answer = () => singleMetric()
  requests = []
  FakeResizeObserver.instances = []
})

describe('DashboardContentSingleMetric', () => {
  it('requests the explicit widget with the dashboard time range', async () => {
    await renderWidget()

    expect(requests).toEqual([
      {
        source: { type: 'explicit', content: CURRENT_VALUE, context: {} },
        time_range: { start: '2026-01-01T00:00:00.000Z', end: '2026-01-01T01:00:00.000Z' }
      }
    ])
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

  it('links the value to the resolved link with its native key', async () => {
    const { container } = await renderWidget()

    expect(container.querySelector('a')).toHaveAttribute(
      'href',
      'view.py?view_name=service&site=heute&host=myhost&service=CPU+load&filled_in=filter&_show_filter_form=0'
    )
  })

  it('does not link the value without a resolved link', async () => {
    answer = () => singleMetric({ links: [], link_properties: { links: [] } })

    const { container } = await renderWidget()

    expect(container.querySelector('a')).toBeNull()
  })

  it('does not link the value on a public dashboard', async () => {
    const { container } = await renderWidget(makeContentProps(CURRENT_VALUE), {
      isPublicDashboard: true
    })

    expect(container.querySelector('a')).toBeNull()
  })

  it('shows the service state when the backend reports one', async () => {
    answer = () => singleMetric({ state: { severity: 'warn', tint_background: true } })

    const { container } = await renderWidget()

    expect(container.querySelector('.db-cmk-kpi-stat-card__state')).toHaveTextContent('WARN')
    expect(container.querySelector('.db-cmk-kpi-stat-card')).toHaveClass(
      'db-cmk-kpi-stat-card--tinted'
    )
  })

  it('labels the range ends when the backend reports them', async () => {
    answer = () => singleMetric({ range_limits: { minimum: '0 B', maximum: '1.00 TB' } })

    const { container } = await renderWidget()

    expect(container.querySelector('.db-cmk-kpi-stat-card__range--minimum')).toHaveTextContent(
      '0 B'
    )
    expect(container.querySelector('.db-cmk-kpi-stat-card__range--maximum')).toHaveTextContent(
      '1.00 TB'
    )
  })

  it('scales the comparison value like the value itself', async () => {
    answer = () =>
      singleMetric({
        series: [
          { timestamp: 0, value: 1_000_000 },
          { timestamp: 60, value: 3_000_000 },
          { timestamp: 120, value: 2_000_000 },
          { timestamp: 180, value: 4_000_000 }
        ]
      })

    const { container } = await renderWidget()

    expect(container.querySelector('.db-cmk-kpi-stat-card__delta-comparison')).toHaveTextContent(
      'vs. 2 MB avg.'
    )
  })

  it('gives the whole widget to the value for the current value alone', async () => {
    answer = () => singleMetric({ series: [] })

    const { container } = await renderWidget()

    expect(container.querySelector('.db-kpi-spark-line')).toBeNull()
    expect(container.querySelector('.db-cmk-kpi-stat-card')).toHaveClass(
      'db-cmk-kpi-stat-card--value-only'
    )
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
})
