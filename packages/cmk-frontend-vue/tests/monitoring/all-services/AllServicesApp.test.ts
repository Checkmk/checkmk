/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import type { MonitoringAllServicesApp } from 'cmk-shared-typing/typescript/monitoring/all_services'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import AllServicesApp from '@/monitoring/all-services/AllServicesApp.vue'

type MonitoringAction = NonNullable<MonitoringAllServicesApp['actions']>[number]

type ApiServiceEntry = components['schemas']['ServiceEntry']

const SERVICES_PATH = '/monitor/services'
const EXPORT_EVENT = 'cmk-monitoring-export'
const ACTION_MENU_PATH = '/monitor/hosts/{hostname}/service/action_menu'
const OVERVIEW_PATH = '/monitor/hosts/{hostname}/service'

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
      export_event: EXPORT_EVENT,
      ...overrides
    } satisfies MonitoringAllServicesApp
  })
}

test('lists the services of every host from the all services endpoint', async () => {
  mockServices([makeApiEntry()])
  renderApp()

  await vi.waitUntil(() => servicesPost.mock.calls.length > 0)

  expect(servicesPost).toHaveBeenLastCalledWith(
    SERVICES_PATH,
    expect.objectContaining({ body: { limit: 1000, fields: [] } })
  )
})

test('requests the services sorted by host name on a click of the Host header', async () => {
  mockServices([makeApiEntry()])
  renderApp()
  await screen.findByRole('button', { name: 'Host' })

  await userEvent.click(screen.getByRole('button', { name: 'Host' }))

  expect(servicesPost).toHaveBeenLastCalledWith(
    SERVICES_PATH,
    expect.objectContaining({ body: { limit: 1000, sort: ['host_name:asc'], fields: [] } })
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
  const originalOffsetHeight = Object.getOwnPropertyDescriptor(
    HTMLElement.prototype,
    'offsetHeight'
  )
  const originalOffsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth')

  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, 'offsetHeight', { configurable: true, value: 600 })
    Object.defineProperty(HTMLElement.prototype, 'offsetWidth', { configurable: true, value: 800 })
  })

  afterEach(() => {
    if (originalOffsetHeight) {
      Object.defineProperty(HTMLElement.prototype, 'offsetHeight', originalOffsetHeight)
    }
    if (originalOffsetWidth) {
      Object.defineProperty(HTMLElement.prototype, 'offsetWidth', originalOffsetWidth)
    }
  })

  test('links the host of each service to its Services of host page', async () => {
    mockServices([makeApiEntry()])
    renderApp()

    expect(await screen.findByRole('link', { name: 'web-2' })).toHaveAttribute(
      'href',
      expect.stringContaining('monitor_host_services.py?host=web-2&site=remote')
    )
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

  test('loads the action menu of a row from its own host and site', async () => {
    mockServices(SAME_NAMED_SERVICES_ON_TWO_HOSTS())
    renderApp()

    const menus = await screen.findAllByRole('button', { name: 'More actions' })
    await userEvent.click(menus[1]!)

    await vi.waitUntil(() => requestedFor(ACTION_MENU_PATH, 'web-2', 'remote'))
    expect(requestedFor(ACTION_MENU_PATH, 'web-1', 'local')).toBe(false)
  })

  test('loads the slide-in of a row from its own host and site', async () => {
    mockServices(SAME_NAMED_SERVICES_ON_TWO_HOSTS())
    renderApp()

    const names = await screen.findAllByRole('button', { name: 'CPU load' })
    await userEvent.click(names[1]!)

    await vi.waitUntil(() => requestedFor(OVERVIEW_PATH, 'web-2', 'remote'))
    expect(requestedFor(OVERVIEW_PATH, 'web-1', 'local')).toBe(false)
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
