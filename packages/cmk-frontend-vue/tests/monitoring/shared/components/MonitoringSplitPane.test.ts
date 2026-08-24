/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef, Row as TableRow } from '@tanstack/vue-table'
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, markRaw, provide } from 'vue'

import type { HostRef } from '@/monitoring/shared/api/types'
import MonitoringSplitPane from '@/monitoring/shared/components/MonitoringSplitPane.vue'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import type { ActionFeedback } from '@/monitoring/shared/components/action/ActionFeedback.vue'
import type { MonitoringActionRegistry } from '@/monitoring/shared/components/action/registry'
import type { MonitoringAction } from '@/monitoring/shared/components/action/types'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'
import {
  MonitoringService,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'

import { makeKeyShortcutService } from '../services/testHelpers'

const RUNNING_CLASS = 'cmk-button--running'
const RESCHEDULE_ID = 'reschedule'
const ACK_ID = 'acknowledge'
const RESCHEDULE_LABEL = 'Reschedule check'
const ACK_LABEL = 'Acknowledge'

interface Row {
  site_id: string
  name: string
}

const ROW: Row = { site_id: 'local', name: 'host-1' }

const COLUMNS: ColumnDef<Row>[] = [
  { id: 'select', header: '', enableSorting: false, meta: { selectColumn: true } },
  { accessorKey: 'name', header: 'Name' }
]

const BULK_ACTIONS: CellAction[] = [
  { id: RESCHEDULE_ID, label: untranslated(RESCHEDULE_LABEL), icon: 'reload' },
  { id: ACK_ID, label: untranslated(ACK_LABEL), icon: 'ack' }
]

const STUB_FORM = markRaw(
  defineComponent({
    props: { modelValue: { type: Object, default: () => ({}) } },
    emits: ['update:modelValue', 'update:valid'],
    setup: () => () => h('div')
  })
)

class RowService extends MonitoringService<Row> {
  protected async fetchBatch(): Promise<PagedResponse<Row>> {
    return { items: [ROW], meta: { limit: 1000, matched: 1, total: 1 } }
  }
}

function makeAction(id: string, perform: MonitoringAction['perform']): MonitoringAction {
  return {
    id,
    title: untranslated(id),
    submitLabel: untranslated('Submit'),
    form: STUB_FORM,
    defaultValues: () => ({}),
    perform
  }
}

let service: RowService | null = null

async function mountPaneWithLoadedRows(perform: MonitoringAction['perform']) {
  service = new RowService('row-service', makeKeyShortcutService(), { columns: COLUMNS })
  const actions: MonitoringActionRegistry = {
    [RESCHEDULE_ID]: makeAction(RESCHEDULE_ID, perform),
    [ACK_ID]: makeAction(ACK_ID, perform)
  }
  const activeService = service
  await vi.waitUntil(() => activeService.hasLoaded.value)

  return render(
    defineComponent({
      setup() {
        provide(MONITORING_SERVICE, activeService as MonitoringService<unknown>)
        return () =>
          h(
            MonitoringSplitPane<Row, HostRef>,
            {
              service: activeService,
              actions,
              bulkActions: BULK_ACTIONS,
              immediateActionIds: [RESCHEDULE_ID],
              columns: COLUMNS,
              columnPinning: {},
              getRowKey: (row: Row) => `${row.site_id}/${row.name}`,
              getActionTarget: (row: Row) => ({ site_id: row.site_id, name: row.name }),
              selectionLabel: (count: number) =>
                `${count} hosts selected` as unknown as TranslatedString,
              actionsLabel: untranslated('Actions for selected hosts'),
              countsLabel: (selected: number, total: number) =>
                `Selected hosts: ${selected} | Total hosts: ${total}` as unknown as TranslatedString
            },
            {
              row: ({ tableRow }: { tableRow: TableRow<Row> }) => [
                h('td', [
                  h('input', {
                    type: 'checkbox',
                    'aria-label': 'Select row',
                    onChange: () => tableRow.toggleSelected()
                  })
                ]),
                h('td', ROW.name)
              ]
            }
          )
      }
    })
  )
}

async function selectTheOnlyRow(): Promise<void> {
  await userEvent.click(await screen.findByRole('checkbox', { name: 'Select all rows' }))
}

describe('MonitoringSplitPane', () => {
  afterEach(() => {
    service?.stopPolling()
    service = null
  })

  it('performs an immediate action on the selected row without opening the form', async () => {
    const perform = vi
      .fn()
      .mockResolvedValue({ variant: 'success', message: untranslated('Rescheduled') })
    await mountPaneWithLoadedRows(perform)
    await selectTheOnlyRow()

    await userEvent.click(screen.getByRole('button', { name: RESCHEDULE_LABEL }))

    expect(perform).toHaveBeenCalledWith([{ site_id: 'local', name: 'host-1' }], {})
    expect(screen.queryByRole('button', { name: 'Submit' })).not.toBeInTheDocument()
  })

  it('opens the form instead of performing for an action that is not immediate', async () => {
    const perform = vi.fn()
    await mountPaneWithLoadedRows(perform)
    await selectTheOnlyRow()

    await userEvent.click(screen.getByRole('button', { name: ACK_LABEL }))

    expect(perform).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Submit' })).toBeInTheDocument()
  })

  it('pulses the immediate action while it is in flight', async () => {
    let settle: () => void = () => {}
    const pending = new Promise<ActionFeedback>((resolve) => {
      settle = () => resolve({ variant: 'success', message: untranslated('Rescheduled') })
    })
    await mountPaneWithLoadedRows(vi.fn().mockReturnValue(pending))
    await selectTheOnlyRow()

    await userEvent.click(screen.getByRole('button', { name: RESCHEDULE_LABEL }))

    expect(screen.getByRole('button', { name: RESCHEDULE_LABEL })).toHaveClass(RUNNING_CLASS)

    settle()
    await pending
  })

  it('stops pulsing once an immediate action reports an error', async () => {
    const perform = vi
      .fn()
      .mockResolvedValue({ variant: 'error', message: untranslated('Could not reschedule') })
    await mountPaneWithLoadedRows(perform)
    await selectTheOnlyRow()

    await userEvent.click(screen.getByRole('button', { name: RESCHEDULE_LABEL }))

    expect(await screen.findByText('Could not reschedule')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: RESCHEDULE_LABEL })).not.toHaveClass(RUNNING_CLASS)
  })

  it('selects every row when the select-all cell is clicked next to its checkbox', async () => {
    await mountPaneWithLoadedRows(vi.fn())
    await screen.findByRole('checkbox', { name: 'Select all rows' })

    await userEvent.click(document.querySelector('.monitoring-table-header__select')!)

    expect(await screen.findByText('1 hosts selected')).toBeInTheDocument()
  })

  it('ignores a bulk action while nothing is selected', async () => {
    const perform = vi.fn()
    await mountPaneWithLoadedRows(perform)
    await screen.findByRole('checkbox', { name: 'Select all rows' })

    await userEvent.click(screen.getByRole('button', { name: RESCHEDULE_LABEL }))

    expect(perform).not.toHaveBeenCalled()
  })
})
