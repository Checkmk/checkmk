/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Row } from '@tanstack/vue-table'
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, within } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { renderDateAndTime } from 'cmk-ui-library/lib/renderTime'
import { computed, defineComponent, h, provide } from 'vue'

import HostServicesRow from '@/monitoring/host-services/components/HostServicesRow.vue'
import type { HostRef, HostServiceEntry, ServiceEntry } from '@/monitoring/shared/api/types'
import {
  COLUMN_LAYOUT_KEY,
  type ColumnLayoutInfo,
  MONITORING_SERVICE
} from '@/monitoring/shared/components/MonitoringTableContext'
import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'
import type { DisplayOptions } from '@/monitoring/shared/types'

import { makeListingService } from '../../shared/services/testHelpers'

// 'abs' keeps assertions comparable to plain `renderDateAndTime`, independent of how old
// a fixture's timestamp happens to be relative to the real clock the test runs under.
const DISPLAY_OPTIONS: DisplayOptions = { dateFormat: '%Y-%m-%d', timestampFormat: 'abs' }

const HOST: HostRef = { site_id: 'local', name: 'web-server-01' }

function reschedulesItself(name: string) {
  return {
    label: 'Reschedule check',
    tooltip: 'Reschedule check',
    icon_name: 'reload',
    target: name
  }
}

function makeService(overrides: Partial<HostServiceEntry> = {}): HostServiceEntry {
  return {
    name: 'CPU load',
    state: 'OK',
    is_flapping: false,
    stale: false,
    summary: 'OK - 15 min load: 0.5',
    last_check: 1783942710,
    last_state_change: 1783942740,
    ...overrides
  }
}

function makeTableRow(overrides: Partial<Row<HostServiceEntry>> = {}): Row<HostServiceEntry> {
  return {
    getIsSelected: () => false,
    toggleSelected: () => {},
    ...overrides
  } as unknown as Row<HostServiceEntry>
}

function mountRow(
  row: HostServiceEntry,
  tableRow: Row<HostServiceEntry> = makeTableRow(),
  extraProps: Record<string, unknown> = {},
  service: MonitoringService<unknown> | null = null
) {
  return render(
    defineComponent({
      components: { HostServicesRow },
      render() {
        return h('table', [
          h('tbody', [
            h('tr', [
              h(HostServicesRow, {
                serviceHost: HOST,
                row,
                tableRow,
                displayOptions: DISPLAY_OPTIONS,
                ...extraProps
              })
            ])
          ])
        ])
      }
    }),
    service ? { global: { provide: { [MONITORING_SERVICE as symbol]: service } } } : {}
  )
}

test('renders service name and summary in their cells', () => {
  mountRow(makeService())

  expect(screen.getByTitle('CPU load')).toBeInTheDocument()
  expect(screen.getByText('OK - 15 min load: 0.5')).toBeInTheDocument()
})

test('renders one cell per column', () => {
  const { container } = mountRow(makeService())

  // select, state, modes, name, summary, last_state_change, last_check, labels, tags, contacts,
  // contact_groups, groups, perfometer
  const tds = Array.from(container.querySelectorAll('td'))
  expect(tds).toHaveLength(13)
})

test('renders last state change before last check, matching the legacy view', () => {
  const service = makeService()
  const { container } = mountRow(service)

  const tds = Array.from(container.querySelectorAll('td'))
  const lastStateChangeIndex = tds.findIndex(
    (td) => td.querySelector(`[title="${renderDateAndTime(service.last_state_change!)}"]`) !== null
  )
  const lastCheckIndex = tds.findIndex(
    (td) => td.querySelector(`[title="${renderDateAndTime(service.last_check!)}"]`) !== null
  )

  expect(lastStateChangeIndex).toBeGreaterThanOrEqual(0)
  expect(lastCheckIndex).toBeGreaterThan(lastStateChangeIndex)
})

