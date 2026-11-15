/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, within } from '@testing-library/vue'
import type { MonitoringAllServicesApp } from 'cmk-shared-typing/typescript/monitoring/all_services'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import AllServicesApp from '@/monitoring/all-services/AllServicesApp.vue'
import type { HostEntry } from '@/monitoring/shared/api/types'

import { pastDoubleClick, userOnFakeClock } from '../shared/deferredClick'
import { layOutThePage } from '../shared/layOutThePage'
import { columnIdsUnderHeaders } from '../shared/rowLayout'

type MonitoringAction = NonNullable<MonitoringAllServicesApp['actions']>[number]

type ApiServiceEntry = components['schemas']['ServiceEntry']

const SERVICES_PATH = '/monitor/services'
const EXPORT_EVENT = 'cmk-monitoring-export'
const ACTION_MENU_PATH = '/monitor/hosts/{hostname}/service/action_menu'
const OVERVIEW_PATH = '/monitor/hosts/{hostname}/service'
const RESCHEDULE_PATH = '/monitor/services/actions/reschedule'
const DISCOVER_GRAPHS_PATH = '/domain-types/graph/actions/discover_template_graphs/invoke'

const RESCHEDULE: MonitoringAction = {
  ident: 'reschedule',
  title: 'Reschedule active checks',
  icon: 'reload'
}

const SAME_NAMED_SERVICES_ON_TWO_HOSTS = (): ApiServiceEntry[] => [
  makeApiEntry({ host_name: 'web-1', site_id: 'local' }),
  makeApiEntry({ host_name: 'web-2', site_id: 'remote' })
]

vi.setConfig({ testTimeout: 20_000 })

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let servicesPost: any
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let getSpy: any

beforeEach(() => {
  document.body.innerHTML =
    '<div class="titlebar"><div class="titlebar-main"></div></div><div id="content_area"></div>'
  getSpy = vi
    .spyOn(client, 'GET')
    .mockImplementation(((path: string) =>
      path === ACTION_MENU_PATH
        ? Promise.resolve({ data: { items: [] }, error: undefined, response: new Response() })
        : new Promise(() => {})) as never)
  postSpy = vi.spyOn(client, 'POST')
  servicesPost = vi.fn()
})

afterEach(() => {
  localStorage.clear()
  window.history.replaceState(null, '', '/monitor_all_services.py')
  vi.restoreAllMocks()
})

function mockServices(services: ApiServiceEntry[]): void {
  postSpy.mockImplementation((path: string, init: unknown) => {
    servicesPost(path, init)
    if (path === DISCOVER_GRAPHS_PATH) {
      return Promise.resolve({
        data: { graphs: [], no_data_message: null },
        error: undefined,
        response: new Response()
      }) as never
    }
    return Promise.resolve({
      data: {
        services,
        meta: { limit: 1000, matched: services.length, total: services.length }
      },
      error: undefined,
      response: new Response()
    }) as never
  })
}

function makeApiEntry(overrides: Partial<ApiServiceEntry> = {}): ApiServiceEntry {
  return {
    name: 'CPU load',
    host_name: 'web-2',
    site_id: 'remote',
    host_state: 'UP',
    state: 'OK',
    is_flapping: false,
    stale: false,
    summary: 'OK - 15 min load: 0.5',
    last_check: 1783942710,
    last_state_change: 1783942740,
    ...overrides
  }
}

function renderApp(overrides: Partial<MonitoringAllServicesApp> = {}) {
  return render(AllServicesApp, {
    props: {
      user_id: 'cmkadmin',
      site: 'local',
      sites: [
        { id: 'local', alias: 'Local site' },
        { id: 'remote', alias: 'Remote site' }
      ],
      edition: 'pro',
      limit_tiers: [1000, 5000],
      unapplied_filters: [],
      export_event: EXPORT_EVENT,
      ...overrides
    } satisfies MonitoringAllServicesApp
  })
}

