/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
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
  document.body.innerHTML = '<div class="titlebar"><div class="titlebar-main"></div></div>'
  postSpy = vi.spyOn(client, 'POST')
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
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

function mockHosts(hosts: HostEntry[], matched: number = hosts.length): void {
  postSpy.mockResolvedValue({
    data: {
      hosts,
      meta: { limit: 1000, matched, total: matched, fields: [] }
    },
    error: undefined,
    response: new Response()
  } as never)
}

const EXPORT_EVENT = 'cmk-monitoring-export'

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
      limit_tiers: [1000, 5000],
      export_event: EXPORT_EVENT,
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

test('shows the listing as sorted by host name ascending before the user sorts', async () => {
  mockHosts([makeHost()])
  renderApp('community')

  expect(await screen.findByRole('columnheader', { name: 'Host' })).toHaveAttribute(
    'aria-sort',
    'ascending'
  )
})

test('asks for the hosts sorted by host name ascending before the user sorts', async () => {
  mockHosts([makeHost()])
  renderApp('community')

  await vi.waitUntil(() => postSpy.mock.calls.length > 0)

  expect(postSpy.mock.lastCall![1].body.sort).toEqual(['name:asc'])
})

test('extends the default sort by the State column when it is shift-clicked', async () => {
  const user = userEvent.setup()
  mockHosts([makeHost()])
  renderApp('community')
  const stateHeader = await screen.findByRole('button', { name: 'State' })

  await user.keyboard('{Shift>}')
  await user.click(stateHeader)
  await user.keyboard('{/Shift}')

  expect(postSpy.mock.lastCall![1].body.sort).toEqual(['name:asc', 'state:desc'])
})

const UNHANDLED_PROBLEMS_FILTER = {
  type: 'and',
  children: [
    { type: 'condition', field: 'state', op: 'one_of', value: ['DOWN', 'UNREACHABLE'] },
    { type: 'condition', field: 'acknowledged', op: 'eq', value: false },
    { type: 'condition', field: 'in_downtime', op: 'eq', value: false }
  ]
}

function openWithFilter(filter: object): void {
  window.history.replaceState(
    null,
    '',
    `/monitor_all_hosts.py?filter=${encodeURIComponent(JSON.stringify(filter))}`
  )
}

test('asks for the hosts a link arrived filtered to with its one and only first request', async () => {
  openWithFilter(UNHANDLED_PROBLEMS_FILTER)
  mockHosts([makeHost()])
  renderApp('community')

  await screen.findByText('Total rows: 1')

  expect(postSpy).toHaveBeenCalledTimes(1)
  expect(postSpy.mock.lastCall![1].body.filter).toEqual(UNHANDLED_PROBLEMS_FILTER)
})

test('shows the unhandled-problems chip as active when a link arrived with its filter', async () => {
  openWithFilter(UNHANDLED_PROBLEMS_FILTER)
  mockHosts([makeHost()])
  renderApp('community')

  expect(await screen.findByRole('button', { name: 'Unhandled host problems' })).toHaveAttribute(
    'aria-pressed',
    'true'
  )
})

test('resetting all filters drops the filter a link arrived with', async () => {
  openWithFilter(UNHANDLED_PROBLEMS_FILTER)
  mockHosts([makeHost()])
  renderApp('community')

  await userEvent.click(await screen.findByRole('button', { name: 'Reset search and filters' }))

  expect(postSpy.mock.lastCall![1].body.filter).toBeUndefined()
})

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

