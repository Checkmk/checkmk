/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
// eslint-disable-next-line no-restricted-imports -- pre-existing violation: type these handlers, never copy this line
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'
import { type Ref, defineComponent, h } from 'vue'

import type { UseWidgetHandler } from '@/dashboard/components/Wizard/types'
import { usePercentageOfServiceProblems } from '@/dashboard/components/Wizard/wizards/alert-notification/stage2/PercentageOfServiceProblems/composables/usePercentageOfServiceProblems'
import { useCustomGraph } from '@/dashboard/components/Wizard/wizards/custom-graphs/stage1/composables/useCustomGraph'
import { useCombinedGraph } from '@/dashboard/components/Wizard/wizards/metrics/stage2/CombinedGraphWidget/composables/useCombinedGraph'
import { useGraph } from '@/dashboard/components/Wizard/wizards/metrics/stage2/GraphWidget/composables/useGraph'
import { usePerformanceGraph } from '@/dashboard/components/Wizard/wizards/metrics/stage2/PerformanceGraphWidget/composables/usePerformanceGraph'
import { useProvideDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'

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
  widgets: Object.fromEntries(
    [
      'single_timeseries',
      'performance_graph',
      'combined_graph',
      'custom_graph',
      'problem_graph'
    ].map((type) => [type, WIDGET_CONSTANTS])
  )
}

const SEPARATE_TIMERANGE = { type: 'predefined', value: 'last_25_hours' } as const

interface GraphHandler extends Pick<UseWidgetHandler, 'getSubmitProps'> {
  followDashboardTimeRange: Ref<boolean>
}

const WIZARDS: {
  widget: string
  content: Record<string, unknown>
  open: (spec: WidgetSpec | null) => Promise<GraphHandler>
}[] = [
  {
    widget: 'graph',
    content: { type: 'single_timeseries', metric: 'util', color: 'default_metric' },
    open: (spec) => useGraph('util', {}, spec)
  },
  {
    widget: 'performance graph',
    content: { type: 'performance_graph', source: 'cpu_utilization' },
    open: (spec) => usePerformanceGraph('cpu_utilization', {}, spec)
  },
  {
    widget: 'combined graph',
    content: { type: 'combined_graph', graph_template: 'cpu', presentation: 'lines' },
    open: (spec) => useCombinedGraph('cpu', {}, spec)
  },
  {
    widget: 'custom graph',
    content: { type: 'custom_graph', custom_graph: 'my_graph' },
    open: (spec) => useCustomGraph({}, spec)
  },
  {
    widget: 'percentage of service problems',
    content: { type: 'problem_graph' },
    open: (spec) => usePercentageOfServiceProblems({}, spec)
  }
]

useMswServer(
  http.post(`${API}/compute-widget-titles/invoke`, () =>
    HttpResponse.json({ extensions: { titles: { preview_widget: 'Graph' } } })
  ),
  http.post(`${API}/compute-widget-attributes/invoke`, () =>
    HttpResponse.json({ value: { filter_context: { uses_infos: [] } } })
  )
)

async function openWizard(
  open: (spec: WidgetSpec | null) => Promise<GraphHandler>,
  content: WidgetSpec['content'] | null
): Promise<GraphHandler> {
  const currentSpec: WidgetSpec | null = content && {
    content,
    filter_context: { filters: {}, uses_infos: [] },
    general_settings: {
      title: { text: 'Graph', render_mode: 'with_background' },
      render_background: true
    }
  }
  let handler: Promise<GraphHandler> | undefined
  const consumer = defineComponent({
    setup() {
      handler = open(currentSpec)
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

async function submittedTimerange(handler: GraphHandler): Promise<unknown> {
  const { content } = await handler.getSubmitProps()
  if (!('timerange' in content)) {
    throw new Error(`The wizard submitted a ${content.type} widget without a timerange.`)
  }
  return content.timerange
}

describe.each(WIZARDS)('the $widget wizard', ({ content, open }) => {
  const stored = (timerange: unknown) => ({ ...content, timerange }) as WidgetSpec['content']

  it('follows the dashboard time range for a new widget', async () => {
    const handler = await openWizard(open, null)

    expect(await submittedTimerange(handler)).toBe('dashboard')
  })

  it('keeps following the dashboard for a widget stored that way', async () => {
    const handler = await openWizard(open, stored('dashboard'))

    expect(await submittedTimerange(handler)).toBe('dashboard')
  })

  it('keeps the stored separate time range of an edited widget', async () => {
    const handler = await openWizard(open, stored(SEPARATE_TIMERANGE))

    expect(await submittedTimerange(handler)).toEqual(SEPARATE_TIMERANGE)
  })

  it('submits a separate time range once the widget stops following the dashboard', async () => {
    const handler = await openWizard(open, null)
    handler.followDashboardTimeRange.value = false

    expect(await submittedTimerange(handler)).not.toBe('dashboard')
  })
})
