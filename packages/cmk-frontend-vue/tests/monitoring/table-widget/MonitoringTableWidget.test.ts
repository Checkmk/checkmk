/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, it, vi } from 'vitest'
import { type Component, type PropType, defineComponent, h } from 'vue'

import type { HostEntry, HostRef, ServiceEntry } from '@/monitoring/shared/api/types'
import type { ActionRun } from '@/monitoring/shared/components/action/run'
import type { ActionOutcome } from '@/monitoring/shared/components/action/types'
import {
  INDICATOR_COLUMN_ID,
  INDICATOR_COLUMN_MAX_WIDTH
} from '@/monitoring/shared/components/indicatorColumn'
import { useActionFeedbackStack } from '@/monitoring/shared/services/useActionFeedbackStack'
import { columnId } from '@/monitoring/shared/tableState/schema'
import { DEFAULT_DISPLAY_OPTIONS } from '@/monitoring/shared/types'
import MonitoringTableWidget from '@/monitoring/table-widget/MonitoringTableWidget.vue'
import { WidgetTableState } from '@/monitoring/table-widget/WidgetTableState'
import {
  HostsTableDescriptor,
  type MonitoringTableActionOffer,
  MonitoringTableDescriptor,
  type MonitoringTableRowActions,
  ServicesTableDescriptor
} from '@/monitoring/table-widget/tableDescriptors'

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

const SERVICE = { name: 'CPU load', host_name: 'web-1', site_id: 'local' } as ServiceEntry

const serviceRowStub = defineComponent({
  props: { row: { type: Object as PropType<ServiceEntry>, required: true } },
  emits: ['open', 'openHost'],
  setup:
    (props, { emit }) =>
    () =>
      h('div', [
        h('button', { onClick: () => emit('open', props.row) }, props.row.name),
        h(
          'button',
          {
            onClick: () =>
              emit('openHost', { name: props.row.host_name, site_id: props.row.site_id })
          },
          props.row.host_name
        )
      ])
})

const hostSlideInStub = defineComponent({
  props: { host: { type: Object as PropType<HostRef | null>, default: null } },
  setup: (props) => () => (props.host ? h('aside', `Details of host ${props.host.name}`) : null)
})

const serviceSlideInStub = defineComponent({
  props: { service: { type: Object as PropType<ServiceEntry | null>, default: null } },
  setup: (props) => () =>
    props.service ? h('aside', `Details of service ${props.service.name}`) : null
})

