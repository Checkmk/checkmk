/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
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

function mountRow(row: HostServiceEntry) {
  return render(
    defineComponent({
      components: { HostServicesRow },
      render() {
        return h('table', [h('tbody', [h('tr', [h(HostServicesRow, { row })])])])
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

  const tds = Array.from(container.querySelectorAll('td'))
  expect(tds).toHaveLength(5)
})

test('renders the two timestamps as formatted date-time strings', () => {
  const { container } = mountRow(makeService())

  const cellText = (td: Element): string =>
    (td.textContent ?? '').split(ZERO_WIDTH_SPACE).join('').trim()
  const tds = Array.from(container.querySelectorAll('td'))
  expect(cellText(tds[3]!)).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)
  expect(cellText(tds[4]!)).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)
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