test('offers row selection and the "More" menu for a command found only there', async () => {
  mockHosts([makeHost()])
  renderApp('community', {
    actions: [
      { ident: 'fake_check_result', title: 'Fake check results', icon: 'fake-check-result' }
    ]
  })

  expect(await screen.findByRole('checkbox', { name: 'Select all rows' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'More' })).toBeInTheDocument()
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

test('typing letters focuses the first host name containing them', async () => {
  // The rows only render once the virtualiser sees a viewport.
  const offsetHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight')
  const offsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth')
  Object.defineProperty(HTMLElement.prototype, 'offsetHeight', { configurable: true, value: 600 })
  Object.defineProperty(HTMLElement.prototype, 'offsetWidth', { configurable: true, value: 800 })
  try {
    mockHosts([makeHost({ name: 'dbnode' }), makeHost({ name: 'cpunode' })])
    renderApp('community')
    const target = await screen.findByRole('button', { name: 'cpunode' })

    await userEvent.keyboard('cpu')

    expect(target).toHaveFocus()
    expect(screen.getByRole('status')).toHaveTextContent('cpu')
  } finally {
    if (offsetHeight) {
      Object.defineProperty(HTMLElement.prototype, 'offsetHeight', offsetHeight)
    }
    if (offsetWidth) {
      Object.defineProperty(HTMLElement.prototype, 'offsetWidth', offsetWidth)
    }
  }
})

/*
 * The Export CSV entry lives in the legacy page menu, which reaches the app through a document
 * event. jsdom has no object URLs and does not download, so the test records the file name the
 * download link was clicked with.
 */

let downloads: string[]

function stubDownloads(): void {
  downloads = []
  URL.createObjectURL = vi.fn(() => 'blob:hosts')
  URL.revokeObjectURL = vi.fn()
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
    this: HTMLAnchorElement
  ) {
    downloads.push(this.download)
  })
}

async function exportCsv(): Promise<void> {
  await screen.findByRole('columnheader', { name: 'Host' })
  await vi.waitUntil(() => postSpy.mock.calls.length > 0)
  document.dispatchEvent(new CustomEvent(EXPORT_EVENT, { detail: 'csv' }))
}

test('says how many hosts were exported when the row limit left some out', async () => {
  const user = userEvent.setup()
  stubDownloads()
  mockHosts([makeHost(), makeHost({ name: 'web-2' })], 3)
  renderApp('community')

  await exportCsv()

  expect(
    await screen.findByText('Exported 2 of 3 hosts. Show more hosts to export more.')
  ).toBeInTheDocument()
  expect(downloads).toEqual([expect.stringMatching(/^all_hosts-.*\.csv$/)])

  await user.click(screen.getByRole('button', { name: 'Dismiss' }))

  expect(screen.queryByText(/^Exported/)).not.toBeInTheDocument()
})

test('suggests narrowing the filters when no higher row limit is left', async () => {
  stubDownloads()
  mockHosts([makeHost(), makeHost({ name: 'web-2' })], 3)
  renderApp('community', { limit_tiers: [1000] })

  await exportCsv()

  expect(
    await screen.findByText('Exported 2 of 3 hosts. Narrow the filters to export all of them.')
  ).toBeInTheDocument()
})

test('exports without a note when every matching host is loaded', async () => {
  stubDownloads()
  mockHosts([makeHost(), makeHost({ name: 'web-2' })])
  renderApp('community')

  await exportCsv()
  await vi.waitUntil(() => downloads.length > 0)

  expect(screen.queryByText(/^Exported/)).not.toBeInTheDocument()
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})

test('exports nothing and says so when the hosts could not be loaded', async () => {
  const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
  stubDownloads()
  postSpy.mockResolvedValue({
    data: undefined,
    error: {},
    response: new Response('', { status: 500, statusText: 'Internal Server Error' })
  } as never)
  renderApp('community')

  await exportCsv()

  expect(
    await screen.findByText('The hosts could not be loaded, so nothing was exported.')
  ).toBeInTheDocument()
  expect(downloads).toEqual([])
  expect(consoleError).toHaveBeenCalled()
})

test('posts the shown columns and the listing to the instant PDF report', async () => {
  const posted: Record<string, string>[] = []
  vi.spyOn(HTMLFormElement.prototype, 'submit').mockImplementation(function (
    this: HTMLFormElement
  ) {
    expect(this.getAttribute('action')).toBe('report_instant_all_hosts.py')
    posted.push(
      Object.fromEntries(
        [...new FormData(this).entries()].map(([key, value]) => [key, String(value)])
      )
    )
  })
  window.history.replaceState(null, '', '/monitor_all_hosts.py?cols=address')
  mockHosts([makeHost()])
  renderApp('pro')
  await screen.findByRole('columnheader', { name: 'Host' })
  await vi.waitUntil(() => postSpy.mock.calls.length > 0)

  document.dispatchEvent(new CustomEvent(EXPORT_EVENT, { detail: 'pdf' }))

  expect(posted[0]!.cols).toBe('state,modes,name,address')
  expect(JSON.parse(posted[0]!.body!)).toMatchObject({ sort: ['name:asc'] })
})

