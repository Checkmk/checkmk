/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'

import type { ScatterplotContent } from '@/dashboard/components/Wizard/types'
import {
  type UseScatterplot,
  useScatterplot
} from '@/dashboard/components/Wizard/wizards/metrics/stage2/ScatterplotWidget/composables/useScatterplot'
import { useProvideDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'

const API = `${location.protocol}//${location.host}/api/internal/domain-types/dashboard/actions`

const CONSTANTS: DashboardConstants = {
  responsive_grid_breakpoints: {},
  widgets: {
    average_scatterplot: {
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
      title_macros: [],
      contextual_link: { modes: [], filters: [], filter_keys: {}, single_infos: [] }
    }
  }
}

const STORED: ScatterplotContent = {
  type: 'average_scatterplot',
  metric: 'util',
  time_range: { type: 'predefined', value: 'last_25_hours' },
  metric_color: 'default',
  average_color: 'default',
  median_color: 'default'
}

useMswServer(
  http.post(`${API}/compute-widget-titles/invoke`, () =>
    HttpResponse.json({ extensions: { titles: { preview_widget: 'Scatterplot' } } })
  ),
  http.post(`${API}/compute-widget-attributes/invoke`, () =>
    HttpResponse.json({ value: { filter_context: { uses_infos: [] } } })
  )
)

async function openScatterplot(content: ScatterplotContent | null = null): Promise<UseScatterplot> {
  const currentSpec: WidgetSpec | null = content && {
    content,
    filter_context: { filters: {}, uses_infos: [] },
    general_settings: {
      title: { text: 'Scatterplot', render_mode: 'with_background' },
      render_background: true
    }
  }
  let handler: Promise<UseScatterplot> | undefined
  const consumer = defineComponent({
    setup() {
      handler = useScatterplot('util', {}, currentSpec)
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

async function submittedContent(handler: UseScatterplot): Promise<ScatterplotContent> {
  const { content } = await handler.getSubmitProps()
  if (content.type !== 'average_scatterplot') {
    throw new Error(`The wizard submitted a ${content.type} widget.`)
  }
  return content
}

describe('useScatterplot', () => {
  it('submits a compact legend for a new widget', async () => {
    const content = await submittedContent(await openScatterplot())

    expect(content.show_legend).toBe(true)
    expect(content.legend_style).toBe('compact')
  })

  it('keeps a widget stored before the legend existed without one', async () => {
    const content = await submittedContent(await openScatterplot(STORED))

    expect(content.show_legend).toBe(false)
  })

  it('keeps the stored legend style of an edited widget', async () => {
    const content = await submittedContent(
      await openScatterplot({ ...STORED, show_legend: true, legend_style: 'extended' })
    )

    expect(content.legend_style).toBe('extended')
  })
})
