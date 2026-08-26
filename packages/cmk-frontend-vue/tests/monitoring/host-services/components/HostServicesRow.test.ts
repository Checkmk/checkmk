/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Row } from '@tanstack/vue-table'
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { defineComponent, h } from 'vue'

import HostServicesRow from '@/monitoring/host-services/components/HostServicesRow.vue'
import type { HostServiceEntry } from '@/monitoring/shared/api/types'

const ZERO_WIDTH_SPACE = String.fromCharCode(0x200b)

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
  extraProps: Record<string, unknown> = {}
) {
  return render(
    defineComponent({
      components: { HostServicesRow },
      render() {
        return h('table', [
          h('tbody', [h('tr', [h(HostServicesRow, { row, tableRow, ...extraProps })])])
        ])
      }
    })
  )
}

test('renders service name and summary in their cells', () => {
  mountRow(makeService())

  expect(screen.getByTitle('CPU load')).toBeInTheDocument()
  expect(screen.getByTitle('OK - 15 min load: 0.5')).toBeInTheDocument()
})

test('renders one cell per column', () => {
  const { container } = mountRow(makeService())

  // select, state, modes, name, summary, last_check, last_state_change, labels, tags, contacts,
  // contact_groups, perfometer
  const tds = Array.from(container.querySelectorAll('td'))
  expect(tds).toHaveLength(12)
})

test('renders the state markers of the summary as badges', () => {
  const { container } = mountRow(makeService({ summary: 'load: 3.1(!), temp: 90(!!)' }))

  expect(container.querySelector('.cmk-state-tag--warning')).toHaveTextContent('WA')
  expect(container.querySelector('.cmk-state-tag--critical')).toHaveTextContent('CR')
})

test('keeps the whole summary readable on hover, markers and all', () => {
  const summary = 'load: 3.1(!), temp: 90(!!)'
  mountRow(makeService({ summary }))

  expect(screen.getByTitle(summary)).toBeInTheDocument()
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
  expect(Array.from(container.querySelectorAll('td'))).toHaveLength(12)
})

test('adds the action cell once a page offers the menu', () => {
  const { container } = mountRow(makeService(), makeTableRow(), {
    loadActionMenu: async () => []
  })

  expect(screen.getByRole('button', { name: 'More actions' })).toBeInTheDocument()
  expect(Array.from(container.querySelectorAll('td'))).toHaveLength(13)
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
                row: makeService({ name: 'Memory' }),
                tableRow: makeTableRow(),
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

test('renders the contact groups of a service, sorted alphabetically', () => {
  const { container } = mountRow(makeService({ contact_groups: ['linux', 'all'] }))

  const tags = Array.from(container.querySelectorAll('[data-label-cell-item]'))
  expect(tags.map((tag) => tag.textContent?.trim())).toEqual(['all', 'linux'])
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

test('renders the perfometer of a service that has one', () => {
  mountRow(
    makeService({
      perfometer: {
        value: 42,
        value_range: { min: 0, max: 100 },
        formatted: '42%',
        color: '#ff0000'
      }
    })
  )

  const perfometer = screen.getByRole('progressbar', { name: 'Perf-O-Meter' })
  expect(perfometer).toHaveAttribute('aria-valuenow', '42')
  expect(perfometer).toHaveTextContent('42%')
})

test('leaves the perfometer cell empty for a service without performance data', () => {
  mountRow(makeService())

  expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
})

test('renders the two timestamps as formatted date-time strings', () => {
  const { container } = mountRow(makeService())

  const cellText = (td: Element): string =>
    (td.textContent ?? '').split(ZERO_WIDTH_SPACE).join('').trim()
  const tds = Array.from(container.querySelectorAll('td'))
  expect(cellText(tds[5]!)).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)
  expect(cellText(tds[6]!)).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)
})

test('dashes out the last check of a service that has never been checked', () => {
  const { container } = mountRow(makeService({ last_check: null }))

  const cellText = (td: Element): string =>
    (td.textContent ?? '').split(ZERO_WIDTH_SPACE).join('').trim()
  const tds = Array.from(container.querySelectorAll('td'))
  expect(cellText(tds[5]!)).toBe('–')
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