test('lists the services sorted by site, host and service by default with a remote site', async () => {
  mockServices([makeApiEntry()])
  renderApp()

  await vi.waitUntil(() => servicesPost.mock.calls.length > 0)

  expect(servicesPost).toHaveBeenLastCalledWith(
    SERVICES_PATH,
    expect.objectContaining({
      body: {
        limit: 1000,
        sort: ['site_id:asc', 'host_name:asc', 'name:asc'],
        fields: ['graphs_link', 'custom_icons']
      }
    })
  )
})

test('shows the site of each service by default when there is a remote site', async () => {
  mockServices([makeApiEntry()])
  renderApp()

  expect(await screen.findByRole('columnheader', { name: 'Site' })).toBeInTheDocument()
})

test('hides the state age, check age and Perf-O-Meter columns by default', async () => {
  mockServices([makeApiEntry()])
  renderApp()

  expect(await screen.findByRole('columnheader', { name: 'Summary' })).toBeInTheDocument()
  for (const name of ['State age', 'Check age', 'Perf-O-Meter']) {
    expect(screen.queryByRole('columnheader', { name })).not.toBeInTheDocument()
  }
})

test('hides the site column by default without a remote site', async () => {
  mockServices([makeApiEntry()])
  renderApp({ sites: [{ id: 'local', alias: 'Local site' }] })

  expect(await screen.findByRole('columnheader', { name: 'Host' })).toBeInTheDocument()
  expect(screen.queryByRole('columnheader', { name: 'Site' })).not.toBeInTheDocument()
})

test('lists the services sorted by host and service by default without a remote site', async () => {
  mockServices([makeApiEntry()])
  renderApp({ sites: [{ id: 'local', alias: 'Local site' }] })

  await vi.waitUntil(() => servicesPost.mock.calls.length > 0)

  expect(servicesPost).toHaveBeenLastCalledWith(
    SERVICES_PATH,
    expect.objectContaining({
      body: expect.objectContaining({ sort: ['host_name:asc', 'name:asc'] })
    })
  )
})

test('numbers the sort of the host first and the service second without a remote site', async () => {
  mockServices([makeApiEntry()])
  renderApp({ sites: [{ id: 'local', alias: 'Local site' }] })

  const hostHeader = await screen.findByRole('columnheader', { name: 'Host' })

  expect(within(hostHeader).getByText('1')).toBeInTheDocument()
  expect(
    within(screen.getByRole('columnheader', { name: 'Service' })).getByText('2')
  ).toBeInTheDocument()
})

test('requests the services by host name alone on a click of the Host header', async () => {
  mockServices([makeApiEntry()])
  renderApp()
  await screen.findByRole('button', { name: 'Host' })

  await userEvent.click(screen.getByRole('button', { name: 'Host' }))

  expect(servicesPost).toHaveBeenLastCalledWith(
    SERVICES_PATH,
    expect.objectContaining({
      body: { limit: 1000, sort: ['host_name:asc'], fields: ['graphs_link', 'custom_icons'] }
    })
  )
})

test('opens the slide-in of a service a link names by its site, host and name', async () => {
  window.history.replaceState(
    null,
    '',
    '/monitor_all_services.py#host=web-2&site=remote&service=CPU+load'
  )
  mockServices([makeApiEntry()])
  renderApp()

  expect(await screen.findByText('Service details')).toBeInTheDocument()
})

