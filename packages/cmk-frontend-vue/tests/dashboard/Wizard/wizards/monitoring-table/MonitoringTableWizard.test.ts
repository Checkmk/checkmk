/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import {
  type FilterDefinition,
  useProvideFilterDefinitions
} from 'cmk-ui-library/components/filter'
import { describe, expect, it } from 'vitest'
import { defineComponent, h, provide, ref } from 'vue'

import MonitoringTableWizard from '@/dashboard/components/Wizard/wizards/monitoring-table/MonitoringTableWizard.vue'
import { useProvideDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import { visualInfosByIdKey } from '@/dashboard/composables/useProvideVisualInfos'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard/types/widget'

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

type Saved = [WidgetContent, WidgetGeneralSettings, WidgetFilterContext]

const EDITED: WidgetSpec = {
  content: {
    type: 'monitoring_table',
    table: 'hosts',
    columns: ['state', 'name', 'labels'],
    sort: ['name:desc'],
    limit: 250,
    date_format: '%d.%m.%Y',
    timestamp_format: 'abs'
  },
  general_settings: {
    title: { text: 'Linux hosts', render_mode: 'with_background' },
    render_background: true
  },
  filter_context: { uses_infos: ['host'], filters: { hostregex: { host_regex: 'linux' } } }
} as WidgetSpec

function renderWizard(editWidgetSpec: WidgetSpec | null) {
  const saved: Saved[] = []
  render(
    defineComponent({
      setup() {
        useProvideDashboardConstants(CONSTANTS)
        useProvideFilterDefinitions({
          definitions: { hostregex: { extensions: { info: 'host' } } as FilterDefinition },
          groups: {}
        })
        provide(visualInfosByIdKey, ref({ host: { title: 'Host' } }) as never)
        return () =>
          h(MonitoringTableWizard, {
            tick: 0,
            range: { start: new Date(0), end: new Date(0) } as never,
            dashboardKey: { name: 'main', owner: '' },
            contextFilters: {},
            editWidgetSpec,
            onAddWidget: (...args: Saved) => saved.push(args)
          })
      }
    }),
    { global: { stubs: { WidgetObjectFilterConfiguration: true, FiltersRecap: true } } }
  )
  return saved
}

async function stepThrough(saveLabel: string) {
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: /Next step: Data configuration/ }))
  await user.click(await screen.findByRole('button', { name: /Next step: Visualization/ }))
  await user.click(await screen.findByRole('button', { name: saveLabel }))
}

describe('monitoring table wizard', () => {
  it('saves an edited widget with its data and filters unchanged', async () => {
    const saved = renderWizard(EDITED)

    await stepThrough('Save widget')

    expect(saved.map(([content, , filterContext]) => [content, filterContext])).toEqual([
      [EDITED.content, EDITED.filter_context]
    ])
  })

  it('saves a new widget with the defaults of the chosen view', async () => {
    const user = userEvent.setup()
    const saved = renderWizard(null)

    await user.click(screen.getByRole('combobox', { name: 'View' }))
    await user.click(await screen.findByText('All hosts'))
    await stepThrough('Add & place widget')

    expect(saved.map(([content, , filterContext]) => [content.type, filterContext])).toEqual([
      ['monitoring_table', { uses_infos: ['host'], filters: {} }]
    ])
  })
})
