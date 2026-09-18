/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, expect, test, vi } from 'vitest'

import AlertWizardApp from '@/mode-alerts/AlertWizardApp.vue'

// The default client singleton captures `globalThis.fetch` at import time, before
// server.listen() patches it. Re-create it with a lazy fetch wrapper so MSW can intercept.
vi.mock('cmk-ui-library/lib/rest-api-client/client', async (importOriginal) => {
  const mod = await importOriginal<Record<string, unknown>>()
  const createClientImpl = (await import('openapi-fetch')).default
  return {
    ...mod,
    default: createClientImpl({
      baseUrl: `${location.protocol}//${location.host}/api/internal`,
      credentials: 'include',
      headers: { Accept: 'application/json' },
      fetch: (...args: Parameters<typeof globalThis.fetch>) => globalThis.fetch(...args)
    })
  }
})

const ENDPOINT = `${location.protocol}//${location.host}/api/internal/domain-types/service/collections/all`

const server = setupServer(
  http.post(ENDPOINT, () =>
    HttpResponse.json({
      id: 'all',
      links: [],
      value: [{ extensions: { host_name: 'web01', description: 'HTTP request duration' } }]
    })
  )
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  cleanup()
  server.resetHandlers()
})
afterAll(() => server.close())

function renderApp() {
  render(AlertWizardApp)
}

test('the wizard opens on naming the alert and selecting its services', () => {
  renderApp()

  expect(screen.getByRole('heading', { name: 'Name the alert and select services' })).toBeVisible()
})

test('the threshold step is offered alongside it', () => {
  renderApp()

  expect(screen.getByRole('heading', { name: 'Define threshold' })).toBeVisible()
})

test('a completed first step advances to the threshold step', async () => {
  renderApp()

  await userEvent.type(screen.getByRole('textbox', { name: /Alert name/ }), 'Latency too high')

  const serviceName = screen.getByRole('combobox', { name: 'Service name' })
  await waitFor(() => expect(serviceName).toBeEnabled())
  void userEvent.click(serviceName)
  await userEvent.click(await screen.findByRole('option', { name: 'HTTP request duration' }))

  await waitFor(() => {
    expect(screen.getByText('web01')).toBeInTheDocument()
  })

  await userEvent.click(screen.getByRole('button', { name: /next step/i }))

  await waitFor(() => {
    expect(
      screen.getByText('Defining the threshold and saving the alert will become available here.')
    ).toBeVisible()
  })
  expect(screen.getByRole('button', { name: 'Create alert' })).toBeDisabled()
})
