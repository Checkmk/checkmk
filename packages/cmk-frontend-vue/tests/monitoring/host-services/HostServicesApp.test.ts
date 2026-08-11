/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, within } from '@testing-library/vue'
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
    summary: 'OK - 15 min load: 0.5',
    last_check: '2026-07-13T11:38:30Z',
    last_state_change: '2026-07-13T11:39:00Z'
  }
}

function renderApp() {
  return render(HostServicesApp, { props: { host: 'web-1', site: 'local' } })
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
    expect.objectContaining({ body: { limit: 1000, sort: ['name:asc'], fields: ['labels'] } })
  )
})

test('requests a descending sort first for the State column', async () => {
  mockServices([makeApiEntry()])
  renderApp()
  await screen.findByRole('button', { name: 'State' })

  await userEvent.click(screen.getByRole('button', { name: 'State' }))

  expect(postSpy).toHaveBeenLastCalledWith(
    '/monitor/hosts/{hostname}/services',
    expect.objectContaining({ body: { limit: 1000, sort: ['state:desc'], fields: ['labels'] } })
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
    expect.objectContaining({ body: { limit: 1000, q: 'CPU', fields: ['labels'] } })
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
        fields: ['labels']
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
    expect.objectContaining({ body: { limit: 1000, fields: ['labels'] } })
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
        fields: ['labels']
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
    expect.objectContaining({ body: { limit: 1000, fields: ['labels'] } })
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
        fields: ['labels']
      }
    })
  )
})

test('clearing the mode filter restores the full, unfiltered list', async () => {
  mockServices([makeApiEntry()])
  renderApp()

  await userEvent.click(await screen.findByRole('button', { name: 'Filter Mode' }))
  let panel = screen.getByRole('group', { name: 'Filter Mode' })
  await userEvent.click(within(panel).getByLabelText('Flapping'))
  await userEvent.click(within(panel).getByRole('button', { name: 'Apply' }))

  await userEvent.click(screen.getByRole('button', { name: 'Filter Mode' }))
  panel = screen.getByRole('group', { name: 'Filter Mode' })
  await userEvent.click(within(panel).getByRole('button', { name: 'Clear' }))
  await userEvent.click(within(panel).getByRole('button', { name: 'Apply' }))

  expect(postSpy).toHaveBeenLastCalledWith(
    '/monitor/hosts/{hostname}/services',
    expect.objectContaining({ body: { limit: 1000, fields: ['labels'] } })
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
    expect.objectContaining({ body: { limit: 1000, fields: ['labels'] } })
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
