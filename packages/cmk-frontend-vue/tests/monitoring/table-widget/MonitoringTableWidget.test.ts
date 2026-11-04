/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import { render } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import { type Component, type PropType, defineComponent, h } from 'vue'

import { MODE_COLUMN_ID, MODE_COLUMN_MAX_WIDTH } from '@/monitoring/shared/components/modeColumn'
import { columnId } from '@/monitoring/shared/tableState/schema'
import { DEFAULT_DISPLAY_OPTIONS } from '@/monitoring/shared/types'
import MonitoringTableWidget from '@/monitoring/table-widget/MonitoringTableWidget.vue'
import { WidgetTableState } from '@/monitoring/table-widget/WidgetTableState'
import { HostsTableDescriptor } from '@/monitoring/table-widget/tableDescriptors'

// The generic widget can't infer its row type through h(); the props below are the hosts'.
const widget: Component = MonitoringTableWidget

/** The columns the hosts widget hands to its table. */
function tableColumns(columnIds: string[]): ColumnDef<unknown>[] {
  const seen: ColumnDef<unknown>[][] = []
  const tableStub = defineComponent({
    props: { columns: { type: Array as PropType<ColumnDef<unknown>[]>, required: true } },
    setup: (props) => {
      seen.push(props.columns)
      return () => null
    }
  })
  render(
    defineComponent({
      setup: () => () =>
        h(widget, {
          descriptor: new HostsTableDescriptor(),
          columnIds,
          rows: [],
          tableState: new WidgetTableState([]),
          displayOptions: DEFAULT_DISPLAY_OPTIONS
        })
    }),
    { global: { stubs: { MonitoringTable: tableStub } } }
  )
  return seen.at(-1) ?? []
}

describe('MonitoringTableWidget', () => {
  it('caps the mode column like the full pages', () => {
    const modes = tableColumns(['name', MODE_COLUMN_ID]).find(
      (column) => columnId(column) === MODE_COLUMN_ID
    )

    expect(modes?.maxSize).toBe(MODE_COLUMN_MAX_WIDTH)
  })
})