function renderWidget(
  descriptor: MonitoringTableDescriptor<HostEntry> | MonitoringTableDescriptor<ServiceEntry>,
  rows: unknown[],
  readOnly: boolean
): boolean[] {
  const readOnlySeen: boolean[] = []
  render(
    defineComponent({
      setup: () => () =>
        h(widget, {
          descriptor,
          columnIds: ['name'],
          rows,
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
          HostServicesRow: serviceRowStub,
          HostSlideIn: hostSlideInStub,
          ServiceSlideIn: serviceSlideInStub
        }
      }
    }
  )
  return readOnlySeen
}

const RAN: ActionOutcome = { variant: 'success', message: untranslated('The check has run') }
const GAVE_UP: ActionOutcome = { variant: 'warning', message: untranslated('Stopped waiting') }

const commandRowStub = defineComponent({
  props: { row: { type: Object as PropType<HostEntry>, required: true } },
  emits: ['command'],
  setup:
    (props, { emit }) =>
    () =>
      h(
        'button',
        { onClick: () => emit('command', { id: 'reschedule', target: props.row }) },
        `Reschedule ${props.row.name}`
      )
})

/** A table of hosts whose rows run `run`, whatever command is picked. */
class CommandTableDescriptor extends MonitoringTableDescriptor<HostEntry, HostEntry> {
  readonly rowComponent: Component = commandRowStub
  readonly detailsComponent: Component = defineComponent({ render: () => null })
  readonly columnIds = ['name']

  constructor(private readonly run: ActionRun) {
    super()
  }

  protected allColumns(): ColumnDef<HostEntry>[] {
    return [{ id: 'name' }]
  }

  rowKey(row: HostEntry): string {
    return row.name
  }

  truncatedHint(): string {
    return ''
  }

  rowActions(): MonitoringTableRowActions<HostEntry, HostEntry> {
    return { rowProps: () => ({}), resolve: () => this.run }
  }

  rowListeners(): object {
    return {}
  }
}

/** A widget whose host row runs `run` once clicked, telling how it goes in `stack`. */
function renderCommandWidget(
  run: ActionRun,
  stack: ReturnType<typeof useActionFeedbackStack>
): { performed: ReturnType<typeof vi.fn>; unmount: () => void } {
  const performed = vi.fn()
  const { unmount } = render(
    defineComponent({
      setup: () => () =>
        h(widget, {
          descriptor: new CommandTableDescriptor(run),
          columnIds: ['name'],
          rows: [HOST],
          tableState: new WidgetTableState([]),
          displayOptions: DEFAULT_DISPLAY_OPTIONS,
          actions: { offer: {} as MonitoringTableActionOffer, feedback: stack },
          readOnly: false,
          onPerformed: performed
        })
    }),
    {
      global: { stubs: { MonitoringTable: rowsStub } }
    }
  )
  return { performed, unmount }
}

describe('MonitoringTableWidget', () => {
  it('caps the Indicator column like the full pages', () => {
    const indicator = tableColumns(['name', INDICATOR_COLUMN_ID]).find(
      (column) => columnId(column) === INDICATOR_COLUMN_ID
    )

    expect(indicator?.maxSize).toBe(INDICATOR_COLUMN_MAX_WIDTH)
  })

  it('opens the details of the host whose name is clicked', async () => {
    renderWidget(new HostsTableDescriptor(), [HOST], false)

    await userEvent.click(screen.getByRole('button', { name: 'web-1' }))

    expect(screen.getByText('Details of host web-1')).toBeInTheDocument()
  })

  it('passes read-only on to its rows', () => {
    const readOnlySeen = renderWidget(new HostsTableDescriptor(), [HOST], true)

    expect(readOnlySeen.at(-1)).toBe(true)
  })

  it('opens the details of the service whose name is clicked', async () => {
    renderWidget(new ServicesTableDescriptor(), [SERVICE], false)

    await userEvent.click(screen.getByRole('button', { name: 'CPU load' }))

    expect(screen.getByText('Details of service CPU load')).toBeInTheDocument()
  })

  it('opens the details of the host a service row names', async () => {
    renderWidget(new ServicesTableDescriptor(), [SERVICE], false)

    await userEvent.click(screen.getByRole('button', { name: 'web-1' }))

    expect(screen.getByText('Details of host web-1')).toBeInTheDocument()
    expect(screen.queryByText('Details of service CPU load')).not.toBeInTheDocument()
  })

  it('tells the page around that the command picked in a row runs', async () => {
    const stack = useActionFeedbackStack()
    renderCommandWidget(
      { pending: untranslated('Waiting'), perform: () => new Promise<ActionOutcome>(() => {}) },
      stack
    )

    await userEvent.click(screen.getByRole('button', { name: 'Reschedule web-1' }))

    expect(stack.items.value.map((item) => item.feedback)).toEqual([
      { variant: 'loading', message: untranslated('Waiting') }
    ])
  })

  it('tells the page around how the command picked in a row went', async () => {
    const stack = useActionFeedbackStack()
    renderCommandWidget(
      { pending: untranslated('Waiting'), perform: () => Promise.resolve(RAN) },
      stack
    )

    await userEvent.click(screen.getByRole('button', { name: 'Reschedule web-1' }))

    await vi.waitFor(() => expect(stack.items.value.map((item) => item.feedback)).toEqual([RAN]))
  })

  it('runs a command picked again on the same object while it runs only once', async () => {
    const stack = useActionFeedbackStack()
    const perform = vi.fn(() => new Promise<ActionOutcome>(() => {}))
    renderCommandWidget(
      { pending: untranslated('Waiting'), perform, key: 'reschedule@local/web-1' },
      stack
    )
    const reschedule = screen.getByRole('button', { name: 'Reschedule web-1' })
    await userEvent.click(reschedule)

    await userEvent.click(reschedule)

    expect(perform).toHaveBeenCalledTimes(1)
    expect(stack.items.value).toHaveLength(1)
  })

  it('waits for the command picked in a row for as long as the page around is there', async () => {
    const stack = useActionFeedbackStack()
    let settle: (outcome: ActionOutcome) => void = () => {}
    const { unmount } = renderCommandWidget(
      {
        pending: untranslated('Waiting'),
        perform: (signal) =>
          new Promise((resolve) => {
            settle = resolve
            signal?.addEventListener('abort', () => resolve(GAVE_UP))
          })
      },
      stack
    )
    await userEvent.click(screen.getByRole('button', { name: 'Reschedule web-1' }))

    unmount()
    settle(RAN)

    await vi.waitFor(() => expect(stack.items.value.map((item) => item.feedback)).toEqual([RAN]))
  })

  it('hands on how the command picked in a row went', async () => {
    const { performed } = renderCommandWidget(
      { pending: untranslated('Waiting'), perform: () => Promise.resolve(RAN) },
      useActionFeedbackStack()
    )

    await userEvent.click(screen.getByRole('button', { name: 'Reschedule web-1' }))

    await vi.waitFor(() => expect(performed).toHaveBeenCalledWith(RAN))
  })
})
