/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, within } from '@testing-library/vue'
import type {
  MonitoringAction,
  MonitoringHostServicesApp
} from 'cmk-shared-typing/typescript/monitoring/host_services'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import HostServicesApp from '@/monitoring/host-services/HostServicesApp.vue'

type ApiServiceEntry = components['schemas']['HostServiceEntry']

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

beforeEach(() => {
  document.body.innerHTML = '<div class="titlebar"></div>'
  postSpy = vi.spyOn(client, 'POST')
})

afterEach(() => {
  vi.restoreAllMocks()
  localStorage.clear()
  window.history.replaceState(null, '', '/monitor_host_services.py')
})

function servicesResponse(
  services: ApiServiceEntry[],
  counts: { matched: number; total: number }
): unknown {
  return {
    data: {
      services,
      meta: { hostname: 'web-1', site_id: 'local', limit: 1000, ...counts }
    },
    error: undefined,
    response: new Response()
  }
}

function mockServices(
  services: ApiServiceEntry[],
  counts: { matched: number; total: number } = {
    matched: services.length,
    total: services.length
  }
): void {
  postSpy.mockResolvedValue(servicesResponse(services, counts) as never)
}

function makeApiEntry(): ApiServiceEntry {
  return {
    name: 'CPU load',
    state: 'OK',
    is_flapping: false,
    stale: false,
    summary: 'OK - 15 min load: 0.5',
    last_check: 1783942710,
    last_state_change: 1783942740
  }
}

function renderApp(overrides: Partial<MonitoringHostServicesApp> = {}) {
  return render(HostServicesApp, {
    props: {
      host: 'web-1',
      site: 'local',
      user_id: 'cmkadmin',
      edition: 'pro',
      ...overrides
    } satisfies MonitoringHostServicesApp
  })
}

test('shows the empty-state message once a load returns no services', async () => {
  mockServices([])
  renderApp()

  expect(await screen.findByText('No results found.')).toBeInTheDocument()
})

test('shows the loading skeleton instead of the empty-state message while loading', () => {
  mockServices([])
  renderApp()

  expect(screen.queryByText('No results found.')).not.toBeInTheDocument()
})

test('shows the total service count reported by the endpoint', async () => {
  mockServices([makeApiEntry()], { matched: 42, total: 42 })
  renderApp()

  expect(await screen.findByText('Total rows: 42')).toBeInTheDocument()
})

test('shows no matching count while nothing narrows the services', async () => {
  mockServices([makeApiEntry()], { matched: 42, total: 42 })
  renderApp()

  expect(await screen.findByText('Total rows: 42')).toBeInTheDocument()
  expect(screen.queryByText(/Rows matching your criteria/)).not.toBeInTheDocument()
})

test('requests the services sorted by name ascending on the first click of the Service header', async () => {
  mockServices([makeApiEntry()])
  renderApp()
  await screen.findByRole('button', { name: 'Service' })

  await userEvent.click(screen.getByRole('button', { name: 'Service' }))

  expect(postSpy).toHaveBeenLastCalledWith(
    '/monitor/hosts/{hostname}/services',
    expect.objectContaining({
      body: {
        limit: 1000,
        sort: ['name:asc'],
        fields: []
      }
    })
  )
})

test('requests a descending sort first for the State column', async () => {
  mockServices([makeApiEntry()])
  renderApp()
  await screen.findByRole('button', { name: 'State' })

  await userEvent.click(screen.getByRole('button', { name: 'State' }))

  expect(postSpy).toHaveBeenLastCalledWith(
    '/monitor/hosts/{hostname}/services',
    expect.objectContaining({
      body: {
        limit: 1000,
        sort: ['state:desc'],
        fields: []
      }
    })
  )
})

test('requests the services matching a submitted search query', async () => {
  mockServices([makeApiEntry()])
  renderApp()
  const input = await screen.findByPlaceholderText('Search services…')

  // Focus explicitly: CmkSplitPane's resizable layout keeps userEvent's
  // simulated click from landing focus on the input under jsdom.
  input.focus()
  await userEvent.type(input, 'CPU{Enter}')

  expect(postSpy).toHaveBeenLastCalledWith(
    '/monitor/hosts/{hostname}/services',
    expect.objectContaining({
      body: { limit: 1000, q: 'CPU', fields: [] }
    })
  )
})

