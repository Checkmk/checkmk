/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Row } from '@tanstack/vue-table'
import { fireEvent, render, screen } from '@testing-library/vue'
import { defineComponent, h } from 'vue'

import { buildHostColumns } from '@/monitoring/all-hosts/columns'
import HostRow from '@/monitoring/all-hosts/components/HostRow.vue'
import type { HostEntry } from '@/monitoring/shared/api/types'
import { formatTimestamp } from '@/monitoring/shared/formatTimestamp'
import { columnId } from '@/monitoring/shared/tableState/schema'

function makeHost(overrides: Partial<HostEntry> = {}): HostEntry {
  return {
    name: 'web-1',
    state: 'UP',
    is_flapping: false,
    stale: false,
    address: '10.0.0.1',
    alias: 'web server 1',
    folder: 'Netzwerk / Rechenzentrum 1',
    site_id: 'local',
    num_services: 6,
    num_services_ok: 5,
    num_services_warn: 1,
    num_services_crit: 0,
    num_services_unknown: 0,
    num_services_pending: 0,
    last_check: 1783942710,
    last_state_change: 1783942740,
    legacy_host_status_link: 'view.py?view_name=hoststatus&site=local&host=web-1',
    num_relations: 0,
    ...overrides
  }
}

function makeTableRow(overrides: Partial<Row<HostEntry>> = {}): Row<HostEntry> {
  return {
    getIsSelected: () => false,
    toggleSelected: () => {},
    ...overrides
  } as unknown as Row<HostEntry>
}

function mountRow(row: HostEntry, tableRow: Row<HostEntry> = makeTableRow()) {
  return render(
    defineComponent({
      components: { HostRow },
      render() {
        return h('table', [h('tbody', [h('tr', [h(HostRow, { row, tableRow })])])])
      }
    })
  )
}

test('renders host name and ip in their cells', () => {
  mountRow(makeHost())

  expect(screen.getByTitle('web-1')).toBeInTheDocument()
  expect(screen.getByTitle('10.0.0.1')).toBeInTheDocument()
})

test('renders alias, folder and formatted timestamps in their cells', () => {
  const host = makeHost()
  mountRow(host)

  expect(screen.getByTitle('web server 1')).toBeInTheDocument()
  expect(screen.getByTitle('Netzwerk / Rechenzentrum 1')).toBeInTheDocument()
  expect(screen.getByTitle(formatTimestamp(host.last_check!))).toBeInTheDocument()
  expect(screen.getByTitle(formatTimestamp(host.last_state_change!))).toBeInTheDocument()
})

test('emits open with the host when the name cell button is clicked', async () => {
  const host = makeHost()
  const onOpen = vi.fn()
  const { container } = render(
    defineComponent({
      components: { HostRow },
      render() {
        return h('table', [
          h('tbody', [h('tr', [h(HostRow, { row: host, tableRow: makeTableRow(), onOpen })])])
        ])
      }
    })
  )

  const nameButton = container.querySelector('.monitoring-string-cell button')!
  await fireEvent.click(nameButton)

  expect(onOpen).toHaveBeenCalledWith(host)
})

test('renders state badge with success color for state UP', () => {
  const { container } = mountRow(makeHost({ state: 'UP' }))

  const stateTag = container.querySelector('.cmk-state-tag--ok')
  expect(stateTag).not.toBeNull()
  expect(stateTag).toHaveTextContent('UP')
})

test('renders state badge with danger color for state DOWN', () => {
  const { container } = mountRow(makeHost({ state: 'DOWN' }))

  const stateTag = container.querySelector('.cmk-state-tag--critical')
  expect(stateTag).not.toBeNull()
  expect(stateTag).toHaveTextContent('DOWN')
})

test('renders state badge with unknown color for state UNREACHABLE', () => {
  const { container } = mountRow(makeHost({ state: 'UNREACHABLE' }))

  const stateTag = container.querySelector('.cmk-state-tag--unknown')
  expect(stateTag).not.toBeNull()
  expect(stateTag).toHaveTextContent('UNREACH')
})

test('renders the state badge as pending for a host that has never been checked', () => {
  mountRow(makeHost({ state: 'PENDING' }))

  expect(screen.getByText('PENDING')).toBeInTheDocument()
  expect(screen.queryByText('DOWN')).not.toBeInTheDocument()
})

