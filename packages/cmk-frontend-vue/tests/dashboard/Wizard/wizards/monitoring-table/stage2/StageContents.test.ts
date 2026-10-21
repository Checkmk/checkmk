/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { describe, expect, it } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import Stage2 from '@/dashboard/components/Wizard/wizards/monitoring-table/stage2/StageContents.vue'
import type { MonitoringTableContent } from '@/dashboard/types/widget'
import type { MonitoringTableColumn } from '@/monitoring/table-widget/tableDescriptors'

const CATALOG: MonitoringTableColumn[] = [
  { id: 'state', title: 'State', sortable: true, shownByDefault: true },
  { id: 'name', title: 'Host', sortable: true, shownByDefault: true },
  { id: 'last_check', title: 'Check age', sortable: true, shownByDefault: false },
  { id: 'labels', title: 'Labels', sortable: false, shownByDefault: false }
]

function renderStage2(initial: Partial<MonitoringTableContent> = {}) {
  const content = ref<MonitoringTableContent>({
    type: 'monitoring_table',
    table: 'hosts',
    columns: ['state', 'name'],
    sort: [],
    limit: 1000,
    date_format: '%Y-%m-%d',
    timestamp_format: 'mixed',
    ...initial
  })
  const goNext: string[] = []
  render(
    defineComponent({
      setup: () => () =>
        h(Stage2, {
          content: content.value,
          'onUpdate:content': (value: MonitoringTableContent) => (content.value = value),
          viewTitle: 'All hosts' as TranslatedString,
          catalog: CATALOG,
          onGoNext: () => goNext.push('next')
        })
    })
  )
  return { content, goNext }
}

describe('monitoring table data configuration', () => {
  it('sorts by the first displayed sortable column once a sorter is added', async () => {
    const user = userEvent.setup()
    const { content } = renderStage2()

    await user.click(screen.getByRole('button', { name: 'Add sorter' }))

    expect(content.value.sort).toEqual(['state:asc'])
  })

  it('stores the chosen row limit', async () => {
    const user = userEvent.setup()
    const { content } = renderStage2()

    await user.click(screen.getByRole('combobox', { name: 'Row limit' }))
    await user.click(await screen.findByText('5000'))

    expect(content.value.limit).toBe(5000)
  })

  it('refuses to go on with an invalid custom row limit', async () => {
    const user = userEvent.setup()
    const { goNext } = renderStage2()

    await user.click(screen.getByRole('combobox', { name: 'Row limit' }))
    await user.click(await screen.findByText('Custom'))
    await user.clear(screen.getByRole('spinbutton', { name: 'Custom row limit' }))
    await user.type(screen.getByRole('spinbutton', { name: 'Custom row limit' }), '0')
    await user.click(screen.getByRole('button', { name: /Next step: Visualization/ }))

    expect(goNext).toEqual([])
  })

  it.each(['0', ''])('keeps the last valid limit while the custom one is %j', async (typed) => {
    const user = userEvent.setup()
    const { content } = renderStage2({ limit: 250 })

    await user.clear(screen.getByRole('spinbutton', { name: 'Custom row limit' }))
    if (typed) {
      await user.type(screen.getByRole('spinbutton', { name: 'Custom row limit' }), typed)
    }

    expect(content.value.limit).toBe(250)
  })

  it('removes a column together with its sorter', async () => {
    const user = userEvent.setup()
    const { content } = renderStage2({ sort: ['name:desc'] })

    await user.click(screen.getByRole('checkbox', { name: 'Host' }))

    expect([content.value.columns, content.value.sort]).toEqual([['state'], []])
  })

  it('keeps the columns in the order of the catalog', async () => {
    const user = userEvent.setup()
    const { content } = renderStage2({ columns: ['name'] })

    await user.click(screen.getByRole('checkbox', { name: 'State' }))

    expect(content.value.columns).toEqual(['state', 'name'])
  })

  it('offers the timestamp format only with a timestamp column', async () => {
    const user = userEvent.setup()
    const { content } = renderStage2()
    expect(screen.queryByRole('combobox', { name: 'Timestamp format' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('checkbox', { name: 'Check age' }))
    await user.click(screen.getByRole('combobox', { name: 'Timestamp format' }))
    await user.click(await screen.findByText('Absolute'))

    expect(content.value.timestamp_format).toBe('abs')
  })

  it('refuses to go on without any column', async () => {
    const user = userEvent.setup()
    const { goNext } = renderStage2({ columns: [] })

    await user.click(screen.getByRole('button', { name: /Next step: Visualization/ }))

    expect(goNext).toEqual([])
    expect(screen.getByText('Please select at least one column.')).toBeInTheDocument()
  })
})