test('tells the user the empty result came from their search', async () => {
  mockServices([makeApiEntry()])
  renderApp()
  const input = await screen.findByPlaceholderText('Search services…')
  mockServices([], { matched: 0, total: 42 })

  // Focus explicitly: CmkSplitPane's resizable layout keeps userEvent's
  // simulated click from landing focus on the input under jsdom.
  input.focus()
  await userEvent.type(input, 'nope{Enter}')

  expect(await screen.findByText('No results found for your search.')).toBeInTheDocument()
})

test('requests services whose name contains the typed filter text', async () => {
  mockServices([makeApiEntry()])
  renderApp()

  await userEvent.click(await screen.findByRole('button', { name: 'Filter Service' }))
  const panel = screen.getByRole('group', { name: 'Filter Service' })
  await fireEvent.update(within(panel).getByRole('textbox'), 'cpu')
  await userEvent.click(within(panel).getByRole('button', { name: 'Apply' }))

  expect(postSpy).toHaveBeenLastCalledWith(
    '/monitor/hosts/{hostname}/services',
    expect.objectContaining({
      body: {
        limit: 1000,
        filter: { type: 'condition', field: 'name', op: 'contains', value: 'cpu' },
        fields: []
      }
    })
  )
})

test('clearing the name filter restores the full, unfiltered list', async () => {
  mockServices([makeApiEntry()])
  renderApp()

  await userEvent.click(await screen.findByRole('button', { name: 'Filter Service' }))
  let panel = screen.getByRole('group', { name: 'Filter Service' })
  await fireEvent.update(within(panel).getByRole('textbox'), 'cpu')
  await userEvent.click(within(panel).getByRole('button', { name: 'Apply' }))

  await userEvent.click(screen.getByRole('button', { name: 'Filter Service' }))
  panel = screen.getByRole('group', { name: 'Filter Service' })
  await userEvent.click(within(panel).getByRole('button', { name: 'Clear' }))
  await userEvent.click(within(panel).getByRole('button', { name: 'Apply' }))

  expect(postSpy).toHaveBeenLastCalledWith(
    '/monitor/hosts/{hostname}/services',
    expect.objectContaining({
      body: { limit: 1000, fields: [] }
    })
  )
})

test('requests services whose summary contains the typed filter text', async () => {
  mockServices([makeApiEntry()])
  renderApp()

  await userEvent.click(await screen.findByRole('button', { name: 'Filter Summary' }))
  const panel = screen.getByRole('group', { name: 'Filter Summary' })
  await fireEvent.update(within(panel).getByRole('textbox'), 'timeout')
  await userEvent.click(within(panel).getByRole('button', { name: 'Apply' }))

  expect(postSpy).toHaveBeenLastCalledWith(
    '/monitor/hosts/{hostname}/services',
    expect.objectContaining({
      body: {
        limit: 1000,
        filter: { type: 'condition', field: 'summary', op: 'contains', value: 'timeout' },
        fields: []
      }
    })
  )
})

test('clearing the summary filter restores the full, unfiltered list', async () => {
  mockServices([makeApiEntry()])
  renderApp()

  await userEvent.click(await screen.findByRole('button', { name: 'Filter Summary' }))
  let panel = screen.getByRole('group', { name: 'Filter Summary' })
  await fireEvent.update(within(panel).getByRole('textbox'), 'timeout')
  await userEvent.click(within(panel).getByRole('button', { name: 'Apply' }))

  await userEvent.click(screen.getByRole('button', { name: 'Filter Summary' }))
  panel = screen.getByRole('group', { name: 'Filter Summary' })
  await userEvent.click(within(panel).getByRole('button', { name: 'Clear' }))
  await userEvent.click(within(panel).getByRole('button', { name: 'Apply' }))

  expect(postSpy).toHaveBeenLastCalledWith(
    '/monitor/hosts/{hostname}/services',
    expect.objectContaining({
      body: { limit: 1000, fields: [] }
    })
  )
})

