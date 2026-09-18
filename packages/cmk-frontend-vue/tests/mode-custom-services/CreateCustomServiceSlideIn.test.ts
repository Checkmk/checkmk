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

import CreateCustomServiceSlideIn from '@/mode-custom-services/CreateCustomServiceSlideIn.vue'
import { type ServiceModel, emptyService } from '@/mode-custom-services/types'

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

const CREATE_URL = `${location.protocol}//${location.host}/api/internal/domain-types/custom_service/collections/all`
const AUTOCOMPLETE_URL = `${location.protocol}//${location.host}/api/1.0/objects/autocomplete/:ident`

let createRequests = 0
let lastBody: unknown = null

const server = setupServer(
  http.post(CREATE_URL, async ({ request }) => {
    createRequests += 1
    lastBody = await request.json()
    return HttpResponse.json({
      domainType: 'custom_service',
      id: 'http_duration',
      title: 'HTTP duration'
    })
  }),
  http.post(AUTOCOMPLETE_URL, () =>
    HttpResponse.json({ choices: [{ id: 'web01', value: 'web01 (10.0.0.1)' }] })
  )
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  cleanup()
  createRequests = 0
  lastBody = null
  server.resetHandlers()
})
afterAll(() => server.close())

function initialModel(overrides: Partial<ServiceModel> = {}): ServiceModel {
  return {
    ...emptyService(),
    metricName: 'otel.http.duration',
    serviceName: 'HTTP duration',
    ...overrides
  }
}

function renderSlideIn(initial: ServiceModel = initialModel()) {
  return render(CreateCustomServiceSlideIn, { props: { open: true, initial } })
}

async function selectHost(): Promise<void> {
  const combobox = await screen.findByRole('combobox')
  await waitFor(() => expect(combobox).toBeEnabled(), { timeout: 10000 })
  void userEvent.click(combobox)
  await userEvent.click(
    await screen.findByRole('option', { name: 'web01 (10.0.0.1)' }, { timeout: 10000 })
  )
}

test('shows the prefilled service name, editable', async () => {
  renderSlideIn()
  const input = await screen.findByDisplayValue('HTTP duration')
  await userEvent.clear(input)
  await userEvent.type(input, 'Latency')
  expect(screen.getByDisplayValue('Latency')).toBeTruthy()
})

test('saving is disabled until a host is selected', async () => {
  renderSlideIn()
  const save = await screen.findByRole('button', { name: 'Save' })
  expect(save).toBeDisabled()
  await selectHost()
  expect(save).toBeEnabled()
})

test('saving is disabled without a service name', async () => {
  renderSlideIn(initialModel({ serviceName: '' }))
  await selectHost()
  expect(await screen.findByRole('button', { name: 'Save' })).toBeDisabled()
})

test('saving persists the metric query from the graph and closes the dialog', async () => {
  const aggregator = {
    stages: [
      {
        aggregate_by: [{ kind: 'resource' as const, name: 'k8s.namespace.name' }],
        aggregation_fn: { type: 'scalar' as const, name: 'avg' as const }
      }
    ]
  }
  const { emitted } = renderSlideIn(
    initialModel({
      consolidation: { type: 'sum', function: 'sum_rate', lookback_seconds: 300 },
      aggregator
    })
  )
  await selectHost()
  await userEvent.click(await screen.findByRole('button', { name: 'Save' }))

  await waitFor(() => expect(emitted('close')).toBeTruthy())
  expect(lastBody).toEqual({
    configuration_name: 'http_duration_on_web01',
    host_assignment: { mode: 'explicit_host', host_name: 'web01' },
    configuration: {
      metric_name: 'otel.http.duration',
      service_name_template: 'HTTP duration',
      consolidation: { type: 'sum', function: 'sum_rate', lookback_seconds: 300 },
      aggregator
    }
  })
})

test('a rejected save keeps the dialog open and shows the backend message', async () => {
  server.use(
    http.post(CREATE_URL, () =>
      HttpResponse.json(
        {
          status: 409,
          title: 'Custom service already exists',
          detail: 'A configuration named "http_duration" already exists.'
        },
        { status: 409 }
      )
    )
  )
  const { emitted } = renderSlideIn()
  await selectHost()
  await userEvent.click(await screen.findByRole('button', { name: 'Save' }))

  expect(await screen.findByText(/already exists/)).toBeTruthy()
  expect(emitted('close')).toBeUndefined()
})

test('cancelling closes the dialog without saving', async () => {
  const { emitted } = renderSlideIn()
  await userEvent.click(await screen.findByRole('button', { name: 'Cancel' }))
  expect(emitted('close')).toBeTruthy()
  expect(createRequests).toBe(0)
})