test('adds a comment to the selected host from the "More" menu', async () => {
  const user = userEvent.setup()
  mockHosts([makeHost()])
  renderApp('community', {
    actions: [{ ident: 'add_comment', title: 'Add comment', icon: 'comment' }]
  })

  await user.click(await screen.findByRole('checkbox', { name: 'Select all rows' }))
  await user.click(screen.getByRole('button', { name: 'More' }))
  await user.click(await screen.findByRole('menuitem', { name: 'Add comment' }))
  // The closing menu hands the focus back to its button first.
  await waitFor(() => expect(screen.getByRole('button', { name: 'More' })).toHaveFocus())
  // jsdom gives every element an empty box, which the split pane's resize handle takes as a hit,
  // swallowing the click that would focus the field.
  screen.getByPlaceholderText('Enter a comment…').focus()
  await user.keyboard('Disk swap planned')
  await user.click(screen.getByRole('button', { name: 'Add comment' }))

  expect(await screen.findByText('Added comment to the selected host')).toBeInTheDocument()
  expect(postSpy).toHaveBeenCalledWith(
    '/domain-types/comment/collections/host',
    expect.objectContaining({ body: expect.objectContaining({ comment: 'Disk swap planned' }) })
  )
})

const ACKNOWLEDGED = {
  id: 'acknowledged' as const,
  icon_name: 'ack',
  link: '',
  title: 'Acknowledged'
}

test('removes the acknowledgement of the selected host after confirming it', async () => {
  const user = userEvent.setup()
  mockHosts([makeHost({ modes: [ACKNOWLEDGED] }), makeHost({ name: 'web-2' })])
  renderApp('community', {
    actions: [{ ident: 'remove_acknowledgments', title: 'Remove acknowledgements', icon: 'ack' }]
  })

  await user.click(await screen.findByRole('checkbox', { name: 'Select all rows' }))
  await user.click(screen.getByRole('button', { name: 'More' }))
  await user.click(await screen.findByRole('menuitem', { name: 'Remove acknowledgements' }))

  const alert = await screen.findByRole('alert')
  expect(alert).toHaveTextContent('Selected hosts: 2 | Total hosts: 2')
  expect(alert).toHaveTextContent('Acknowledgements: 1')
  await user.click(screen.getByRole('button', { name: 'Remove acknowledgements' }))

  expect(
    await screen.findByText('Removed acknowledgement of the selected host')
  ).toBeInTheDocument()
  expect(postSpy).toHaveBeenCalledWith(
    '/domain-types/acknowledge/actions/delete/invoke',
    expect.objectContaining({
      body: expect.objectContaining({
        query: { op: 'or', expr: [{ op: '=', left: 'name', right: 'web-1' }] }
      })
    })
  )
})

test('cancelling the confirmation removes nothing', async () => {
  const user = userEvent.setup()
  mockHosts([makeHost({ modes: [ACKNOWLEDGED] })])
  renderApp('community', {
    actions: [{ ident: 'remove_acknowledgments', title: 'Remove acknowledgements', icon: 'ack' }]
  })

  await user.click(await screen.findByRole('checkbox', { name: 'Select all rows' }))
  await user.click(screen.getByRole('button', { name: 'More' }))
  await user.click(await screen.findByRole('menuitem', { name: 'Remove acknowledgements' }))
  await user.click(await screen.findByRole('button', { name: 'Cancel' }))

  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  expect(postSpy).not.toHaveBeenCalledWith(
    '/domain-types/acknowledge/actions/delete/invoke',
    expect.anything()
  )
})
