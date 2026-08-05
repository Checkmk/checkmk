/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
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
    expect.objectContaining({ body: { limit: 1000, sort: ['name:asc'] } })
  )
})

test('requests a descending sort first for the State column', async () => {
  mockServices([makeApiEntry()])
  renderApp()
  await screen.findByRole('button', { name: 'State' })

  await userEvent.click(screen.getByRole('button', { name: 'State' }))

  expect(postSpy).toHaveBeenLastCalledWith(
    '/monitor/hosts/{hostname}/services',
    expect.objectContaining({ body: { limit: 1000, sort: ['state:desc'] } })
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
    expect.objectContaining({ body: { limit: 1000, q: 'CPU' } })
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
