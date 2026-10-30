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
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, markRaw, provide } from 'vue'

import type { HostRef } from '@/monitoring/shared/api/types'
import MonitoringSplitPane from '@/monitoring/shared/components/MonitoringSplitPane.vue'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import type { MonitoringActionRegistry } from '@/monitoring/shared/components/action/registry'
import type { RowCommand } from '@/monitoring/shared/components/action/rowCommand'
import type { ActionOutcome, MonitoringAction } from '@/monitoring/shared/components/action/types'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'
import {
  MonitoringService,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'

import { makeKeyShortcutService } from '../services/testHelpers'

// The table renders the rows the virtualizer finds room for, and jsdom lays nothing out.
const originalOffsetHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight')
const originalOffsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth')

beforeAll(() => {
  Object.defineProperty(HTMLElement.prototype, 'offsetHeight', { configurable: true, value: 600 })
  Object.defineProperty(HTMLElement.prototype, 'offsetWidth', { configurable: true, value: 800 })
})

afterAll(() => {
  if (originalOffsetHeight) {
    Object.defineProperty(HTMLElement.prototype, 'offsetHeight', originalOffsetHeight)
  }
  if (originalOffsetWidth) {
    Object.defineProperty(HTMLElement.prototype, 'offsetWidth', originalOffsetWidth)
  }
})

const RUNNING_CLASS = 'cmk-button--running'
const RESCHEDULE_ID = 'reschedule'
const ACK_ID = 'acknowledge'
const COMMENT_ID = 'comment'
const RESCHEDULE_LABEL = 'Reschedule check'
const ACK_LABEL = 'Acknowledge'
const COMMENT_LABEL = 'Add comment'
const ROW_RESCHEDULE_LABEL = 'Reschedule this row'

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
  { id: ACK_ID, label: untranslated(ACK_LABEL), icon: 'ack' },
  { id: COMMENT_ID, label: untranslated(COMMENT_LABEL), icon: 'comment' }
]

const STUB_FORM = markRaw(
  defineComponent({
    props: { modelValue: { type: Object, default: () => ({}) } },
    emits: ['update:modelValue', 'update:valid'],
    setup: (_props, { emit }) => {
      emit('update:valid', true)
      return () => h('div')
    }
  })
)

let unreachableSites: string[] = []

class RowService extends MonitoringService<Row> {
  protected async fetchBatch(): Promise<PagedResponse<Row>> {
    return {
      items: [ROW],
      meta: { limit: 1000, matched: 1, total: 1, unreachable_sites: unreachableSites }
    }
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

async function mountPaneWithLoadedRows(
  perform: MonitoringAction['perform'],
  getActionTargets?: (rows: Row[], actionId: string) => HostRef[],
  ackConfirm?: MonitoringAction['confirm']
) {
  service = new RowService('row-service', makeKeyShortcutService(), { columns: COLUMNS })
  const actions: MonitoringActionRegistry = {
    [RESCHEDULE_ID]: makeAction(RESCHEDULE_ID, perform),
    [ACK_ID]: { ...makeAction(ACK_ID, perform), ...(ackConfirm && { confirm: ackConfirm }) },
    [COMMENT_ID]: makeAction(COMMENT_ID, perform)
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
              getActionTargets,
              selectionLabel: (count: number) =>
                `${count} hosts selected` as unknown as TranslatedString,
              actionsLabel: untranslated('Actions for selected hosts'),
              countsLabel: (selected: number, total: number) =>
                `Selected hosts: ${selected} | Total hosts: ${total}` as unknown as TranslatedString
            },
            {
              row: ({
                tableRow,
                onCommand
              }: {
                tableRow: TableRow<Row>
                onCommand: (command: RowCommand<HostRef>) => void
              }) => [
                h('td', [
                  h('input', {
                    type: 'checkbox',
                    'aria-label': 'Select row',
                    onChange: () => tableRow.toggleSelected()
                  })
                ]),
                h('td', ROW.name),
                h('td', [
                  h(
                    'button',
                    { onClick: () => onCommand({ id: RESCHEDULE_ID, target: ROW }) },
                    ROW_RESCHEDULE_LABEL
                  )
                ])
              ],
              'display-options': () => h('div', 'Display options marker')
            }
          )
      }
    })
  )
}

async function selectTheOnlyRow(): Promise<void> {
  await userEvent.click(await screen.findByRole('checkbox', { name: 'Select all rows' }))
}

/** An outcome that comes only once settled, as a reschedule that waits for its check. */
function pendingOutcome(message: string): { outcome: Promise<ActionOutcome>; settle: () => void } {
  let settle: () => void = () => {}
  const outcome = new Promise<ActionOutcome>((resolve) => {
    settle = () => resolve({ variant: 'success', message: untranslated(message) })
  })
  return { outcome, settle }
}

