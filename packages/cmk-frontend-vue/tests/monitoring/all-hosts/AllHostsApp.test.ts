/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import type {
  MonitoringAction,
  MonitoringAllHostsApp
} from 'cmk-shared-typing/typescript/monitoring/all_hosts'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import AllHostsApp from '@/monitoring/all-hosts/AllHostsApp.vue'
import type { HostEntry } from '@/monitoring/shared/api/types'
import { ACTION_REFRESH_DELAY_MS } from '@/monitoring/shared/constants'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

beforeEach(() => {
  document.body.innerHTML = '<div class="titlebar"></div>'
  postSpy = vi.spyOn(client, 'POST')
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  localStorage.clear()
  window.history.replaceState(null, '', '/monitor_all_hosts.py')
})

function makeHost(overrides: Partial<HostEntry> = {}): HostEntry {
  return {
    name: 'web-1',
    state: 'UP',
    is_flapping: false,
    stale: false,
    site_id: 'local',
    address: '10.0.0.1',
    num_services: 1,
    num_services_ok: 1,
    num_services_warn: 0,
    num_services_crit: 0,
    num_services_unknown: 0,
    num_services_pending: 0,
    legacy_host_status_link: 'view.py?view_name=hoststatus&site=local&host=web-1',
    num_relations: 0,
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

function renderApp(
  edition: MonitoringAllHostsApp['edition'],
  overrides: Partial<MonitoringAllHostsApp> = {}
) {
  return render(AllHostsApp, {
    props: {
      user_id: 'cmkadmin',
      site: 'local',
      sites: [{ id: 'local', alias: 'Local site' }],
      edition,
      ...overrides
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

/*
 * The checkboxes are only worth showing where the selection can be acted on, so they follow the
 * permitted actions the page is handed - the same list the action bar follows.
 */

const ACKNOWLEDGE: MonitoringAction = {
  ident: 'acknowledge',
  title: 'Acknowledge problems',
  icon: 'acknowledge'
}

test('offers no row selection to a user permitted no action', async () => {
  mockHosts([makeHost()])
  renderApp('community', { actions: [] })
  await screen.findByRole('columnheader', { name: 'Host' })

  expect(screen.queryByRole('checkbox', { name: 'Select all rows' })).not.toBeInTheDocument()
  expect(
    screen.queryByRole('toolbar', { name: 'Actions for selected hosts' })
  ).not.toBeInTheDocument()
})

test('offers row selection once one action is permitted', async () => {
  mockHosts([makeHost()])
  renderApp('community', { actions: [ACKNOWLEDGE] })

  expect(await screen.findByRole('checkbox', { name: 'Select all rows' })).toBeInTheDocument()
  expect(screen.getByRole('toolbar', { name: 'Actions for selected hosts' })).toBeInTheDocument()
})

/*
 * What a command's outcome does to the listing. The refresh mechanism itself is covered on the
 * service; what is covered here is which outcome arms it.
 */

const RESCHEDULE: MonitoringAction = {
  ident: 'reschedule',
  title: 'Reschedule active checks',
  icon: 'reload'
}

const LISTING = '/monitor/hosts'
const RESCHEDULE_COMMAND = '/monitor/hosts/actions/reschedule'

/** Answers the two endpoints this flow touches; any other is a wiring mistake, not a test case. */
function mockBackend(commandFails: boolean): void {
  postSpy.mockImplementation((path: string) => {
    if (path === LISTING) {
      return Promise.resolve({
        data: {
          hosts: [makeHost()],
          meta: { limit: 1000, matched: 1, total: 1, fields: [] }
        },
        error: undefined,
        response: new Response()
      })
    }
    if (path === RESCHEDULE_COMMAND) {
      return commandFails
        ? Promise.resolve({
            data: undefined,
            error: {},
            response: new Response('', { status: 403, statusText: 'Forbidden' })
          })
        : Promise.resolve({
            data: { rescheduled: 1 },
            error: undefined,
            response: new Response()
          })
    }
    throw new Error(`unexpected POST to ${path}`)
  })
}

function listingReads(): number {
  return postSpy.mock.calls.filter(([path]: [string]) => path === LISTING).length
}

/*
 * Loads one host, selects it and runs the reschedule command on it. Reschedule is the one command
 * that runs on click, so this reaches an outcome without a form.
 *
 * The clock is faked to hold the deferred refresh still, which rules out every testing-library
 * waiter: they advance a faked clock themselves and would fire the very timer under test.
 */
async function rescheduleTheOnlyHost(commandFails: boolean): Promise<void> {
  vi.useFakeTimers()
  const user = userEvent.setup({ advanceTimers: (ms: number) => vi.advanceTimersByTime(ms) })
  mockBackend(commandFails)

  renderApp('community', { actions: [RESCHEDULE] })
  await vi.advanceTimersByTimeAsync(0)

  await user.click(screen.getByRole('checkbox', { name: 'Select all rows' }))
  await user.click(screen.getByRole('button', { name: RESCHEDULE.title }))
  await vi.advanceTimersByTimeAsync(0)
}

test('re-reads the listing a moment after a command the site accepted', async () => {
  await rescheduleTheOnlyHost(false)

  expect(screen.getByText('Rescheduled 1 check')).toBeInTheDocument()
  expect(listingReads()).toBe(1)

  await vi.advanceTimersByTimeAsync(ACTION_REFRESH_DELAY_MS)

  expect(listingReads()).toBe(2)
})

test('leaves the listing alone after a command the site refused', async () => {
  await rescheduleTheOnlyHost(true)

  expect(
    screen.getByText('Could not reschedule the checks for the selected hosts')
  ).toBeInTheDocument()

  await vi.advanceTimersByTimeAsync(ACTION_REFRESH_DELAY_MS)

  expect(listingReads()).toBe(1)
})