test('renders the state markers of the summary as badges', () => {
  const { container } = mountRow(makeService({ summary: 'load: 3.1(!), temp: 90(!!)' }))

  expect(container.querySelector('.cmk-state-tag--warning')).toHaveTextContent('WA')
  expect(container.querySelector('.cmk-state-tag--critical')).toHaveTextContent('CR')
})

function summaryText(container: Element): Element {
  return container.querySelector('[data-column-id="summary"] .monitoring-string-cell__text')!
}

test('keeps a cut summary readable on hover, with the markers spelled out', async () => {
  const { container } = mountRow(makeService({ summary: 'load: 3.1(!), temp: 90(!!)' }))
  const text = summaryText(container)
  Object.defineProperty(text, 'scrollHeight', { configurable: true, value: 90 })
  Object.defineProperty(text, 'clientHeight', { configurable: true, value: 60 })

  await fireEvent.mouseEnter(text)

  expect(text).toHaveAttribute('title', 'load: 3.1(WARN), temp: 90(CRIT)')
})

test('repeats no summary on hover that fits the cell', async () => {
  const { container } = mountRow(makeService({ summary: 'load: 3.1(!), temp: 90(!!)' }))
  const text = summaryText(container)

  await fireEvent.mouseEnter(text)

  expect(text).not.toHaveAttribute('title')
})

test('renders the flapping icon next to the state badge for a flapping service', () => {
  mountRow(makeService({ is_flapping: true }))

  expect(screen.getByTitle('Flapping')).toBeInTheDocument()
})

test('renders the stale icon next to the state badge for a stale service', () => {
  mountRow(makeService({ stale: true }))

  expect(screen.getByTitle('Stale')).toBeInTheDocument()
})

test('renders neither icon for a service that is not flapping nor stale', () => {
  mountRow(makeService())

  expect(screen.queryByTitle('Flapping')).not.toBeInTheDocument()
  expect(screen.queryByTitle('Stale')).not.toBeInTheDocument()
})

test('resolves the service into the url of a row action', () => {
  mountRow(makeService({ name: 'CPU load' }), makeTableRow(), {
    rowActions: [
      {
        id: 'parameters',
        label: 'Parameters' as TranslatedString,
        icon: 'rulesets' as const,
        url: 'wato.py?mode=object_parameters&host=web-1&service={service}'
      }
    ]
  })

  expect(screen.getByRole('link', { name: 'Parameters' })).toHaveAttribute(
    'href',
    'wato.py?mode=object_parameters&host=web-1&service=CPU%20load'
  )
})

test('renders no action cell for a page that offers no menu', () => {
  const { container } = mountRow(makeService())

  expect(screen.queryByRole('button', { name: 'More actions' })).not.toBeInTheDocument()
  expect(Array.from(container.querySelectorAll('td'))).toHaveLength(13)
})

test('adds the action cell once a page offers the menu', () => {
  const { container } = mountRow(makeService(), makeTableRow(), {
    loadActionMenu: async () => []
  })

  expect(screen.getByRole('button', { name: 'More actions' })).toBeInTheDocument()
  expect(Array.from(container.querySelectorAll('td'))).toHaveLength(14)
})

test('loads the menu of its own service, and only once it is opened', async () => {
  const loadActionMenu = vi.fn(async () => [])
  mountRow(makeService({ name: 'Memory' }), makeTableRow(), { loadActionMenu })
  expect(loadActionMenu).not.toHaveBeenCalled()

  await userEvent.click(screen.getByRole('button', { name: 'More actions' }))

  expect(loadActionMenu).toHaveBeenCalledWith('Memory')
})

test('emits a picked command with the service it acts on', async () => {
  const command = {
    id: 'reschedule',
    label: 'Reschedule check' as TranslatedString,
    icon: 'reload' as const
  }
  const onCommand = vi.fn()
  render(
    defineComponent({
      components: { HostServicesRow },
      render() {
        return h('table', [
          h('tbody', [
            h('tr', [
              h(HostServicesRow, {
                serviceHost: HOST,
                row: makeService({ name: 'Memory' }),
                tableRow: makeTableRow(),
                displayOptions: DISPLAY_OPTIONS,
                loadActionMenu: async () => [command],
                onCommand
              })
            ])
          ])
        ])
      }
    })
  )

  await userEvent.click(screen.getByRole('button', { name: 'More actions' }))
  await userEvent.click(await screen.findByRole('menuitem', { name: /Reschedule check/ }))

  expect(onCommand).toHaveBeenCalledWith({ id: 'reschedule', target: 'Memory' })
})