describe('with the rows laid out', () => {
  layOutThePage({ slideIns: false })

  test('puts the cells of a row in the position of their column headers', async () => {
    mockServices([makeApiEntry()])
    renderApp()
    await screen.findByText('web-2')

    expect(columnIdsUnderHeaders(['Service', 'Summary', 'Host', 'Site'])).toEqual({
      Service: 'name',
      Summary: 'summary',
      Host: 'host_name',
      Site: 'site_id'
    })
  })

  function requestedFor(path: string, hostName: string, siteId: string): boolean {
    return getSpy.mock.calls.some(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ([calledPath, init]: [string, any]) =>
        calledPath === path &&
        init.params.path.hostname === hostName &&
        init.params.query.site_id === siteId
    )
  }

  test('reschedules the service of a row on its own host and site', async () => {
    mockServices(
      SAME_NAMED_SERVICES_ON_TWO_HOSTS().map((service) => ({
        ...service,
        reschedule: {
          label: 'Reschedule check',
          tooltip: 'Reschedule check',
          icon_name: 'reload',
          target: service.name
        }
      }))
    )
    renderApp({ actions: [RESCHEDULE] })

    const menus = await screen.findAllByRole('button', { name: 'More actions' })
    await userEvent.click(menus[1]!)
    await userEvent.click(await screen.findByRole('menuitem', { name: /Reschedule check/ }))

    expect(servicesPost).toHaveBeenCalledWith(
      '/monitor/services/actions/reschedule',
      expect.objectContaining({
        body: expect.objectContaining({
          services: [{ site_id: 'remote', host_name: 'web-2', name: 'CPU load' }]
        })
      })
    )
  })

  test('reschedules the "Check_MK" service of a host once while it runs, whichever row picks it', async () => {
    const byCheckMk = {
      label: 'Reschedule "Check_MK" service',
      tooltip: 'Reschedule "Check_MK" service',
      icon_name: 'reload',
      target: 'Check_MK'
    }
    mockServices([
      makeApiEntry({
        name: 'CPU load',
        host_name: 'web-1',
        site_id: 'local',
        reschedule: byCheckMk
      }),
      makeApiEntry({ name: 'Memory', host_name: 'web-1', site_id: 'local', reschedule: byCheckMk })
    ])
    // The first reschedule is still sent off when the second row picks it.
    const listServices = postSpy.getMockImplementation()
    postSpy.mockImplementation((path: string, init: unknown) => {
      if (path !== RESCHEDULE_PATH) {
        return listServices(path, init)
      }
      servicesPost(path, init)
      return new Promise(() => {})
    })
    renderApp({ actions: [RESCHEDULE] })
    const menus = await screen.findAllByRole('button', { name: 'More actions' })

    for (const menu of menus) {
      await userEvent.click(menu)
      await userEvent.click(await screen.findByRole('menuitem', { name: /Reschedule/ }))
    }

    expect(
      await screen.findAllByText('Waiting for the "Check_MK" service of web-1 to finish')
    ).toHaveLength(1)
    expect(
      servicesPost.mock.calls.filter(([path]: [string]) => path === RESCHEDULE_PATH)
    ).toHaveLength(1)
  })

  test('loads the action menu of a row from its own host and site', async () => {
    mockServices(SAME_NAMED_SERVICES_ON_TWO_HOSTS())
    renderApp()

    const menus = await screen.findAllByRole('button', { name: 'More actions' })
    await userEvent.click(menus[1]!)

    await vi.waitUntil(() => requestedFor(ACTION_MENU_PATH, 'web-2', 'remote'))
    expect(requestedFor(ACTION_MENU_PATH, 'web-1', 'local')).toBe(false)
  })

  test('asks the action menu of a row for the links into Setup', async () => {
    mockServices(SAME_NAMED_SERVICES_ON_TWO_HOSTS())
    renderApp()

    const menus = await screen.findAllByRole('button', { name: 'More actions' })
    await userEvent.click(menus[0]!)

    await vi.waitUntil(() =>
      getSpy.mock.calls.some(
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        ([calledPath, init]: [string, any]) =>
          calledPath === ACTION_MENU_PATH && init.params.query.include_setup_links === 'true'
      )
    )
  })

  test('loads the slide-in of a row from its own host and site', async () => {
    mockServices(SAME_NAMED_SERVICES_ON_TWO_HOSTS())
    renderApp()

    const names = await screen.findAllByRole('button', { name: 'CPU load' })
    await userEvent.click(names[1]!)

    await vi.waitUntil(() => requestedFor(OVERVIEW_PATH, 'web-2', 'remote'))
    expect(requestedFor(OVERVIEW_PATH, 'web-1', 'local')).toBe(false)
  })

  test('opens the slide-in of a row clicked outside its name', async () => {
    mockServices([
      makeApiEntry({ host_name: 'web-1', site_id: 'local', summary: 'first summary' }),
      makeApiEntry({ host_name: 'web-2', site_id: 'remote', summary: 'second summary' })
    ])
    const user = userOnFakeClock()
    renderApp()

    await user.click(await screen.findByText('second summary'))
    await pastDoubleClick()

    await vi.waitUntil(() => requestedFor(OVERVIEW_PATH, 'web-2', 'remote'))
    expect(requestedFor(OVERVIEW_PATH, 'web-1', 'local')).toBe(false)
  })

  function graphsDiscoveredFor(hostName: string, siteId: string): boolean {
    return servicesPost.mock.calls.some(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ([calledPath, init]: [string, any]) =>
        calledPath === DISCOVER_GRAPHS_PATH &&
        init.body.hostname === hostName &&
        init.body.site === siteId
    )
  }

  test('previews the graphs of a row from its own host and site', async () => {
    mockServices(
      SAME_NAMED_SERVICES_ON_TWO_HOSTS().map((service) => ({ ...service, graphs_link: 'view.py' }))
    )
    renderApp()

    const links = await screen.findAllByRole('link', {
      name: 'Show the graphs of service CPU load'
    })
    await userEvent.hover(links[1]!)

    await vi.waitUntil(() => graphsDiscoveredFor('web-2', 'remote'))
    expect(graphsDiscoveredFor('web-1', 'local')).toBe(false)
  })

  test('reloads the slide-in for a service of the same name on another host', async () => {
    mockServices(SAME_NAMED_SERVICES_ON_TWO_HOSTS())
    renderApp()

    const names = await screen.findAllByRole('button', { name: 'CPU load' })
    await userEvent.click(names[0]!)
    await vi.waitUntil(() => requestedFor(OVERVIEW_PATH, 'web-1', 'local'))
    await userEvent.click(names[1]!)

    await vi.waitUntil(() => requestedFor(OVERVIEW_PATH, 'web-2', 'remote'))
  })

  test('names the service it opens by its site, host and name in the URL fragment', async () => {
    mockServices([makeApiEntry()])
    renderApp()

    await userEvent.click(await screen.findByRole('button', { name: 'CPU load' }))

    const fragment = new URLSearchParams(window.location.hash.slice(1))
    expect([fragment.get('host'), fragment.get('site'), fragment.get('service')]).toEqual([
      'web-2',
      'remote',
      'CPU load'
    ])
  })

  const HOST: HostEntry = {
    name: 'web-2',
    state: 'DOWN',
    is_flapping: false,
    stale: false,
    site_id: 'remote',
    address: '10.0.0.2',
    num_services: 1,
    num_services_ok: 1,
    num_services_warn: 0,
    num_services_crit: 0,
    num_services_unknown: 0,
    num_services_pending: 0,
    legacy_host_status_link: 'view.py?view_name=hoststatus&site=remote&host=web-2',
    num_relations: 0
  }

  function mockServicesAndHost(): ReturnType<typeof vi.fn> {
    const hostsPost = vi.fn()
    postSpy.mockImplementation((path: string, init: unknown) => {
      if (path === '/monitor/hosts') {
        hostsPost(init)
        return Promise.resolve({
          data: { hosts: [HOST], meta: { limit: 1, matched: 1, total: 1, fields: [] } },
          error: undefined,
          response: new Response()
        }) as never
      }
      return Promise.resolve({
        data: {
          services: [makeApiEntry({ host_name: 'web-2', site_id: 'remote' })],
          meta: { limit: 1000, matched: 1, total: 1 }
        },
        error: undefined,
        response: new Response()
      }) as never
    })
    return hostsPost
  }

  test('opens the host slide-in of the row without fetching the host again', async () => {
    const hostsPost = mockServicesAndHost()
    renderApp({
      host_actions: [{ ident: 'reschedule', title: 'Reschedule host check', icon: 'reload' }]
    })

    await userEvent.click(await screen.findByText('web-2'))

    expect(await screen.findByRole('button', { name: 'Reschedule host check' })).toBeInTheDocument()
    expect(hostsPost).not.toHaveBeenCalled()
  })

  test('opens the host slide-in for a click on the host cell, not the service one', async () => {
    mockServicesAndHost()
    const user = userOnFakeClock()
    renderApp()

    await user.click(await screen.findByText('web-2'))
    await pastDoubleClick()

    expect(await screen.findByText('Host details')).toBeInTheDocument()
    expect(requestedFor(OVERVIEW_PATH, 'web-2', 'remote')).toBe(false)
  })

  test('names the host it shows in the URL fragment apart from a service', async () => {
    mockServicesAndHost()
    renderApp()

    await userEvent.click(await screen.findByText('web-2'))
    await screen.findByText('Host details')

    const fragment = new URLSearchParams(window.location.hash.slice(1))
    expect([fragment.get('slide_in_host'), fragment.get('slide_in_site')]).toEqual([
      'web-2',
      'remote'
    ])
    expect(fragment.has('host')).toBe(false)
  })

  test('opens the host slide-in from a link naming its host', async () => {
    window.history.replaceState(
      null,
      '',
      '/monitor_all_services.py#slide_in_host=web-2&slide_in_site=remote'
    )
    const hostsPost = mockServicesAndHost()
    renderApp()

    expect(await screen.findByText('Host details')).toBeInTheDocument()
    expect(hostsPost).not.toHaveBeenCalled()
  })
})

