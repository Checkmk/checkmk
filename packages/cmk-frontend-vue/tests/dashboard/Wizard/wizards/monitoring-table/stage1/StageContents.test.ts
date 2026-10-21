/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { useProvideFilterDefinitions } from 'cmk-ui-library/components/filter'
import { describe, expect, it } from 'vitest'
import { defineComponent, h, provide, ref } from 'vue'

import Stage1 from '@/dashboard/components/Wizard/wizards/monitoring-table/stage1/StageContents.vue'
import { visualInfosByIdKey } from '@/dashboard/composables/useProvideVisualInfos'
import type { MonitoringTableName } from '@/monitoring/table-widget/tableDescriptors'

function renderStage1(initialTable: MonitoringTableName | null = null) {
  const table = ref<MonitoringTableName | null>(initialTable)
  const goNext: string[] = []
  render(
    defineComponent({
      setup() {
        useProvideFilterDefinitions({ definitions: {}, groups: {} })
        provide(
          visualInfosByIdKey,
          ref({ host: { title: 'Host' }, service: { title: 'Service' } }) as never
        )
        return () =>
          h(Stage1, {
            table: table.value,
            'onUpdate:table': (value: MonitoringTableName | null) => (table.value = value),
            widgetConfiguredFilters: {},
            widgetActiveFilters: [],
            contextFilters: {},
            currentFilterSelectionMenuFocus: null,
            onGoNext: () => goNext.push('next')
          })
      }
    }),
    { global: { stubs: { WidgetObjectFilterConfiguration: true } } }
  )
  return { table, goNext }
}

describe('monitoring table data selection', () => {
  it('offers no filters before a view is chosen', () => {
    renderStage1()

    expect(screen.queryByRole('region', { name: 'Host' })).not.toBeInTheDocument()
  })

  it('offers host filters once All hosts is chosen', async () => {
    const user = userEvent.setup()
    const { table } = renderStage1()

    await user.click(screen.getByRole('combobox', { name: 'View' }))
    await user.click(await screen.findByText('All hosts'))

    expect(table.value).toBe('hosts')
    expect(screen.getByRole('region', { name: 'Host' })).toBeInTheDocument()
  })

  it('offers only host filters for All hosts', () => {
    renderStage1('hosts')

    expect(screen.getByRole('region', { name: 'Host' })).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Service' })).not.toBeInTheDocument()
  })

  it('asks for the next stage', async () => {
    const user = userEvent.setup()
    const { goNext } = renderStage1('hosts')

    await user.click(screen.getByRole('button', { name: /Next step: Data configuration/ }))

    expect(goNext).toEqual(['next'])
  })
})