test('offers no AI explanation by default', () => {
  mountRow(makeService(), makeTableRow(), { loadActionMenu: async () => [] })

  expect(screen.queryByRole('button', { name: 'Explain with AI' })).not.toBeInTheDocument()
})

test('asks for the AI explanation of its own service', async () => {
  const onExplain = vi.fn()
  const service = makeService({ name: 'Memory' })
  mountRow(service, makeTableRow(), { aiExplain: true, onExplain })

  await userEvent.click(screen.getByRole('button', { name: 'Explain with AI' }))

  expect(onExplain).toHaveBeenCalledWith(service)
})

test('renders the contact groups of a service, sorted alphabetically', () => {
  const { container } = mountRow(makeService({ contact_groups: ['linux', 'all'] }))

  const tags = Array.from(container.querySelectorAll('[data-label-cell-item]'))
  expect(tags.map((tag) => tag.textContent?.trim())).toEqual(['all', 'linux'])
})

test('renders the service groups of a service, sorted alphabetically', () => {
  const { container } = mountRow(makeService({ groups: ['web', 'databases'] }))

  const tags = Array.from(container.querySelectorAll('[data-label-cell-item]'))
  expect(tags.map((tag) => tag.textContent?.trim())).toEqual(['databases', 'web'])
})

test('clicking a service group narrows the listing to the services in that group', async () => {
  const service = makeListingService()
  mountRow(makeService({ groups: ['web', 'databases'] }), makeTableRow(), {}, service)

  await fireEvent.click(screen.getByRole('button', { name: 'databases' }))

  expect(service.filterState.value).toStrictEqual({
    type: 'condition',
    field: 'groups',
    op: 'one_of',
    value: ['databases']
  })
})

test('renders the contacts of a service, sorted alphabetically', () => {
  const { container } = mountRow(makeService({ contacts: ['ops', 'hh'] }))

  const tags = Array.from(container.querySelectorAll('[data-label-cell-item]'))
  expect(tags.map((tag) => tag.textContent?.trim())).toEqual(['hh', 'ops'])
})

test('renders the tags of a service, sorted alphabetically', () => {
  const { container } = mountRow(makeService({ tags: { networking: 'lan', criticality: 'prod' } }))

  const tags = Array.from(container.querySelectorAll('[data-label-cell-item]'))
  expect(tags.map((tag) => tag.textContent?.trim())).toEqual([
    'criticality: prod',
    'networking: lan'
  ])
})

test('renders the labels of a service, sorted alphabetically', () => {
  const { container } = mountRow(
    makeService({
      labels: {
        owner: { value: 'platform', source: 'explicit' },
        'cmk/check_plugin': { value: 'cpu_load', source: 'discovered' }
      }
    })
  )

  const tags = Array.from(container.querySelectorAll('[data-label-cell-item]'))
  expect(tags.map((tag) => tag.textContent?.trim())).toEqual([
    'cmk/check_plugin: cpu_load',
    'owner: platform'
  ])
})

test('clicking a label narrows the listing to the services carrying it', async () => {
  const service = makeListingService()
  mountRow(
    makeService({ labels: { owner: { value: 'platform', source: 'explicit' } } }),
    makeTableRow(),
    {},
    service
  )

  await fireEvent.click(screen.getByRole('button', { name: 'owner: platform' }))

  expect(service.filterState.value).toStrictEqual({
    type: 'condition',
    field: 'labels',
    op: 'all_of',
    value: ['owner:platform']
  })
})

