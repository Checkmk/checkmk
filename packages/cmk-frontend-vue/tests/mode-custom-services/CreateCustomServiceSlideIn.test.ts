/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
// eslint-disable-next-line no-restricted-imports -- pre-existing violation: type these handlers, never copy this line
import { HttpResponse, delay, http } from 'msw'
import { afterEach, expect, test } from 'vitest'

import CreateCustomServiceSlideIn from '@/mode-custom-services/CreateCustomServiceSlideIn.vue'
import { type ServiceModel, emptyService } from '@/mode-custom-services/types'

const CREATE_URL = `${location.protocol}//${location.host}/api/internal/domain-types/custom_service/collections/all`
const AUTOCOMPLETE_URL = `${location.protocol}//${location.host}/api/internal/objects/autocomplete/:ident`
const TEMPLATE_ATTRIBUTES_URL = `${location.protocol}//${location.host}/api/internal/domain-types/custom_service/actions/template_attributes/invoke`
const RESOLVE_URL = `${location.protocol}//${location.host}/api/internal/domain-types/custom_service/actions/resolve_host_name_template/invoke`
const OPENTELEMETRY_DATA_URL = `${location.protocol}//${location.host}/api/internal/domain-types/custom_service/actions/opentelemetry_data/invoke`
const RESOLVE_SERVICES_URL = `${location.protocol}//${location.host}/api/internal/domain-types/custom_service/actions/resolve_services/invoke`

let createRequests = 0
let lastBody: unknown = null
let existingNames: string[] = []

const server = useMswServer(
  http.post(CREATE_URL, async ({ request }) => {
    createRequests += 1
    lastBody = await request.json()
    return HttpResponse.json({
      domainType: 'custom_service',
      id: 'http_duration',
      title: 'HTTP duration'
    })
  }),
  http.get(CREATE_URL, () =>
    HttpResponse.json({
      value: existingNames.map((id) => ({ id, domainType: 'custom_service' }))
    })
  ),
  http.post(AUTOCOMPLETE_URL, () =>
    HttpResponse.json({ choices: [{ id: 'web01', value: 'web01 (10.0.0.1)' }] })
  ),
  http.post(TEMPLATE_ATTRIBUTES_URL, () =>
    HttpResponse.json({ availability: 'available', attributes: [], truncated: false })
  ),
  http.post(RESOLVE_URL, () =>
    HttpResponse.json({
      matching_hosts: [],
      unmatched_host_names: [],
      hidden_match_count: 0,
      truncated: false,
      creatable_folders: [{ path: '/', title: 'Main' }],
      host_creation_refusal: null
    })
  ),
  http.post(RESOLVE_SERVICES_URL, () =>
    HttpResponse.json({ services: [], total: 0, clashes: [], complete: true })
  ),
  http.post(OPENTELEMETRY_DATA_URL, () => HttpResponse.json({ hosts: [] }))
)

afterEach(() => {
  cleanup()
  createRequests = 0
  lastBody = null
  existingNames = []
})

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

async function configurationNameInput(): Promise<HTMLElement> {
  return await screen.findByRole('textbox', { name: /Configuration name/ })
}

async function enterConfigurationName(name: string): Promise<void> {
  const input = await configurationNameInput()
  await waitFor(() => expect(input).not.toHaveValue(''))
  await userEvent.clear(input)
  await userEvent.type(input, name)
}

async function selectHost(): Promise<void> {
  const combobox = await screen.findByRole('combobox')
  await waitFor(() => expect(combobox).toBeEnabled(), { timeout: 10000 })
  void userEvent.click(combobox)
  await userEvent.click(
    await screen.findByRole('option', { name: 'web01 (10.0.0.1)' }, { timeout: 10000 })
  )
}

test('suggests the next free configuration name', async () => {
  existingNames = ['custom_service_config_1', 'custom_service_config_4']
  renderSlideIn()
  const input = await configurationNameInput()
  await waitFor(() => expect(input).toHaveValue('custom_service_config_5'))
})

