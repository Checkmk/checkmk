/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromDate } from '@internationalized/date'
import { screen, waitFor } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import DashboardContentGauge from '@/dashboard/components/DashboardContent/figures/DashboardContentGauge.vue'
import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import type { Gauge, GaugeContent } from '@/dashboard/types/widget'

import {
  renderComputedWidget,
  useComputeWidgetEndpoint
} from '@tests/dashboard/computeWidgetEndpoint'
import { makeContentProps } from '@tests/dashboard/contentProps'

const OTHER_RANGE = {
  from: fromDate(new Date('2026-01-02T00:00:00Z'), 'UTC'),
  to: fromDate(new Date('2026-01-02T01:00:00Z'), 'UTC')
}

const GAUGE: Gauge = {
  links: [],
  link_properties: { links: [] },
  value: 42,
  unit_format: {
    notation: 'decimal',
    symbol: '',
    precision: { type: 'auto', digits: 2 },
    convertible: false
  },
  range: { minimum: 0, maximum: 100 },
  samples: [],
  status: null
}

const CURRENT_VALUE: GaugeContent = {
  type: 'gauge',
  metric: 'load1',
  time_range: 'current',
  display_range: { type: 'fixed', unit: '%', minimum: 0, maximum: 100 }
}

const FOLLOWS_DASHBOARD: GaugeContent = {
  ...CURRENT_VALUE,
  time_range: { type: 'window', window: 'dashboard', consolidation: 'average' }
}

const FIXED_WINDOW: GaugeContent = {
  ...CURRENT_VALUE,
  time_range: {
    type: 'window',
    window: { type: 'predefined', value: 'last_4_hours' },
    consolidation: 'average'
  }
}

const endpoint = useComputeWidgetEndpoint<Gauge>('compute-gauge', () => GAUGE)

async function renderWidget(props: ContentProps<GaugeContent> = makeContentProps(CURRENT_VALUE)) {
  return renderComputedWidget(DashboardContentGauge, props)
}

describe('DashboardContentGauge', () => {
  it('requests the explicit widget with the dashboard time range', async () => {
    await renderWidget()

    await waitFor(() =>
      expect(endpoint.requests).toEqual([
        {
          source: { type: 'explicit', content: CURRENT_VALUE, context: {} },
          time_range: { start: '2026-01-01T00:00:00.000Z', end: '2026-01-01T01:00:00.000Z' }
        }
      ])
    )
  })

  it('draws the value as delivered by the backend', async () => {
    await renderWidget()

    expect(await screen.findByText('42')).toBeInTheDocument()
  })

  it('fetches again when the dashboard range changes and the widget follows it', async () => {
    const { rerender } = await renderWidget(makeContentProps(FOLLOWS_DASHBOARD))
    await screen.findByText('42')

    await rerender(makeContentProps(FOLLOWS_DASHBOARD, { range: OTHER_RANGE }))

    await waitFor(() => expect(endpoint.requests).toHaveLength(2))
  })

  it('does not fetch again when the dashboard range changes under a fixed window', async () => {
    const { rerender } = await renderWidget(makeContentProps(FIXED_WINDOW))
    await screen.findByText('42')

    await rerender(makeContentProps(FIXED_WINDOW, { range: OTHER_RANGE }))
    await rerender(makeContentProps(FIXED_WINDOW, { range: OTHER_RANGE, tick: 1 }))

    await waitFor(() => expect(endpoint.requests).toHaveLength(2))
  })
})