test('renders the perfometer of a service that has one', () => {
  mountRow(
    makeService({
      perfometer: {
        bars: [
          [
            { share: 42, color: '#ff0000' },
            { share: 58, color: null }
          ]
        ],
        formatted: '42%'
      }
    })
  )

  const perfometer = screen.getByRole('progressbar', { name: 'Perf-O-Meter' })
  expect(perfometer).toHaveAttribute('aria-valuenow', '42')
  expect(perfometer).toHaveTextContent('42%')
})

test('the perfometer asks for the graphs of its service', async () => {
  const openGraphs = vi.fn()
  const service = makeService({
    perfometer: {
      bars: [
        [
          { share: 42, color: '#ff0000' },
          { share: 58, color: null }
        ]
      ],
      formatted: '42%'
    }
  })
  const { container } = mountRow(service, makeTableRow(), { onOpenGraphs: openGraphs })

  await userEvent.click(container.querySelector('td[data-column-id="perfometer"] button')!)

  expect(openGraphs).toHaveBeenCalledWith(service)
})

test('links a service with graphs to its graphs page, beside its name', () => {
  const graphsLink =
    'view.py?view_name=service_graphs&site=local&host=web-server-01&service=CPU+load'
  const { container } = mountRow(makeService({ name: 'CPU load', graphs_link: graphsLink }))

  const link = screen.getByRole('link', { name: 'Show the graphs of service CPU load' })
  expect(link).toHaveAttribute('href', graphsLink)
  expect(container.querySelector('td[data-column-id="name"]')).toContainElement(link)
})

test('offers no graphs link for a service without graphs', () => {
  mountRow(makeService({ name: 'CPU load' }))

  expect(
    screen.queryByRole('link', { name: 'Show the graphs of service CPU load' })
  ).not.toBeInTheDocument()
})

test('a service without a perfometer leaves its cell unclickable', () => {
  const { container } = mountRow(makeService())

  expect(container.querySelector('td[data-column-id="perfometer"] button')).toBeNull()
})

test('leaves the perfometer cell empty for a service without performance data', () => {
  mountRow(makeService())

  expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
})

test('renders the two timestamps as formatted date-time strings', () => {
  const { container } = mountRow(makeService())

  const cellText = (td: Element): string => (td.textContent ?? '').trim()
  const tds = Array.from(container.querySelectorAll('td'))
  expect(cellText(tds[5]!)).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)
  expect(cellText(tds[6]!)).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)
})

test('dashes out the state age of a service that has never been checked', () => {
  const { container } = mountRow(makeService({ last_state_change: null }))

  const cellText = (td: Element): string => (td.textContent ?? '').trim()
  const tds = Array.from(container.querySelectorAll('td'))
  expect(cellText(tds[5]!)).toBe('–')
})

test('dashes out the last check of a service that has never been checked', () => {
  const { container } = mountRow(makeService({ last_check: null }))

  const cellText = (td: Element): string => (td.textContent ?? '').trim()
  const tds = Array.from(container.querySelectorAll('td'))
  expect(cellText(tds[6]!)).toBe('–')
})

test('renders the state badge with success color for state OK', () => {
  const { container } = mountRow(makeService({ state: 'OK' }))

  const stateTag = container.querySelector('.cmk-state-tag--ok')
  expect(stateTag).not.toBeNull()
  expect(stateTag).toHaveTextContent('OK')
})

test('renders the state badge with warning color for state WARN', () => {
  const { container } = mountRow(makeService({ state: 'WARN' }))

  const stateTag = container.querySelector('.cmk-state-tag--warning')
  expect(stateTag).not.toBeNull()
  expect(stateTag).toHaveTextContent('WARNING')
})

test('renders the state badge with danger color for state CRIT', () => {
  const { container } = mountRow(makeService({ state: 'CRIT' }))

  const stateTag = container.querySelector('.cmk-state-tag--critical')
  expect(stateTag).not.toBeNull()
  expect(stateTag).toHaveTextContent('CRITICAL')
})

test('renders the state badge with unknown color for state UNKNOWN', () => {
  const { container } = mountRow(makeService({ state: 'UNKNOWN' }))

  const stateTag = container.querySelector('.cmk-state-tag--unknown')
  expect(stateTag).not.toBeNull()
  expect(stateTag).toHaveTextContent('UNKNOWN')
})

