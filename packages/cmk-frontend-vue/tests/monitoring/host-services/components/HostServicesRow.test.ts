/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Row } from '@tanstack/vue-table'
import { fireEvent, render, screen } from '@testing-library/vue'
import { defineComponent, h } from 'vue'

import HostServicesRow from '@/monitoring/host-services/components/HostServicesRow.vue'
import type { HostServiceEntry } from '@/monitoring/shared/api/types'

const ZERO_WIDTH_SPACE = String.fromCharCode(0x200b)

function makeService(overrides: Partial<HostServiceEntry> = {}): HostServiceEntry {
  return {
    name: 'CPU load',
    state: 'OK',
    summary: 'OK - 15 min load: 0.5',
    last_check: '2026-07-13T11:38:30Z',
    last_state_change: '2026-07-13T11:39:00Z',
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

function mountRow(row: HostServiceEntry, tableRow: Row<HostServiceEntry> = makeTableRow()) {
  return render(
    defineComponent({
      components: { HostServicesRow },
      render() {
        return h('table', [h('tbody', [h('tr', [h(HostServicesRow, { row, tableRow })])])])
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

  // select, state, modes, name, summary, last_check, last_state_change, labels, tags, perfometer
  const tds = Array.from(container.querySelectorAll('td'))
  expect(tds).toHaveLength(10)
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

  const stateTag = container.querySelector('.cmk-tag--color-success')
  expect(stateTag).not.toBeNull()
  expect(stateTag).toHaveTextContent('OK')
})

test('renders the state badge with warning color for state WARN', () => {
  const { container } = mountRow(makeService({ state: 'WARN' }))

  const stateTag = container.querySelector('.cmk-tag--color-warning')
  expect(stateTag).not.toBeNull()
  expect(stateTag).toHaveTextContent('WARN')
})

test('renders the state badge with danger color for state CRIT', () => {
  const { container } = mountRow(makeService({ state: 'CRIT' }))

  const stateTag = container.querySelector('.cmk-tag--color-danger')
  expect(stateTag).not.toBeNull()
  expect(stateTag).toHaveTextContent('CRIT')
})

test('renders the state badge with unknown color for state UNKNOWN', () => {
  const { container } = mountRow(makeService({ state: 'UNKNOWN' }))

  const stateTag = container.querySelector('.cmk-tag--color-unknown')
  expect(stateTag).not.toBeNull()
  expect(stateTag).toHaveTextContent('UNKN')
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