test('renders the flapping icon next to the state badge for a flapping host', () => {
  mountRow(makeHost({ is_flapping: true }))

  expect(screen.getByTitle('Flapping')).toBeInTheDocument()
})

test('renders the stale icon next to the state badge for a stale host', () => {
  mountRow(makeHost({ stale: true }))

  expect(screen.getByTitle('Stale')).toBeInTheDocument()
})

test('renders neither icon for a host that is not flapping nor stale', () => {
  mountRow(makeHost())

  expect(screen.queryByTitle('Flapping')).not.toBeInTheDocument()
  expect(screen.queryByTitle('Stale')).not.toBeInTheDocument()
})

const SERVICE_COUNT_COLUMNS = [
  'num_services',
  'num_services_ok',
  'num_services_warn',
  'num_services_crit',
  'num_services_unknown',
  'num_services_pending'
] as const

function cell(container: Element, columnId: string): HTMLElement {
  const td = container.querySelector<HTMLElement>(`td[data-column-id="${columnId}"]`)
  expect(td, `no cell for column ${columnId}`).not.toBeNull()
  return td!
}

test('renders one cell per service state with its count', () => {
  const { container } = mountRow(
    makeHost({
      num_services: 15,
      num_services_ok: 1,
      num_services_warn: 2,
      num_services_crit: 3,
      num_services_unknown: 4,
      num_services_pending: 5
    })
  )

  const counts = SERVICE_COUNT_COLUMNS.map((id) => cell(container, id).textContent?.trim())
  expect(counts).toEqual(['15', '1', '2', '3', '4', '5'])
})

test('renders its cells in the order the columns are defined in', () => {
  const { container } = mountRow(makeHost())

  const rendered = Array.from(container.querySelectorAll('td')).map((td) => td.dataset['columnId'])
  const defined = buildHostColumns({
    includeSelect: true,
    includeActions: false,
    showCustomer: true,
    sites: [],
    showRelations: true
  }).map(columnId)

  expect(rendered).toEqual(defined)
})

function serviceCountLinks(container: Element): Array<HTMLAnchorElement | null> {
  return SERVICE_COUNT_COLUMNS.map((id) => cell(container, id).querySelector('a'))
}

function filterParam(link: HTMLAnchorElement | null | undefined): string | null {
  return new URL(
    link!.getAttribute('href')!,
    'http://checkmk.example/site/check_mk/'
  ).searchParams.get('filter')
}

function stateFilter(...states: string[]): string {
  return JSON.stringify({ type: 'condition', field: 'state', op: 'one_of', value: states })
}

test('links every service count to the services of that host', () => {
  const { container } = mountRow(
    makeHost({
      num_services: 15,
      num_services_ok: 1,
      num_services_warn: 2,
      num_services_crit: 3,
      num_services_unknown: 4,
      num_services_pending: 5
    })
  )

  for (const link of serviceCountLinks(container)) {
    expect(link).toHaveAttribute('target', '_top')
    expect(link!.getAttribute('href')).toContain('monitor_host_services.py?host=web-1&site=local')
  }
})

test('narrows each service count link to the state that column counts', () => {
  const { container } = mountRow(
    makeHost({
      num_services: 15,
      num_services_ok: 1,
      num_services_warn: 2,
      num_services_crit: 3,
      num_services_unknown: 4,
      num_services_pending: 5
    })
  )

  const [total, ok, warn, crit, unknown, pending] = serviceCountLinks(container)
  expect(filterParam(total)).toBeNull()
  expect(filterParam(ok)).toBe(stateFilter('OK'))
  expect(filterParam(warn)).toBe(stateFilter('WARN'))
  expect(filterParam(crit)).toBe(stateFilter('CRIT'))
  expect(filterParam(unknown)).toBe(stateFilter('UNKNOWN'))
  expect(filterParam(pending)).toBe(stateFilter('PENDING'))
})

test('links no service count a host has none of', () => {
  const { container } = mountRow(
    makeHost({
      num_services: 0,
      num_services_ok: 0,
      num_services_warn: 0,
      num_services_crit: 0,
      num_services_unknown: 0,
      num_services_pending: 0
    })
  )

  expect(serviceCountLinks(container)).toEqual([null, null, null, null, null, null])
})