test('requests services that are not acknowledged and not in downtime', async () => {
  mockServices([makeApiEntry()])
  renderApp()

  await userEvent.click(await screen.findByRole('button', { name: 'Filter Mode' }))
  const panel = screen.getByRole('group', { name: 'Filter Mode' })
  await userEvent.click(within(panel).getByLabelText('NOT Acknowledged'))
  await userEvent.click(within(panel).getByLabelText('NOT In downtime'))
  await userEvent.click(within(panel).getByRole('button', { name: 'Apply' }))

  expect(postSpy).toHaveBeenLastCalledWith(
    '/monitor/hosts/{hostname}/services',
    expect.objectContaining({
      body: {
        limit: 1000,
        filter: {
          type: 'and',
          children: [
            { type: 'condition', field: 'in_downtime', op: 'eq', value: false },
            { type: 'condition', field: 'acknowledged', op: 'eq', value: false }
          ]
        },
        fields: []
      }
    })
  )
})

test('clearing the mode filter restores the full, unfiltered list', async () => {
  mockServices([makeApiEntry()])
  renderApp()

  await userEvent.click(await screen.findByRole('button', { name: 'Filter Mode' }))
  let panel = screen.getByRole('group', { name: 'Filter Mode' })
  await userEvent.click(within(panel).getByLabelText('Acknowledged'))
  await userEvent.click(within(panel).getByRole('button', { name: 'Apply' }))

  await userEvent.click(screen.getByRole('button', { name: 'Filter Mode' }))
  panel = screen.getByRole('group', { name: 'Filter Mode' })
  await userEvent.click(within(panel).getByRole('button', { name: 'Clear' }))
  await userEvent.click(within(panel).getByRole('button', { name: 'Apply' }))

  expect(postSpy).toHaveBeenLastCalledWith(
    '/monitor/hosts/{hostname}/services',
    expect.objectContaining({
      body: { limit: 1000, fields: [] }
    })
  )
})

test('activating the unhandled-problems quick filter requests the WARN/CRIT, unacked, no-downtime preset', async () => {
  mockServices([makeApiEntry()])
  renderApp()

  await userEvent.click(await screen.findByRole('button', { name: 'Unhandled service problems' }))

  expect(postSpy).toHaveBeenLastCalledWith(
    '/monitor/hosts/{hostname}/services',
    expect.objectContaining({
      body: {
        limit: 1000,
        filter: {
          type: 'and',
          children: [
            { type: 'condition', field: 'state', op: 'one_of', value: ['WARN', 'CRIT'] },
            { type: 'condition', field: 'acknowledged', op: 'eq', value: false },
            { type: 'condition', field: 'in_downtime', op: 'eq', value: false }
          ]
        },
        fields: []
      }
    })
  )
})

test('clicking the unhandled-problems chip again turns it back off', async () => {
  mockServices([makeApiEntry()])
  renderApp()

  const chip = await screen.findByRole('button', { name: 'Unhandled service problems' })
  await userEvent.click(chip)
  await userEvent.click(chip)

  expect(postSpy).toHaveBeenLastCalledWith(
    '/monitor/hosts/{hostname}/services',
    expect.objectContaining({
      body: { limit: 1000, fields: [] }
    })
  )
})

test('resetting all filters also turns off the unhandled-problems chip', async () => {
  mockServices([makeApiEntry()])
  renderApp()

  await userEvent.click(await screen.findByRole('button', { name: 'Unhandled service problems' }))
  await userEvent.click(screen.getByRole('button', { name: 'Reset all filters' }))

  expect(postSpy).toHaveBeenLastCalledWith(
    '/monitor/hosts/{hostname}/services',
    expect.objectContaining({
      body: { limit: 1000, fields: [] }
    })
  )
})

test('shows a tooltip on the unhandled-problems chip', async () => {
  mockServices([makeApiEntry()])
  renderApp()

  expect(await screen.findByRole('button', { name: 'Unhandled service problems' })).toHaveAttribute(
    'title',
    'Show only services in a problem state (WARN or CRIT) that are neither acknowledged nor in a scheduled downtime'
  )
})