const UNAPPLIED_FILTERS = [{ id: 'hostalias', title: 'Host alias' }]

test('names the filters of the classic view it was opened from that it does not apply', async () => {
  mockServices([makeApiEntry()])
  renderApp({ unapplied_filters: UNAPPLIED_FILTERS })

  expect(await screen.findByText('Some filters not supported yet: Host alias')).toBeVisible()
})

test('names the unapplied filters next to the filter it applies from the classic view', async () => {
  const filter = { type: 'condition', field: 'host_name', op: 'contains', value: 'web' }
  window.history.replaceState(
    null,
    '',
    `/monitor_all_services.py?filter=${encodeURIComponent(JSON.stringify(filter))}&unapplied=hostalias`
  )
  mockServices([makeApiEntry()])
  renderApp({ unapplied_filters: UNAPPLIED_FILTERS })

  await vi.waitUntil(() =>
    servicesPost.mock.calls.some(
      ([path, init]: [string, { body: { filter?: unknown } }]) =>
        path === SERVICES_PATH && JSON.stringify(init.body.filter) === JSON.stringify(filter)
    )
  )

  expect(await screen.findByText('Some filters not supported yet: Host alias')).toBeVisible()
})

test('drops the unapplied filters from the address bar', async () => {
  window.history.replaceState(null, '', '/monitor_all_services.py?unapplied=hostalias')
  mockServices([makeApiEntry()])
  renderApp({ unapplied_filters: UNAPPLIED_FILTERS })

  await screen.findByText('Some filters not supported yet: Host alias')

  await vi.waitFor(() =>
    expect(new URLSearchParams(window.location.search).has('unapplied')).toBe(false)
  )
})

