/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

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
    relations: [],
    more_relations: false,
    ...overrides
  }
}

const RELATION: HostOverview['relations'][number] = {
  host_name: 'mgmt-web-1',
  kind: 'management',
  direction: 'parent',
  relation_type: 'Management board',
  site_id: 'local',
  health: {
    state: 'UP',
    service_counts: { ok: 4, warn: 0, crit: 0, unknown: 0, pending: 0, total: 4 }
  }
}

test('summarizes the services of the host being shown', async () => {
  render(HostOverviewTab, { props: { data: makeData() } })

  // Only that the host's own counts reach the bar; what it makes of them is its own business.
  const bar = await screen.findByRole('img')
  expect(bar).toHaveAttribute('aria-label', '9 OK, 2 WARN, 3 CRIT, 1 UNKNOWN')
})

test('leads the counts of a relation to the related host, not to the one being shown', () => {
  render(HostOverviewTab, { props: { data: makeData({ relations: [RELATION] }) } })

  expect(screen.getByRole('link', { name: 'All services: 15' }).getAttribute('href')).toContain(
    'host=web-1'
  )
  expect(screen.getByRole('link', { name: 'OK: 4' }).getAttribute('href')).toContain(
    'host=mgmt-web-1'
  )
})
