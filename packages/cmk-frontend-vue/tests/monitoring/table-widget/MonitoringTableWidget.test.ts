/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import { type Component, type PropType, defineComponent, h } from 'vue'

import type { HostEntry } from '@/monitoring/shared/api/types'
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
          displayOptions: DEFAULT_DISPLAY_OPTIONS,
          readOnly: true
        })
    }),
    { global: { stubs: { MonitoringTable: tableStub } } }
  )
  return seen.at(-1) ?? []
}

const HOST = { name: 'web-1', site_id: 'local', state: 'UP' } as HostEntry

const rowsStub = defineComponent({
  inheritAttrs: false,
  props: { rows: { type: Array as PropType<unknown[]>, required: true } },
  setup:
    (props, { slots }) =>
    () =>
      h(
        'div',
        props.rows.map((row) => slots['row']?.({ row, tableRow: {} }))
      )
})

function hostRowStub(readOnlySeen: boolean[]) {
  return defineComponent({
    props: { row: { type: Object as PropType<HostEntry>, required: true }, readOnly: Boolean },
    emits: ['open'],
    setup:
      (props, { emit }) =>
      () => {
        readOnlySeen.push(props.readOnly)
        return h('button', { onClick: () => emit('open', props.row) }, props.row.name)
      }
  })
}

const hostSlideInStub = defineComponent({
  props: { host: { type: Object as PropType<HostEntry | null>, default: null } },
  setup: (props) => () => (props.host ? h('aside', `Details of ${props.host.name}`) : null)
})

function renderHosts(readOnly: boolean): boolean[] {
  const readOnlySeen: boolean[] = []
  render(
    defineComponent({
      setup: () => () =>
        h(widget, {
          descriptor: new HostsTableDescriptor(),
          columnIds: ['name'],
          rows: [HOST],
          tableState: new WidgetTableState([]),
          displayOptions: DEFAULT_DISPLAY_OPTIONS,
          readOnly
        })
    }),
    {
      global: {
        stubs: {
          MonitoringTable: rowsStub,
          HostRow: hostRowStub(readOnlySeen),
          HostSlideIn: hostSlideInStub
        }
      }
    }
  )
  return readOnlySeen
}

describe('MonitoringTableWidget', () => {
  it('caps the mode column like the full pages', () => {
    const modes = tableColumns(['name', MODE_COLUMN_ID]).find(
      (column) => columnId(column) === MODE_COLUMN_ID
    )

    expect(modes?.maxSize).toBe(MODE_COLUMN_MAX_WIDTH)
  })

  it('opens the details of the host whose name is clicked', async () => {
    renderHosts(false)

    await userEvent.click(screen.getByRole('button', { name: 'web-1' }))

    expect(screen.getByText('Details of web-1')).toBeInTheDocument()
  })

  it('passes read-only on to its rows', () => {
    const readOnlySeen = renderHosts(true)

    expect(readOnlySeen.at(-1)).toBe(true)
  })
})