test('keeps naming the unapplied filters when the user searches', async () => {
  mockServices([makeApiEntry()])
  renderApp({ unapplied_filters: UNAPPLIED_FILTERS })
  await screen.findByText('Some filters not supported yet: Host alias')

  const search = screen.getByRole('searchbox')
  await fireEvent.update(search, 'cpu')
  await fireEvent.keyDown(search, { key: 'Enter' })
  await vi.waitUntil(() =>
    servicesPost.mock.calls.some(
      ([path, init]: [string, { body: { q?: string } }]) =>
        path === SERVICES_PATH && init.body.q === 'cpu'
    )
  )

  expect(screen.getByText('Some filters not supported yet: Host alias')).toBeVisible()
})

describe('export', () => {
  let downloads: string[]

  beforeEach(() => {
    downloads = []
    URL.createObjectURL = vi.fn(() => 'blob:services')
    URL.revokeObjectURL = vi.fn()
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
      this: HTMLAnchorElement
    ) {
      downloads.push(this.download)
    })
  })

  test('downloads the services of all hosts', async () => {
    mockServices([makeApiEntry()])
    renderApp()
    await screen.findByRole('columnheader', { name: 'Service' })
    await vi.waitUntil(() => servicesPost.mock.calls.length > 0)

    document.dispatchEvent(new CustomEvent(EXPORT_EVENT, { detail: 'csv' }))
    await vi.waitUntil(() => downloads.length > 0)

    expect(downloads[0]).toMatch(/^all-services-.*\.csv$/)
  })
})
