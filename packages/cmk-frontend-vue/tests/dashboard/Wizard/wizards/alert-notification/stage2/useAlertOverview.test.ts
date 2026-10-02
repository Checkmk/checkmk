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

import type { AlertOverviewContent } from '@/dashboard/components/Wizard/types'
import {
  type UseAlertOverview,
  useAlertOverview
} from '@/dashboard/components/Wizard/wizards/alert-notification/stage2/AlertOverview/composables/useAlertOverview'
import { useProvideDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'

const API = `${location.protocol}//${location.host}/api/internal/domain-types/dashboard/actions`

const CONSTANTS: DashboardConstants = {
  responsive_grid_breakpoints: {},
  widgets: {
    alert_overview: {
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
    HttpResponse.json({ extensions: { titles: { preview_widget: 'Alert overview' } } })
  ),
  http.post(`${API}/compute-widget-attributes/invoke`, () =>
    HttpResponse.json({ value: { filter_context: { uses_infos: [] } } })
  )
)

function storedAlertOverview(timeRange: AlertOverviewContent['time_range']): WidgetSpec {
  return {
    content: { type: 'alert_overview', time_range: timeRange },
    filter_context: { filters: {}, uses_infos: [] },
    general_settings: {
      title: { text: 'Alert overview', render_mode: 'with_background' },
      render_background: true
    }
  }
}

async function openAlertOverview(currentSpec: WidgetSpec | null = null): Promise<UseAlertOverview> {
  let handler: Promise<UseAlertOverview> | undefined
  const consumer = defineComponent({
    setup() {
      handler = useAlertOverview({}, currentSpec)
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

async function submittedTimeRange(
  handler: UseAlertOverview
): Promise<AlertOverviewContent['time_range']> {
  const { content } = await handler.getSubmitProps()
  if (content.type !== 'alert_overview') {
    throw new Error(`The wizard submitted a ${content.type} widget.`)
  }
  return content.time_range
}

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('useAlertOverview', () => {
  it('follows the dashboard time range for a new widget', async () => {
    const handler = await openAlertOverview()

    expect(handler.followDashboardTimeRange.value).toBe(true)
    expect(await submittedTimeRange(handler)).toBe('dashboard')
  })

  it('reads back a stored fixed window and submits it unchanged', async () => {
    const window: AlertOverviewContent['time_range'] = {
      type: 'predefined',
      value: 'last_25_hours'
    }
    const handler = await openAlertOverview(storedAlertOverview(window))

    expect(handler.followDashboardTimeRange.value).toBe(false)
    expect(await submittedTimeRange(handler)).toEqual(window)
  })
})
