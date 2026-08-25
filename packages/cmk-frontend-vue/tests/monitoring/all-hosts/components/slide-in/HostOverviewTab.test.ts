/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, within } from '@testing-library/vue'

import HostOverviewTab from '@/monitoring/all-hosts/components/slide-in/HostOverviewTab.vue'
import type { HostOverview } from '@/monitoring/shared/api/types'

function makeData(overrides: Partial<HostOverview> = {}): HostOverview {
  return {
    name: 'web-1',
    alias: 'web server 1',
    address: '10.0.0.1',
    state: 'UP',
    site_id: 'local',
    site_alias: 'Local site',
    folder: 'Netzwerk',
    customer: null,
    contact_groups: ['all'],
    tags: { 'cmk/os_family': 'linux' },
    labels: { 'cmk/os_family': { source: 'discovered', value: 'linux' } },
    modes: [],
    service_counts: { ok: 9, warn: 2, crit: 3, unknown: 1, pending: 0, total: 15 },
    last_check: 1784023200,
    last_state_change: 1784019600,
    legacy_host_status_link: '/check_mk/index.py',
    ...overrides
  }
}

test('renders the service summary state-count bar from the host service counts', async () => {
  render(HostOverviewTab, { props: { data: makeData() } })

  const bar = await screen.findByRole('img')
  expect(bar).toHaveAttribute('aria-label', '9 OK, 2 WARN, 3 CRIT, 1 UNKNOWN')

  // Non-zero states each occupy a bar segment; PENDING (0) is omitted.
  const segments = bar.querySelectorAll('.cmk-state-count-bar__segment')
  expect(segments).toHaveLength(4)
})

test('legend lists every state with its count, including the zero one', async () => {
  const { container } = render(HostOverviewTab, { props: { data: makeData() } })

  await screen.findByRole('img')

  const legendItems = container.querySelectorAll<HTMLElement>('.cmk-state-count-bar__legend-item')
  const expected: [string, string][] = [
    ['OK', '9'],
    ['WARN', '2'],
    ['CRIT', '3'],
    ['UNKNOWN', '1'],
    ['PENDING', '0']
  ]
  expect(legendItems).toHaveLength(expected.length)
  expected.forEach(([label, count], index) => {
    const item = within(legendItems[index]!)
    expect(item.getByText(label)).toBeInTheDocument()
    expect(item.getByText(count)).toBeInTheDocument()
  })
})