describe('MonitoringSplitPane', () => {
  afterEach(() => {
    service?.stopPolling()
    service = null
    unreachableSites = []
  })

  it('names the sites that cannot be reached', async () => {
    unreachableSites = ['remote_1', 'remote_2']

    await mountPaneWithLoadedRows(vi.fn())

    expect(screen.getByText('2 sites are not reachable')).toBeInTheDocument()
    expect(
      screen.getByText('No data could be retrieved from sites remote_1, remote_2.')
    ).toBeInTheDocument()
  })

  it('warns about no site while every site answers', async () => {
    await mountPaneWithLoadedRows(vi.fn())

    expect(screen.queryByText(/not reachable/)).not.toBeInTheDocument()
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

  it('performs an immediate action on what the page maps the selection to', async () => {
    const perform = vi
      .fn()
      .mockResolvedValue({ variant: 'success', message: untranslated('Rescheduled') })
    await mountPaneWithLoadedRows(perform, () => [{ site_id: 'local', name: 'other-host' }])
    await selectTheOnlyRow()

    await userEvent.click(screen.getByRole('button', { name: RESCHEDULE_LABEL }))

    expect(perform).toHaveBeenCalledWith([{ site_id: 'local', name: 'other-host' }], {})
  })

  it('refuses an action the selection maps to nothing for', async () => {
    const perform = vi.fn()
    await mountPaneWithLoadedRows(perform, () => [])
    await selectTheOnlyRow()

    await userEvent.click(screen.getByRole('button', { name: ACK_LABEL }))

    expect(perform).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'Submit' })).not.toBeInTheDocument()
    expect(
      await screen.findByText('This action cannot be performed on any of the selected rows.')
    ).toBeInTheDocument()
  })

  it('refuses a confirmed action whose targets are gone by the time it is confirmed', async () => {
    const perform = vi
      .fn()
      .mockResolvedValue({ variant: 'success', message: untranslated('Acknowledged') })
    let targets: HostRef[] = [ROW]
    await mountPaneWithLoadedRows(perform, () => targets, {
      detail: (count) => untranslated(`Targets: ${count}`),
      submitLabel: () => untranslated('Confirm')
    })
    await selectTheOnlyRow()
    await userEvent.click(screen.getByRole('button', { name: ACK_LABEL }))
    targets = []

    await userEvent.click(await screen.findByRole('button', { name: 'Confirm' }))

    expect(perform).not.toHaveBeenCalled()
    expect(
      await screen.findByText('This action cannot be performed on any of the selected rows.')
    ).toBeInTheDocument()
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
    const pending = new Promise<ActionOutcome>((resolve) => {
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

  it('leaves a form opened while an immediate action runs open once it settles', async () => {
    const { outcome, settle } = pendingOutcome('Rescheduled')
    await mountPaneWithLoadedRows(vi.fn().mockReturnValue(outcome))
    await selectTheOnlyRow()
    await userEvent.click(screen.getByRole('button', { name: RESCHEDULE_LABEL }))
    await userEvent.click(screen.getByRole('button', { name: ACK_LABEL }))

    settle()

    expect(await screen.findByText('Rescheduled')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Submit' })).toBeInTheDocument()
  })

  it('leaves a form opened while a row command runs open once it settles', async () => {
    const { outcome, settle } = pendingOutcome('Rescheduled')
    await mountPaneWithLoadedRows(vi.fn().mockReturnValue(outcome))
    await selectTheOnlyRow()
    await userEvent.click(screen.getByRole('button', { name: ROW_RESCHEDULE_LABEL }))
    await userEvent.click(screen.getByRole('button', { name: ACK_LABEL }))

    settle()

    expect(await screen.findByText('Rescheduled')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Submit' })).toBeInTheDocument()
  })

  it('stops waiting for a submitted action once another action is picked', async () => {
    const { outcome, settle } = pendingOutcome('Acknowledged')
    const perform = vi.fn().mockReturnValue(outcome)
    await mountPaneWithLoadedRows(perform)
    await selectTheOnlyRow()
    await userEvent.click(screen.getByRole('button', { name: ACK_LABEL }))
    await userEvent.click(screen.getByRole('button', { name: 'Submit' }))

    await userEvent.click(screen.getByRole('button', { name: COMMENT_LABEL }))

    expect(perform.mock.calls[0]![2]).toHaveProperty('aborted', true)
    expect(screen.getByRole('button', { name: 'Submit' })).not.toHaveClass(RUNNING_CLASS)
    settle()
    await outcome
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

  it('opens the display-options slot when the setup button is clicked', async () => {
    await mountPaneWithLoadedRows(vi.fn())

    await userEvent.click(screen.getByRole('button', { name: 'Modify display options' }))

    expect(screen.getByText('Display options marker')).toBeInTheDocument()
  })

  it('closes the display-options pane when a bulk action is opened', async () => {
    await mountPaneWithLoadedRows(vi.fn())
    await selectTheOnlyRow()
    await userEvent.click(screen.getByRole('button', { name: 'Modify display options' }))
    expect(screen.getByText('Display options marker')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: ACK_LABEL }))

    expect(screen.queryByText('Display options marker')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Submit' })).toBeInTheDocument()
  })

  it('closes the bulk action pane when the setup button is opened', async () => {
    await mountPaneWithLoadedRows(vi.fn())
    await selectTheOnlyRow()
    await userEvent.click(screen.getByRole('button', { name: ACK_LABEL }))
    expect(screen.getByRole('button', { name: 'Submit' })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Modify display options' }))

    expect(screen.queryByRole('button', { name: 'Submit' })).not.toBeInTheDocument()
    expect(screen.getByText('Display options marker')).toBeInTheDocument()
  })
})
