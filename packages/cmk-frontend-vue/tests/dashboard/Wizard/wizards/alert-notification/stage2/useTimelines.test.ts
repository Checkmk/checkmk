/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'

import type {
  AlertTimelineContent,
  NotificationTimelineContent,
  WidgetProps
} from '@/dashboard/components/Wizard/types'
import { useAlertTimeline } from '@/dashboard/components/Wizard/wizards/alert-notification/stage2/AlertTimeline/composables/useAlertTimeline'
import { useNotificationTimeline } from '@/dashboard/components/Wizard/wizards/alert-notification/stage2/NotificationTimeline/composables/useNotificationTimeline'
import { useProvideDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'

type TimelineContent = AlertTimelineContent | NotificationTimelineContent
type TimelineWindow = TimelineContent['render_mode']['time_range']

interface TimelineHandler {
  getSubmitProps: () => Promise<WidgetProps>
}

const API = `${location.protocol}//${location.host}/api/internal/domain-types/dashboard/actions`

const WIDGET_CONSTANTS: DashboardConstants['widgets'][string] = {
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

const CONSTANTS: DashboardConstants = {
  responsive_grid_breakpoints: {},
  widgets: { alert_timeline: WIDGET_CONSTANTS, notification_timeline: WIDGET_CONSTANTS }
}

useMswServer(
  http.post(`${API}/compute-widget-titles/invoke`, () =>
    HttpResponse.json({ extensions: { titles: { preview_widget: 'Timeline' } } })
  ),
  http.post(`${API}/compute-widget-attributes/invoke`, () =>
    HttpResponse.json({ value: { filter_context: { uses_infos: [] } } })
  )
)

const FIXED_WINDOW: TimelineWindow = { type: 'predefined', value: 'last_25_hours' }

function storedTimeline(type: TimelineContent['type'], window: TimelineWindow): WidgetSpec {
  return {
    content: {
      type,
      log_target: 'both',
      render_mode: { type: 'bar_chart', time_range: window, time_resolution: 'hour' }
    },
    filter_context: { filters: {}, uses_infos: [] },
    general_settings: {
      title: { text: 'Timeline', render_mode: 'with_background' },
      render_background: true
    }
  }
}

async function openWizard(
  useTimeline: (filters: ConfiguredFilters, spec: WidgetSpec | null) => Promise<TimelineHandler>,
  currentSpec: WidgetSpec | null
): Promise<TimelineHandler> {
  let handler: Promise<TimelineHandler> | undefined
  const consumer = defineComponent({
    setup() {
      handler = useTimeline({}, currentSpec)
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

async function submittedWindow(handler: TimelineHandler): Promise<TimelineWindow> {
  const { content } = await handler.getSubmitProps()
  if (content.type !== 'alert_timeline' && content.type !== 'notification_timeline') {
    throw new Error(`The wizard submitted a ${content.type} widget.`)
  }
  return content.render_mode.time_range
}

describe.each([
  ['alert_timeline', useAlertTimeline],
  ['notification_timeline', useNotificationTimeline]
] as const)('the %s wizard', (type, useTimeline) => {
  it('reads back a stored fixed window and submits it unchanged', async () => {
    const handler = await openWizard(useTimeline, storedTimeline(type, FIXED_WINDOW))

    expect(await submittedWindow(handler)).toEqual(FIXED_WINDOW)
  })

  it('starts a widget that follows the dashboard from the default fixed window', async () => {
    const newWidget = await openWizard(useTimeline, null)
    const followingWidget = await openWizard(useTimeline, storedTimeline(type, 'dashboard'))

    const submitted = await submittedWindow(followingWidget)

    expect(submitted).not.toBe('dashboard')
    expect(submitted).toEqual(await submittedWindow(newWidget))
  })
})