test('renders the state badge as pending for a service that has never been checked', () => {
  mountRow(makeService({ state: 'PENDING' }))

  expect(screen.getByText('PENDING')).toBeInTheDocument()
  expect(screen.queryByText('CRITICAL')).not.toBeInTheDocument()
})

test('renders a checkbox cell for row selection', () => {
  mountRow(makeService())

  const checkbox = screen.getByRole('checkbox', { name: /Select service CPU load/i })
  expect(checkbox).toBeInTheDocument()
})

test('checkbox reflects selected state from tableRow', () => {
  const tableRow = makeTableRow({ getIsSelected: () => true })
  mountRow(makeService(), tableRow)

  const checkbox = screen.getByRole('checkbox', { name: /Select service CPU load/i })
  expect(checkbox).toBeChecked()
})

test('checkbox calls toggleSelected on tableRow when clicked', async () => {
  const toggleSelected = vi.fn()
  const tableRow = makeTableRow({ toggleSelected })
  mountRow(makeService(), tableRow)

  const checkbox = screen.getByRole('checkbox', { name: /Select service CPU load/i })
  await fireEvent.click(checkbox)

  expect(toggleSelected).toHaveBeenCalledWith(true)
})

test('offers the reschedule the backend decided on, ahead of the menu links', async () => {
  mountRow(
    makeService({ name: 'Memory', reschedule: reschedulesItself('Memory') }),
    makeTableRow(),
    {
      mayReschedule: true,
      loadActionMenu: async () => [
        {
          id: 'graphs',
          label: 'Graphs' as TranslatedString,
          icon: 'graph' as const,
          url: 'view.py'
        }
      ]
    }
  )

  await userEvent.click(screen.getByRole('button', { name: 'More actions' }))

  const items = await screen.findAllByRole('menuitem')
  expect(items.map((item) => item.textContent?.trim())).toEqual(['Reschedule check', 'Graphs'])
})

test('reschedules the Check_MK service for a service that is a byproduct of it', async () => {
  const onCommand = vi.fn()
  mountRow(
    makeService({
      name: 'Check_MK Agent',
      reschedule: {
        label: "Reschedule 'Check_MK' service",
        tooltip: "Reschedule 'Check_MK' service",
        icon_name: 'reload-cmk',
        target: 'Check_MK'
      }
    }),
    makeTableRow(),
    { mayReschedule: true, onCommand }
  )

  await userEvent.click(screen.getByRole('button', { name: 'More actions' }))
  await userEvent.click(await screen.findByRole('menuitem', { name: /Reschedule 'Check_MK'/ }))

  expect(onCommand).toHaveBeenCalledWith({ id: 'reschedule', target: 'Check_MK' })
})

test('shows a reschedule that cannot be run greyed out, with the reason on hover', async () => {
  const onCommand = vi.fn()
  mountRow(
    makeService({
      name: 'CPU load',
      reschedule: {
        label: 'Reschedule check',
        tooltip: 'This service is based on cached agent data and cannot be rescheduled.',
        icon_name: 'cannot-reschedule'
      }
    }),
    makeTableRow(),
    { mayReschedule: true, onCommand }
  )

  await userEvent.click(screen.getByRole('button', { name: 'More actions' }))
  const item = await screen.findByRole('menuitem', { name: /Reschedule check/ })

  expect(item).toHaveAttribute(
    'title',
    'This service is based on cached agent data and cannot be rescheduled.'
  )
  await userEvent.click(item)
  expect(onCommand).not.toHaveBeenCalled()
})

test('leaves the reschedule out for a service the backend offers none for', async () => {
  mountRow(makeService({ name: 'CPU load' }), makeTableRow(), {
    mayReschedule: true,
    loadActionMenu: async () => [
      { id: 'graphs', label: 'Graphs' as TranslatedString, icon: 'graph' as const, url: 'view.py' }
    ]
  })

  await userEvent.click(screen.getByRole('button', { name: 'More actions' }))

  expect(await screen.findByRole('menuitem', { name: 'Graphs' })).toBeInTheDocument()
  expect(screen.queryByRole('menuitem', { name: /Reschedule/ })).not.toBeInTheDocument()
})

