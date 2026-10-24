/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
// eslint-disable-next-line no-restricted-imports -- pre-existing violation: type these handlers, never copy this line
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'

import { useWidgetVisualizationProps } from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import Stage3 from '@/dashboard/components/Wizard/wizards/monitoring-table/stage3/StageContents.vue'
import { useProvideDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetGeneralSettings } from '@/dashboard/types/widget'

const API = `${location.protocol}//${location.host}/api/internal/domain-types/dashboard/actions`

const CONSTANTS: DashboardConstants = {
  responsive_grid_breakpoints: {},
  widgets: {
    monitoring_table: {
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

useMswServer(
  http.post(`${API}/compute-widget-titles/invoke`, () =>
    HttpResponse.json({ extensions: { titles: { preview_widget: 'Monitoring table' } } })
  )
)

function renderStage3(currentSettings?: WidgetGeneralSettings) {
  const saved: WidgetGeneralSettings[] = []
  const stage = defineComponent({
    setup() {
      const visualization = useWidgetVisualizationProps(
        '$DEFAULT_TITLE$',
        currentSettings,
        'monitoring_table'
      )
      return () =>
        h(Stage3, {
          visualization,
          tick: 0,
          range: { start: new Date(0), end: new Date(0) } as never,
          dashboardKey: { name: 'main', owner: '' },
          content: {
            type: 'monitoring_table',
            table: 'hosts',
            columns: ['state', 'name'],
            sort: [],
            limit: 1000,
            date_format: '%Y-%m-%d',
            timestamp_format: 'mixed'
          },
          effectiveFilterContext: { uses_infos: ['host'], filters: {}, restricted_to_single: [] },
          isEditMode: currentSettings !== undefined,
          onAddWidget: (settings: WidgetGeneralSettings) => saved.push(settings)
        })
    }
  })
  render(
    defineComponent({
      setup() {
        useProvideDashboardConstants(CONSTANTS)
        return () => h(stage)
      }
    }),
    { global: { stubs: { DashboardPreviewContent: true } } }
  )
  return saved
}

describe('monitoring table visualization', () => {
  it('places the widget without a title when the title is hidden', async () => {
    const user = userEvent.setup()
    const saved = renderStage3()

    await user.click(screen.getByRole('checkbox', { name: 'Show title' }))
    await user.click(screen.getByRole('button', { name: 'Add & place widget' }))

    expect(saved).toEqual([
      {
        title: { text: '$DEFAULT_TITLE$', render_mode: 'hidden' },
        render_background: true
      }
    ])
  })

  it('keeps the title settings of the widget being edited', async () => {
    const user = userEvent.setup()
    const current: WidgetGeneralSettings = {
      title: { text: 'Linux hosts', render_mode: 'without_background', url: 'https://x.test' },
      render_background: false
    }
    const saved = renderStage3(current)

    await user.click(screen.getByRole('button', { name: 'Save widget' }))

    expect(saved).toEqual([current])
  })
})
