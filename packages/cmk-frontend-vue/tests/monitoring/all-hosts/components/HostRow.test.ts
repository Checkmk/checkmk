/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { defineComponent, h } from 'vue'

import HostRow from '@/monitoring/all-hosts/components/HostRow.vue'
import type { HostEntry } from '@/monitoring/shared/api/types'

function makeHost(overrides: Partial<HostEntry> = {}): HostEntry {
  return {
    name: 'web-1',
    state: 'UP',
    address: '10.0.0.1',
    alias: 'web server 1',
    site_id: 'local',
    num_services: 6,
    num_services_ok: 5,
    num_services_warn: 1,
    num_services_crit: 0,
    num_services_unknown: 0,
    num_services_pending: 0,
    ...overrides
  }
}

function mountRow(row: HostEntry) {
  return render(
    defineComponent({
      components: { HostRow },
      render() {
        return h('table', [h('tbody', [h('tr', [h(HostRow, { row })])])])
      }
    })
  )
}

test('renders host name, alias and ip in their cells', () => {
  mountRow(makeHost())

  expect(screen.getByTitle('web-1')).toBeInTheDocument()
  expect(screen.getByTitle('web server 1')).toBeInTheDocument()
  expect(screen.getByTitle('10.0.0.1')).toBeInTheDocument()
})

test('renders state badge with success color for state UP', () => {
  const { container } = mountRow(makeHost({ state: 'UP' }))

  const stateTag = container.querySelector('.monitoring-base-cell__highlight--color-success')
  expect(stateTag).not.toBeNull()
  expect(stateTag).toHaveTextContent('UP')
})

test('renders state badge with danger color for state DOWN', () => {
  const { container } = mountRow(makeHost({ state: 'DOWN' }))

  const stateTag = container.querySelector('.monitoring-base-cell__highlight--color-danger')
  expect(stateTag).not.toBeNull()
  expect(stateTag).toHaveTextContent('DOWN')
})

test('renders state badge with warning color for state UNREACHABLE', () => {
  const { container } = mountRow(makeHost({ state: 'UNREACHABLE' }))

  const stateTag = container.querySelector('.monitoring-base-cell__highlight--color-warning')
  expect(stateTag).not.toBeNull()
  expect(stateTag).toHaveTextContent('UNREACH')
})

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

  const tds = Array.from(container.querySelectorAll('td'))
  // state, name, alias, address, total, ok, warn, crit, unknown, pending
  expect(tds).toHaveLength(10)
  expect(tds[4]).toHaveTextContent('15')
  expect(tds[5]).toHaveTextContent('1')
  expect(tds[6]).toHaveTextContent('2')
  expect(tds[7]).toHaveTextContent('3')
  expect(tds[8]).toHaveTextContent('4')
  expect(tds[9]).toHaveTextContent('5')
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
