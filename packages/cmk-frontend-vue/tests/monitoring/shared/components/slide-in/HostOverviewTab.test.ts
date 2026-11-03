/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'

import type { HostOverview } from '@/monitoring/shared/api/types'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import HostOverviewTab from '@/monitoring/shared/components/slide-in/HostOverviewTab.vue'
import { labelCondition } from '@/monitoring/shared/labels'
import type { DisplayOptions } from '@/monitoring/shared/types'

import { makeListingService } from '../../../shared/services/testHelpers'

const DISPLAY_OPTIONS: DisplayOptions = { dateFormat: '%Y-%m-%d', timestampFormat: 'abs' }

function makeData(overrides: Partial<HostOverview> = {}): HostOverview {
  return {
    name: 'web-1',
    alias: 'web server 1',
    address: '10.0.0.1',
    state: 'UP',
    is_flapping: false,
    stale: false,
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
    setup_access: false,
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
  render(HostOverviewTab, { props: { data: makeData(), displayOptions: DISPLAY_OPTIONS } })

  // Only that the host's own counts reach the bar; what it makes of them is its own business.
  const bar = await screen.findByRole('img')
  expect(bar).toHaveAttribute('aria-label', '9 OK, 2 WARN, 3 CRIT, 1 UNKNOWN')
})

test('puts the service summary before the details of the host', async () => {
  render(HostOverviewTab, { props: { data: makeData(), displayOptions: DISPLAY_OPTIONS } })

  const bar = await screen.findByRole('img')
  expect(bar.compareDocumentPosition(screen.getByText('Host name'))).toBe(
    Node.DOCUMENT_POSITION_FOLLOWING
  )
})

test('puts the link to all services beside the service summary heading', async () => {
  render(HostOverviewTab, { props: { data: makeData(), displayOptions: DISPLAY_OPTIONS } })

  const heading = await screen.findByRole('heading', { name: 'Service summary' })
  expect(heading.parentElement).toBe(
    screen.getByRole('link', { name: 'All services: 15' }).parentElement
  )
})

test('leads the counts of a relation to the related host, not to the one being shown', () => {
  render(HostOverviewTab, {
    props: { data: makeData({ relations: [RELATION] }), displayOptions: DISPLAY_OPTIONS }
  })

  expect(screen.getByRole('link', { name: 'All services: 15' }).getAttribute('href')).toContain(
    'host=web-1'
  )
  expect(screen.getByRole('link', { name: 'OK: 4' }).getAttribute('href')).toContain(
    'host=mgmt-web-1'
  )
})

test('names the timestamps as ages even when they show a point in time', () => {
  render(HostOverviewTab, { props: { data: makeData(), displayOptions: DISPLAY_OPTIONS } })

  expect(screen.getByText('Check age')).toHaveAttribute('title', 'Age of the check')
  expect(screen.getByText('State age')).toHaveAttribute('title', 'Age of the state')
})

test('dashes out the timestamps of a host that has never been checked', () => {
  render(HostOverviewTab, {
    props: {
      data: makeData({ last_check: null, last_state_change: null }),
      displayOptions: DISPLAY_OPTIONS
    }
  })

  expect(screen.getAllByText('–')).toHaveLength(2)
})

test('narrows the listing of hosts to the ones carrying a label clicked on', async () => {
  const service = makeListingService()
  render(HostOverviewTab, {
    props: { data: makeData(), displayOptions: DISPLAY_OPTIONS, filterLabelsBy: labelCondition },
    global: { provide: { [MONITORING_SERVICE as symbol]: service } }
  })

  await userEvent.click(screen.getByRole('button', { name: 'cmk/os_family: linux' }))

  expect(service.filterState.value).toStrictEqual({
    type: 'condition',
    field: 'labels',
    op: 'all_of',
    value: ['cmk/os_family:linux']
  })
})

test('keeps the labels plain where the listing behind the panel holds no hosts', () => {
  render(HostOverviewTab, {
    props: { data: makeData(), displayOptions: DISPLAY_OPTIONS },
    global: { provide: { [MONITORING_SERVICE as symbol]: makeListingService() } }
  })

  expect(screen.queryByRole('button', { name: 'cmk/os_family: linux' })).not.toBeInTheDocument()
})
