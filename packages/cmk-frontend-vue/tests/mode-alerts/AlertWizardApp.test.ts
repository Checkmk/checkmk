/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'
import { afterEach, expect, test } from 'vitest'

import AlertWizardApp from '@/mode-alerts/AlertWizardApp.vue'

const API_BASE = `${location.protocol}//${location.host}/api/internal`
const ENDPOINT = `${API_BASE}/domain-types/service/collections/all`
const CREATE_ENDPOINT = `${API_BASE}/domain-types/telemetry_alert/collections/all`

const server = useMswServer(
  http.post(ENDPOINT, () =>
    HttpResponse.json({
      id: 'all',
      links: [],
      value: [{ extensions: { host_name: 'web01', description: 'HTTP request duration' } }]
    })
  )
)

afterEach(() => {
  cleanup()
})

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

async function completeFirstStep() {
  await userEvent.type(screen.getByRole('textbox', { name: /Alert name/ }), 'Latency too high')

  const serviceName = screen.getByRole('combobox', { name: 'Service name' })
  await waitFor(() => expect(serviceName).toBeEnabled())
  void userEvent.click(serviceName)
  await userEvent.click(await screen.findByRole('option', { name: 'HTTP request duration' }))

  await waitFor(() => {
    expect(screen.getByText('web01')).toBeInTheDocument()
  })

  await userEvent.click(screen.getByRole('button', { name: /next step/i }))
}

test('a completed first step advances to the threshold step', async () => {
  renderApp()

  await completeFirstStep()

  await waitFor(() => {
    expect(screen.getByText('Defining the threshold will become available here.')).toBeVisible()
  })
})

test('creating the alert sends its name and service match', async () => {
  let sentBody: unknown = null
  server.use(
    http.post(CREATE_ENDPOINT, async ({ request }) => {
      sentBody = await request.json()
      return HttpResponse.json({})
    })
  )
  renderApp()
  await completeFirstStep()

  await userEvent.click(await screen.findByRole('button', { name: 'Create alert' }))

  expect(await screen.findByText('The alert was created.')).toBeVisible()
  expect(sentBody).toEqual({
    configuration_name: 'latency_too_high',
    alert_name: 'Latency too high',
    service_match: { mode: 'exact', pattern: 'HTTP request duration' }
  })
})

test('a rejected alert shows the reason', async () => {
  server.use(
    http.post(CREATE_ENDPOINT, () =>
      HttpResponse.json(
        {
          title: 'Configuration name already in use',
          detail: 'A configuration named "latency_too_high" already exists.',
          status: 409
        },
        { status: 409 }
      )
    )
  )
  renderApp()
  await completeFirstStep()

  await userEvent.click(await screen.findByRole('button', { name: 'Create alert' }))

  expect(await screen.findByText(/already exists/)).toBeVisible()
})
