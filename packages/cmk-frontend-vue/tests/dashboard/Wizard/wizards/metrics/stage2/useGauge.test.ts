/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'

import type { GaugeContent } from '@/dashboard/components/Wizard/types'
import {
  type UseGauge,
  useGauge
} from '@/dashboard/components/Wizard/wizards/metrics/stage2/GaugeWidget/composables/useGauge'
import { useProvideDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'

const API = `${location.protocol}//${location.host}/api/internal/domain-types/dashboard/actions`

const CONSTANTS: DashboardConstants = {
  responsive_grid_breakpoints: {},
  widgets: {
    gauge: {
      filter_context: { restricted_to_single: [] },
      layout: {
        relative: {
          initial_position: { x: 1, y: 1 },
          initial_size: { width: 10, height: 10 },
          is_resizable: true,
          minimum_size: { width: 1, height: 1 }
        },
        responsive: {}
      },
      title_macros: []
    }
  }
}

const server = setupServer(
  http.post(`${API}/compute-widget-titles/invoke`, () =>
    HttpResponse.json({ extensions: { titles: { preview_widget: 'Gauge' } } })
  ),
  http.post(`${API}/compute-widget-attributes/invoke`, () =>
    HttpResponse.json({ value: { filter_context: { uses_infos: [] } } })
  )
)

function storedGauge(timeRange: GaugeContent['time_range']): WidgetSpec {
  return {
    content: {
      type: 'gauge',
      metric: 'load1',
      time_range: timeRange,
      display_range: { type: 'fixed', unit: '', minimum: 0, maximum: 4 }
    },
    filter_context: { filters: {}, uses_infos: [] },
    general_settings: {
      title: { text: 'Gauge', render_mode: 'with_background' },
      render_background: true
    }
  }
}

async function openGauge(currentSpec: WidgetSpec | null = null): Promise<UseGauge> {
  let handler: Promise<UseGauge> | undefined
  const consumer = defineComponent({
    setup() {
      handler = useGauge('load1', {}, currentSpec)
      return () => h('div')
    }
  })
  render(
    defineComponent({
      setup() {
        useProvideDashboardConstants(CONSTANTS)
        return () => h(consumer)
      }
    })
  )
  return handler!
}

async function submittedTimeRange(handler: UseGauge): Promise<GaugeContent['time_range']> {
  const { content } = await handler.getSubmitProps()
  if (content.type !== 'gauge') {
    throw new Error(`The wizard submitted a ${content.type} widget.`)
  }
  return content.time_range
}

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('useGauge', () => {
  it('shows the current value for a new gauge', async () => {
    const handler = await openGauge()

    expect(handler.timeRangeType.value).toBe('current')
    expect(await submittedTimeRange(handler)).toBe('current')
  })

  it('follows the dashboard when a new gauge shows historic values', async () => {
    const handler = await openGauge()

    handler.timeRangeType.value = 'window'

    expect(handler.followDashboardTimeRange.value).toBe(true)
    expect(await submittedTimeRange(handler)).toEqual({
      type: 'window',
      window: 'dashboard',
      consolidation: 'average'
    })
  })

  it('reads back a stored window that follows the dashboard', async () => {
    const stored = { type: 'window', window: 'dashboard', consolidation: 'average' } as const

    const handler = await openGauge(storedGauge(stored))

    expect(handler.timeRangeType.value).toBe('window')
    expect(await submittedTimeRange(handler)).toEqual(stored)
  })

  it('reads back a stored separate window', async () => {
    const stored = {
      type: 'window',
      window: { type: 'graph', duration: 3600 },
      consolidation: 'average'
    } as const

    const handler = await openGauge(storedGauge(stored))

    expect(handler.followDashboardTimeRange.value).toBe(false)
    expect(await submittedTimeRange(handler)).toEqual(stored)
  })
})
