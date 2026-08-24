/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import type { MonitoringAllHostsApp } from 'cmk-shared-typing/typescript/monitoring/all_hosts'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import AllHostsApp from '@/monitoring/all-hosts/AllHostsApp.vue'
import type { HostEntry } from '@/monitoring/shared/api/types'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

beforeEach(() => {
  document.body.innerHTML = '<div class="titlebar"></div>'
  postSpy = vi.spyOn(client, 'POST')
})

afterEach(() => {
  vi.restoreAllMocks()
  localStorage.clear()
  window.history.replaceState(null, '', '/monitor_all_hosts.py')
})

function makeHost(overrides: Partial<HostEntry> = {}): HostEntry {
  return {
    name: 'web-1',
    state: 'UP',
    site_id: 'local',
    address: '10.0.0.1',
    num_services: 1,
    num_services_ok: 1,
    num_services_warn: 0,
    num_services_crit: 0,
    num_services_unknown: 0,
    num_services_pending: 0,
    legacy_host_status_link: 'view.py?view_name=hoststatus&site=local&host=web-1',
    ...overrides
  }
}

function mockHosts(hosts: HostEntry[]): void {
  postSpy.mockResolvedValue({
    data: {
      hosts,
      meta: { limit: 1000, matched: hosts.length, total: hosts.length, fields: [] }
    },
    error: undefined,
    response: new Response()
  } as never)
}

function renderApp(edition: MonitoringAllHostsApp['edition']) {
  return render(AllHostsApp, {
    props: {
      user_id: 'cmkadmin',
      site: 'local',
      sites: [{ id: 'local', alias: 'Local site' }],
      edition
    } satisfies MonitoringAllHostsApp
  })
}

/**
 * The rows themselves are virtualised and never render under jsdom, so these assert what the
 * app asks the API for - which is where an edition-gated column can go wrong.
 */
test.each(['community', 'ultimatemt'] as const)(
  'asks only for the fields of its shown columns on %s',
  async (edition) => {
    mockHosts([makeHost()])
    renderApp(edition)

    await vi.waitUntil(() => postSpy.mock.calls.length > 0)

    expect(postSpy.mock.lastCall![0]).toBe('/monitor/hosts')
    expect(postSpy.mock.lastCall![1].body.fields).toEqual([
      'address',
      'num_services',
      'num_services_ok',
      'num_services_warn',
      'num_services_crit',
      'num_services_unknown',
      'num_services_pending'
    ])
  }
)

test('never asks for the customer, the API deriving it from the site', async () => {
  mockHosts([makeHost({ customer: 'Customer A' })])
  renderApp('ultimatemt')

  await vi.waitUntil(() => postSpy.mock.calls.length > 0)

  expect(postSpy.mock.lastCall![1].body.fields).not.toContain('customer')
})
