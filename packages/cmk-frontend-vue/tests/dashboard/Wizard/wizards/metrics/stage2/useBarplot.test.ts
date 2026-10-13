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

import type { BarplotContent } from '@/dashboard/components/Wizard/types'
import {
  type UseBarplot,
  useBarplot
} from '@/dashboard/components/Wizard/wizards/metrics/stage2/BarplotWidget/composables/useBarplot'
import { useProvideDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'

const API = `${location.protocol}//${location.host}/api/internal/domain-types/dashboard/actions`

const CONSTANTS: DashboardConstants = {
  responsive_grid_breakpoints: {},
  widgets: {
    barplot: {
      filter_context: { restricted_to_single: ['service'] },
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
      contextual_link: {
        modes: ['default', 'inherited', 'custom'],
        filters: ['siteopt', 'host', 'service', 'hoststate', 'svcstate'],
        single_infos: ['host', 'service']
      }
    }
  }
}

const CUSTOM: BarplotContent['contextual_link'] = {
  type: 'custom',
  links: [
    {
      title: 'Problems',
      location: { type: 'views', name: 'allservices', owner: null },
      filters: [{ filter_id: 'host' }, { filter_id: 'svcstate' }],
      include_context: false,
      include_time_range: false,
      show_filter_form: true
    }
  ]
}

useMswServer(
  http.post(`${API}/compute-widget-titles/invoke`, () =>
    HttpResponse.json({ extensions: { titles: { preview_widget: 'Bar chart' } } })
  ),
  http.post(`${API}/compute-widget-attributes/invoke`, () =>
    HttpResponse.json({ value: { filter_context: { uses_infos: [] } } })
  )
)

async function openBarplot(currentSpec: WidgetSpec | null = null): Promise<UseBarplot> {
  let handler: Promise<UseBarplot> | undefined
  const consumer = defineComponent({
    setup() {
      handler = useBarplot('util', {}, currentSpec)
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

async function submittedLink(handler: UseBarplot): Promise<BarplotContent['contextual_link']> {
  const { content } = await handler.getSubmitProps()
  if (content.type !== 'barplot') {
    throw new Error(`The wizard submitted a ${content.type} widget.`)
  }
  return content.contextual_link
}

describe('useBarplot', () => {
  it('submits the default link for a new widget', async () => {
    const handler = await openBarplot()

    expect(await submittedLink(handler)).toEqual({ type: 'default' })
  })

  it('keeps the stored custom link of an edited widget', async () => {
    const handler = await openBarplot({
      content: {
        type: 'barplot',
        metric: 'util',
        display_range: 'automatic',
        contextual_link: CUSTOM
      },
      filter_context: { filters: {}, uses_infos: [] },
      general_settings: {
        title: { text: 'Bar chart', render_mode: 'with_background' },
        render_background: true
      }
    })

    expect(await submittedLink(handler)).toEqual(CUSTOM)
  })
})