test('leaves the reschedule out for a user who may not reschedule', () => {
  mountRow(makeService({ reschedule: reschedulesItself('CPU load') }), makeTableRow(), {
    mayReschedule: false
  })

  expect(screen.queryByRole('button', { name: 'More actions' })).not.toBeInTheDocument()
})

function makeServiceOfHost(): ServiceEntry {
  return { ...makeService(), host_name: 'web-2', site_id: 'remote', host_state: 'UP' }
}

function mountRowInLayout(row: HostServiceEntry, columnIds: string[]) {
  const layoutInfo: ColumnLayoutInfo = {
    width: null,
    pinnedLeft: null,
    pinnedRight: null,
    isLastPinned: false,
    isFirstPinnedRight: false,
    justify: 'left'
  }
  return render(
    defineComponent({
      setup() {
        provide(
          COLUMN_LAYOUT_KEY,
          computed(() => new Map(columnIds.map((id) => [id, layoutInfo])))
        )
      },
      render() {
        return h('table', [
          h('tbody', [
            h('tr', [
              h(HostServicesRow, {
                row,
                serviceHost: HOST,
                tableRow: makeTableRow(),
                displayOptions: DISPLAY_OPTIONS
              })
            ])
          ])
        ])
      }
    })
  )
}

function renderedColumnIds(container: Element): (string | null)[] {
  return Array.from(container.querySelectorAll('td')).map((td) => td.getAttribute('data-column-id'))
}

test('renders the host and site of a row that names its host after the summary', () => {
  const { container } = mountRow(makeServiceOfHost())

  const cells = renderedColumnIds(container)
  expect(cells.slice(cells.indexOf('name'), cells.indexOf('site_id') + 1)).toEqual([
    'name',
    'summary',
    'host_name',
    'site_id'
  ])
  expect(screen.getByText('web-2')).toBeInTheDocument()
  expect(screen.getByText('remote')).toBeInTheDocument()
})

test('opens the host on a click anywhere in its cell, its state included', async () => {
  const openHost = vi.fn()
  const { container } = mountRow(makeServiceOfHost(), makeTableRow(), { onOpenHost: openHost })
  const hostCell = container.querySelector('[data-column-id="host_name"]') as HTMLElement

  await userEvent.click(within(hostCell).getByText('UP'))
  await userEvent.click(within(hostCell).getByText('web-2'))

  expect(openHost).toHaveBeenCalledTimes(2)
  expect(openHost).toHaveBeenLastCalledWith({ name: 'web-2', site_id: 'remote', state: 'UP' })
})

test('renders no host cells in a layout without the host and site columns', () => {
  const { container } = mountRowInLayout(makeServiceOfHost(), ['state', 'name'])

  expect(renderedColumnIds(container)).toEqual(['state', 'name'])
})

test('renders only the site cell in a layout without the host column', () => {
  const { container } = mountRowInLayout(makeServiceOfHost(), [
    'state',
    'name',
    'summary',
    'site_id'
  ])

  expect(renderedColumnIds(container)).toEqual(['state', 'name', 'summary', 'site_id'])
})

test('renders no host cells for a service of the page host', () => {
  const { container } = mountRow(makeService())

  expect(container.querySelector('[data-column-id="host_name"]')).toBeNull()
  expect(container.querySelector('[data-column-id="site_id"]')).toBeNull()
})

test('shows the state of the host beside its name', () => {
  const service: ServiceEntry = { ...makeServiceOfHost(), host_state: 'DOWN' }
  const { container } = mountRow(service)

  const hostCell = container.querySelector('[data-column-id="host_name"]') as HTMLElement
  expect(within(hostCell).getByText('DO')).toBeInTheDocument()
  expect(within(hostCell).getByText('web-2')).toBeInTheDocument()
})