test('resetting all filters restores the full, unfiltered list', async () => {
  mockServices([makeApiEntry()])
  renderApp()

  await userEvent.click(await screen.findByRole('button', { name: 'Filter Service' }))
  await fireEvent.update(
    within(screen.getByRole('group', { name: 'Filter Service' })).getByRole('textbox'),
    'cpu'
  )
  await userEvent.click(
    within(screen.getByRole('group', { name: 'Filter Service' })).getByRole('button', {
      name: 'Apply'
    })
  )

  await userEvent.click(screen.getByRole('button', { name: 'Filter Summary' }))
  await fireEvent.update(
    within(screen.getByRole('group', { name: 'Filter Summary' })).getByRole('textbox'),
    'timeout'
  )
  await userEvent.click(
    within(screen.getByRole('group', { name: 'Filter Summary' })).getByRole('button', {
      name: 'Apply'
    })
  )

  await userEvent.click(screen.getByRole('button', { name: 'Reset all filters' }))

  expect(postSpy).toHaveBeenLastCalledWith(
    '/monitor/hosts/{hostname}/services',
    expect.objectContaining({
      body: { limit: 1000, fields: [] }
    })
  )
})

test('requests only the states the URL a link arrived on names', async () => {
  window.history.replaceState(
    null,
    '',
    `/monitor_host_services.py?host=web-1&site=local&filter=${encodeURIComponent(
      JSON.stringify({ type: 'condition', field: 'state', op: 'one_of', value: ['CRIT'] })
    )}`
  )
  mockServices([makeApiEntry()])
  renderApp()
  await screen.findByText('Total rows: 1')

  expect(postSpy).toHaveBeenLastCalledWith(
    '/monitor/hosts/{hostname}/services',
    expect.objectContaining({
      body: {
        limit: 1000,
        filter: { type: 'condition', field: 'state', op: 'one_of', value: ['CRIT'] },
        fields: []
      }
    })
  )
})

test('shows the state filter a link arrived with as an active filter', async () => {
  window.history.replaceState(
    null,
    '',
    `/monitor_host_services.py?host=web-1&site=local&filter=${encodeURIComponent(
      JSON.stringify({ type: 'condition', field: 'state', op: 'one_of', value: ['CRIT'] })
    )}`
  )
  mockServices([makeApiEntry()])
  renderApp()

  await userEvent.click(await screen.findByRole('button', { name: 'Filter State' }))

  expect(
    within(screen.getByRole('group', { name: 'Filter State' })).getByLabelText('CRIT')
  ).toBeChecked()
})

test('requests services in a picked state that are also flapping', async () => {
  mockServices([makeApiEntry()])
  renderApp()

  await userEvent.click(await screen.findByRole('button', { name: 'Filter State' }))
  const panel = screen.getByRole('group', { name: 'Filter State' })
  await userEvent.click(within(panel).getByLabelText('CRIT'))
  await userEvent.click(within(panel).getByLabelText('Flapping'))
  await userEvent.click(within(panel).getByRole('button', { name: 'Apply' }))

  expect(postSpy).toHaveBeenLastCalledWith(
    '/monitor/hosts/{hostname}/services',
    expect.objectContaining({
      body: {
        limit: 1000,
        filter: {
          type: 'and',
          children: [
            { type: 'condition', field: 'state', op: 'one_of', value: ['CRIT'] },
            { type: 'condition', field: 'is_flapping', op: 'eq', value: true }
          ]
        },
        fields: []
      }
    })
  )
})

test('clearing the state filter also clears its flapping/stale flags', async () => {
  mockServices([makeApiEntry()])
  renderApp()

  await userEvent.click(await screen.findByRole('button', { name: 'Filter State' }))
  let panel = screen.getByRole('group', { name: 'Filter State' })
  await userEvent.click(within(panel).getByLabelText('Stale'))
  await userEvent.click(within(panel).getByRole('button', { name: 'Apply' }))

  await userEvent.click(screen.getByRole('button', { name: 'Filter State' }))
  panel = screen.getByRole('group', { name: 'Filter State' })
  await userEvent.click(within(panel).getByRole('button', { name: 'Clear' }))
  await userEvent.click(within(panel).getByRole('button', { name: 'Apply' }))

  expect(postSpy).toHaveBeenLastCalledWith(
    '/monitor/hosts/{hostname}/services',
    expect.objectContaining({
      body: { limit: 1000, fields: [] }
    })
  )
})

