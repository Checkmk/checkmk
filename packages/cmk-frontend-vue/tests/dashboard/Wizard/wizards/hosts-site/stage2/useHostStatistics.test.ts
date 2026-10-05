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

import type { HostStatisticsContent } from '@/dashboard/components/Wizard/types'
import {
  type UseHostStatistics,
  useHostStatistics
} from '@/dashboard/components/Wizard/wizards/hosts-site/stage2/HostStatistics/composables/useHostStatistics'
import { useProvideDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'

const API = `${location.protocol}//${location.host}/api/internal/domain-types/dashboard/actions`

const CONSTANTS: DashboardConstants = {
  responsive_grid_breakpoints: {},
  widgets: {
    host_stats: {
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
      contextual_link: {
        modes: ['default', 'inherited', 'custom'],
        filters: ['siteopt', 'wato_folder', 'hoststate', 'opthostgroup'],
        single_infos: []
      }
    }
  }
}

const CUSTOM: HostStatisticsContent['contextual_link'] = {
  type: 'custom',
  links: [
    {
      title: 'Problems',
      location: { type: 'views', name: 'searchhost', owner: 'harry' },
      filters: [{ filter_id: 'siteopt' }, { filter_id: 'hoststate' }],
      include_context: false,
      include_time_range: true,
      show_filter_form: true
    }
  ]
}

const server = setupServer(
  http.post(`${API}/compute-widget-titles/invoke`, () =>
    HttpResponse.json({ extensions: { titles: { preview_widget: 'Host statistics' } } })
  ),
  http.post(`${API}/compute-widget-attributes/invoke`, () =>
    HttpResponse.json({ value: { filter_context: { uses_infos: [] } } })
  )
)

async function openHostStatistics(currentSpec: WidgetSpec): Promise<UseHostStatistics> {
  let handler: Promise<UseHostStatistics> | undefined
  const consumer = defineComponent({
    setup() {
      handler = useHostStatistics({}, currentSpec)
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

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('useHostStatistics', () => {
  it('keeps the stored custom link of an edited widget', async () => {
    const handler = await openHostStatistics({
      content: { type: 'host_stats', contextual_link: CUSTOM },
      filter_context: { filters: {}, uses_infos: [] },
      general_settings: {
        title: { text: 'Host statistics', render_mode: 'with_background' },
        render_background: true
      }
    })

    const { content } = await handler.getSubmitProps()

    expect(content).toEqual({ type: 'host_stats', contextual_link: CUSTOM })
  })
})