test('creates the service under the entered configuration name', async () => {
  const { emitted } = renderSlideIn()
  await enterConfigurationName('my_latency')
  await selectHost()
  await userEvent.click(await screen.findByRole('button', { name: 'Save' }))

  await waitFor(() => expect(emitted('close')).toBeTruthy())
  expect(lastBody).toMatchObject({ configuration_name: 'my_latency' })
})

test('a malformed configuration name blocks the create and shows the error at the field', async () => {
  const { emitted } = renderSlideIn()
  await enterConfigurationName('1 bad')
  await selectHost()
  await userEvent.click(await screen.findByRole('button', { name: 'Save' }))

  await screen.findByText(
    'The name must only consist of letters, digits, dash and underscore and it must start with a letter or underscore.'
  )
  expect(createRequests).toBe(0)
  expect(emitted('close')).toBeUndefined()
})

test('a configuration name in use blocks the create and shows the error at the field', async () => {
  existingNames = ['taken_name']
  const { emitted } = renderSlideIn()
  await enterConfigurationName('taken_name')
  await selectHost()
  await userEvent.click(await screen.findByRole('button', { name: 'Save' }))

  await screen.findByText('A configuration with this name already exists. Choose a different name.')
  expect(createRequests).toBe(0)
  expect(emitted('close')).toBeUndefined()
})

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
  await waitFor(async () => expect(await configurationNameInput()).not.toHaveValue(''))
  await selectHost()
  await userEvent.click(await screen.findByRole('button', { name: 'Save' }))

  await waitFor(() => expect(emitted('close')).toBeTruthy())
  expect(lastBody).toEqual({
    configuration_name: 'custom_service_config_1',
    host_assignment: { mode: 'explicit_host', host_name: 'web01' },
    configuration: {
      metric_name: 'otel.http.duration',
      service_name_template: 'HTTP duration $SERIES_ATTRIBUTES$',
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

test('a host name template that resolves to no host name cannot be saved', async () => {
  renderSlideIn(initialModel({ hostNameTemplate: '$RESOURCE_ATTR.service.name$' }))

  expect(await screen.findByText(/resolves to no host name/)).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled()
})

test('a host name template that resolves only to new hosts can be saved', async () => {
  server.use(
    http.post(RESOLVE_URL, () =>
      HttpResponse.json({
        matching_hosts: [],
        unmatched_host_names: ['pod-cart'],
        hidden_match_count: 0,
        truncated: false,
        creatable_folders: [{ path: '/', title: 'Main' }],
        host_creation_refusal: null
      })
    )
  )
  renderSlideIn(initialModel({ hostNameTemplate: '$RESOURCE_ATTR.service.name$' }))

  expect(await screen.findByText(/New hosts/)).toHaveTextContent('pod-cart')
  expect(screen.getByRole('button', { name: 'Save' })).toBeEnabled()
})

test('a new host is looked up and created in the folder chosen for it', async () => {
  let servicesRequest: unknown = null
  server.use(
    http.post(RESOLVE_URL, () =>
      HttpResponse.json({
        matching_hosts: [],
        unmatched_host_names: ['pod-cart'],
        hidden_match_count: 0,
        truncated: false,
        creatable_folders: [
          { path: '/', title: 'Main' },
          { path: '/k8s/shop', title: 'Main / K8s / Shop' }
        ],
        host_creation_refusal: null
      })
    ),
    http.post(RESOLVE_SERVICES_URL, async ({ request }) => {
      servicesRequest = await request.json()
      return HttpResponse.json({
        services: [
          { host_name: 'pod-cart', service_name: 'HTTP duration', new_host: true, clash: null }
        ],
        total: 1,
        clashes: [],
        complete: true
      })
    })
  )
  const { emitted } = renderSlideIn(
    initialModel({ hostNameTemplate: '$RESOURCE_ATTR.service.name$' })
  )
  await enterConfigurationName('pod_latency')

  await userEvent.click(await screen.findByRole('combobox', { name: 'Folder of pod-cart' }))
  await userEvent.click(await screen.findByRole('option', { name: 'Main / K8s / Shop' }))
  const chosen = { new_host_folders: [{ host_name: 'pod-cart', folder: '/k8s/shop' }] }
  await waitFor(() => expect(servicesRequest).toMatchObject(chosen))
  await userEvent.click(screen.getByRole('button', { name: 'Save' }))

  await waitFor(() => expect(emitted('close')).toBeTruthy())
  expect(lastBody).toMatchObject(chosen)
})

test('choosing a folder keeps the services and the folder choice shown while looking up', async () => {
  let servicesRequests = 0
  server.use(
    http.post(RESOLVE_URL, () =>
      HttpResponse.json({
        matching_hosts: [],
        unmatched_host_names: ['pod-cart'],
        hidden_match_count: 0,
        truncated: false,
        creatable_folders: [
          { path: '/', title: 'Main' },
          { path: '/k8s/shop', title: 'Main / K8s / Shop' }
        ],
        host_creation_refusal: null
      })
    ),
    http.post(RESOLVE_SERVICES_URL, async () => {
      servicesRequests += 1
      if (servicesRequests > 1) {
        await delay('infinite')
      }
      return HttpResponse.json({
        services: [
          { host_name: 'pod-cart', service_name: 'HTTP duration', new_host: true, clash: null }
        ],
        total: 1,
        clashes: [],
        complete: true
      })
    })
  )
  renderSlideIn(initialModel({ hostNameTemplate: '$RESOURCE_ATTR.service.name$' }))

  await userEvent.click(await screen.findByRole('combobox', { name: 'Folder of pod-cart' }))
  await userEvent.click(await screen.findByRole('option', { name: 'Main / K8s / Shop' }))

  await screen.findByText('Updating…')
  expect(screen.getByText('HTTP duration')).toBeTruthy()
  expect(screen.getByRole('combobox', { name: 'Folder of pod-cart' })).toHaveTextContent(
    'Main / K8s / Shop'
  )
})

test('a refused new host keeps the dialog open and says why', async () => {
  server.use(
    http.post(RESOLVE_URL, () =>
      HttpResponse.json({
        matching_hosts: [],
        unmatched_host_names: ['pod-cart'],
        hidden_match_count: 0,
        truncated: false,
        creatable_folders: [{ path: '/', title: 'Main' }],
        host_creation_refusal: null
      })
    ),
    http.post(CREATE_URL, () =>
      HttpResponse.json(
        {
          status: 403,
          title: 'Some hosts could not be created',
          detail: 'Sorry, the hosts in the folder Main are locked.',
          ext: { new_host_names: ['pod-cart'] }
        },
        { status: 403 }
      )
    )
  )
  const { emitted } = renderSlideIn(
    initialModel({ hostNameTemplate: '$RESOURCE_ATTR.service.name$' })
  )
  const save = await screen.findByRole('button', { name: 'Save' })
  await waitFor(() => expect(save).toBeEnabled())
  await userEvent.click(save)

  expect(await screen.findByText('Sorry, the hosts in the folder Main are locked.')).toBeTruthy()
  expect(emitted('close')).toBeUndefined()
})

function serveClash(): void {
  server.use(
    http.post(RESOLVE_SERVICES_URL, () =>
      HttpResponse.json({
        services: [
          { host_name: 'pod-cart', service_name: 'Latency', new_host: false, clash: 'monitored' }
        ],
        total: 1,
        clashes: [
          {
            host_name: 'pod-cart',
            service_name: 'Latency',
            message: 'A service named "Latency" already exists on host "pod-cart".'
          }
        ],
        complete: true
      })
    )
  )
}

test('a service name that clashes cannot be saved', async () => {
  server.use(
    http.post(RESOLVE_URL, () =>
      HttpResponse.json({
        matching_hosts: [],
        unmatched_host_names: ['pod-cart'],
        hidden_match_count: 0,
        truncated: false,
        creatable_folders: [{ path: '/', title: 'Main' }],
        host_creation_refusal: null
      })
    )
  )
  serveClash()
  renderSlideIn(initialModel({ hostNameTemplate: '$RESOURCE_ATTR.service.name$' }))

  expect(await screen.findByText(/already exists on host "pod-cart"/)).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled()
})