test('keeps the host and site params a filter write leaves the URL with', async () => {
  window.history.replaceState(null, '', '/monitor_host_services.py?host=web-1&site=local')
  mockServices([makeApiEntry()])
  renderApp()

  await userEvent.click(await screen.findByRole('button', { name: 'Filter Service' }))
  const panel = screen.getByRole('group', { name: 'Filter Service' })
  await fireEvent.update(within(panel).getByRole('textbox'), 'cpu')
  await userEvent.click(within(panel).getByRole('button', { name: 'Apply' }))

  const params = new URLSearchParams(window.location.search)
  expect(params.get('host')).toBe('web-1')
  expect(params.get('site')).toBe('local')
  expect(params.get('filter')).toBe(
    JSON.stringify({ type: 'condition', field: 'name', op: 'contains', value: 'cpu' })
  )
})

test('marks the sorted column with its direction', async () => {
  mockServices([makeApiEntry()])
  renderApp()
  await screen.findByRole('button', { name: 'Service' })

  await userEvent.click(screen.getByRole('button', { name: 'Service' }))

  expect(screen.getByRole('columnheader', { name: 'Service' })).toHaveAttribute(
    'aria-sort',
    'ascending'
  )
})

test('requests services whose last state change is at or after the picked instant', async () => {
  mockServices([makeApiEntry()])
  renderApp()

  await userEvent.click(await screen.findByRole('button', { name: 'Filter Last state change' }))
  const panel = screen.getByRole('group', { name: 'Filter Last state change' })
  const from = within(panel).getByRole('group', { name: 'From' })

  await userEvent.click(within(from).getByRole('button', { name: 'Open calendar' }))
  await userEvent.click(within(from).getByRole('button', { name: /\b20,/ }))
  await fireEvent.update(within(from).getByRole('spinbutton', { name: 'Hours' }), '08')
  await fireEvent.update(within(from).getByRole('spinbutton', { name: 'Minutes' }), '45')
  await userEvent.click(within(from).getByRole('button', { name: 'Apply' }))

  await userEvent.click(within(panel).getByRole('button', { name: 'Apply' }))

  // The picker works in the browser zone, so the expectation is built from the same local clock.
  const today = new Date()
  const picked = new Date(today.getFullYear(), today.getMonth(), 20, 8, 45).getTime() / 1000

  expect(postSpy).toHaveBeenLastCalledWith(
    '/monitor/hosts/{hostname}/services',
    expect.objectContaining({
      body: {
        limit: 1000,
        filter: {
          type: 'condition',
          field: 'last_state_change',
          op: 'gte',
          value: picked
        },
        fields: []
      }
    })
  )
})

test('a column decision applied in the picker outlives the page', async () => {
  mockServices([makeApiEntry()])
  renderApp()
  await screen.findByRole('columnheader', { name: 'Service' })

  await userEvent.click(screen.getByRole('button', { name: 'Show or hide columns' }))
  await userEvent.click(screen.getByRole('button', { name: 'Labels' }))
  await userEvent.click(screen.getByRole('button', { name: 'Apply' }))

  expect(
    JSON.parse(
      localStorage.getItem('monitoring-host-services-columns-local-cmkadmin-pro') ?? 'null'
    )
  ).toMatchObject({ labels: true })
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
  mockServices([makeApiEntry()])
  renderApp({ actions: [] })
  await screen.findByRole('columnheader', { name: 'Service' })

  expect(screen.queryByRole('checkbox', { name: 'Select all rows' })).not.toBeInTheDocument()
  expect(
    screen.queryByRole('toolbar', { name: 'Actions for selected services' })
  ).not.toBeInTheDocument()
})

test('offers row selection once one action is permitted', async () => {
  mockServices([makeApiEntry()])
  renderApp({ actions: [ACKNOWLEDGE] })

  expect(await screen.findByRole('checkbox', { name: 'Select all rows' })).toBeInTheDocument()
  expect(screen.getByRole('toolbar', { name: 'Actions for selected services' })).toBeInTheDocument()
})