test('toggles the row selection when the checkbox is clicked', async () => {
  const toggleSelected = vi.fn()
  const { container } = mountRow(makeHost(), makeTableRow({ toggleSelected }))

  const checkbox = container.querySelector('.cmk-checkbox__button')!
  await fireEvent.click(checkbox)

  expect(toggleSelected).toHaveBeenCalledWith(true)
})

test('reflects the selected state from the tanstack row', () => {
  const { container } = mountRow(makeHost(), makeTableRow({ getIsSelected: () => true }))

  const checkbox = container.querySelector('.cmk-checkbox__button')!
  expect(checkbox).toHaveAttribute('aria-checked', 'true')
})

test('renders the relation count in the cell following the host name', () => {
  const { container } = mountRow(makeHost({ num_relations: 2 }))

  expect(cell(container, 'num_relations')).toHaveTextContent('2')
  expect(cell(container, 'num_relations').querySelector('button')).not.toBeNull()
})

test('names the relation count button, whose number alone says nothing about it', () => {
  const { container } = mountRow(makeHost({ name: 'web-01', num_relations: 2 }))

  expect(cell(container, 'num_relations').querySelector('button')).toHaveAccessibleName(
    'Show the 2 related hosts of web-01'
  )
})

test('names the button of a host with a single relation in the singular', () => {
  const { container } = mountRow(makeHost({ name: 'web-01', num_relations: 1 }))

  expect(cell(container, 'num_relations').querySelector('button')).toHaveAccessibleName(
    'Show the 1 related host of web-01'
  )
})

test('leaves the relation cell of a host without relations empty and unclickable', () => {
  const { container } = mountRow(makeHost({ num_relations: 0 }))

  expect(cell(container, 'num_relations').textContent?.trim()).toBe('')
  expect(cell(container, 'num_relations').querySelector('button')).toBeNull()
})

test('emits open asking for the relations when the relation count is clicked', async () => {
  const host = makeHost({ num_relations: 2 })
  const onOpen = vi.fn()
  const { container } = render(
    defineComponent({
      components: { HostRow },
      render() {
        return h('table', [
          h('tbody', [h('tr', [h(HostRow, { row: host, tableRow: makeTableRow(), onOpen })])])
        ])
      }
    })
  )

  await fireEvent.click(cell(container, 'num_relations').querySelector('button')!)

  expect(onOpen).toHaveBeenCalledWith(host, true)
})

test('renders the zero counts as well — one badge per service state column', () => {
  mountRow(
    makeHost({
      num_services_ok: 0,
      num_services_warn: 0,
      num_services_crit: 0,
      num_services_unknown: 0,
      num_services_pending: 0
    })
  )

  expect(screen.getAllByText('0')).toHaveLength(5)
})

test('renders the labels of a host, sorted alphabetically', () => {
  const { container } = mountRow(
    makeHost({
      labels: {
        owner: { value: 'platform', source: 'explicit' },
        'cmk/site': { value: 'heute', source: 'discovered' }
      }
    })
  )

  const tags = Array.from(container.querySelectorAll('[data-label-cell-item]'))
  expect(tags.map((tag) => tag.textContent?.trim())).toEqual(['cmk/site: heute', 'owner: platform'])
})

test('renders the tags of a host, sorted alphabetically', () => {
  const { container } = mountRow(makeHost({ tags: { networking: 'lan', criticality: 'prod' } }))

  const tags = Array.from(container.querySelectorAll('[data-label-cell-item]'))
  expect(tags.map((tag) => tag.textContent?.trim())).toEqual([
    'criticality: prod',
    'networking: lan'
  ])
})

test('renders the contacts of a host, sorted alphabetically', () => {
  const { container } = mountRow(makeHost({ contacts: ['ops', 'hh'] }))

  const tags = Array.from(container.querySelectorAll('[data-label-cell-item]'))
  expect(tags.map((tag) => tag.textContent?.trim())).toEqual(['hh', 'ops'])
})

test('renders the contact groups of a host, sorted alphabetically', () => {
  const { container } = mountRow(makeHost({ contact_groups: ['linux', 'all'] }))

  const tags = Array.from(container.querySelectorAll('[data-label-cell-item]'))
  expect(tags.map((tag) => tag.textContent?.trim())).toEqual(['all', 'linux'])
})

test('renders the customer of a host', () => {
  mountRow(makeHost({ customer: 'Customer A' }))

  // Asserted through the title: the cell breaks long values with zero-width spaces.
  expect(screen.getByTitle('Customer A')).toBeInTheDocument()
})
