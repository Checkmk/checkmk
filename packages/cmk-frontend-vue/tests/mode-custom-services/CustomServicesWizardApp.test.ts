/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// The wizard in edit mode: it loads the stored service, shows it, and writes it back through
// the update endpoint. In create mode, it can go on to add an alert once the service is created.
// The endpoints are stubbed at the network boundary (MSW).
import { userEvent } from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
// eslint-disable-next-line no-restricted-imports -- pre-existing violation: type these handlers, never copy this line
import { HttpResponse, http } from 'msw'
import { afterEach, beforeEach, expect, test } from 'vitest'

import { resetGlobalTimeState } from '@/graphing/GlobalTimePicker/globalTimeState'
import CustomServicesWizardApp from '@/mode-custom-services/CustomServicesWizardApp.vue'

const API_BASE = `${location.protocol}//${location.host}/api/internal`
const OBJECT_URL = `${API_BASE}/objects/custom_service/http_duration_on_web01`
const LIST_URL = `${API_BASE}/domain-types/custom_service/collections/all`
const AUTOCOMPLETE_URL = `${API_BASE}/objects/autocomplete/:ident`
const METRIC_NAMES_URL = `${API_BASE}/domain-types/telemetry_metrics/actions/names_with_types/invoke`
const GRAPH_DATA_URL = `${API_BASE}/domain-types/custom_graph/actions/fetch_data/invoke`
const TEMPLATE_ATTRIBUTES_URL = `${API_BASE}/domain-types/custom_service/actions/template_attributes/invoke`
const RESOLVE_URL = `${API_BASE}/domain-types/custom_service/actions/resolve_host_name_template/invoke`

const STORED_EXTENSIONS = {
  host_assignment: { mode: 'explicit_host', host_name: 'web01' },
  configuration: {
    metric_name: 'otel.http.duration',
    service_name_template: 'HTTP duration',
    consolidation: { type: 'sum', function: 'sum_rate', lookback_seconds: 300 }
  }
}

// Step 1's filter editor materialises the "matches everything" filter as soon as it renders, so
// a service stored without one is written back carrying the empty AND. The endpoint reports that
// one as omitted again, so the round trip loses nothing.
const WRITTEN_EXTENSIONS = {
  ...STORED_EXTENSIONS,
  configuration: {
    ...STORED_EXTENSIONS.configuration,
    attribute_filter: { type: 'and', conjuncts: [] }
  }
}

let updateRequests = 0
let createRequests = 0
let templateAttributesRequests = 0
let lastBody: unknown = null
let lastIfMatch: string | null = null

const server = useMswServer(
  http.get(OBJECT_URL, () =>
    HttpResponse.json(
      {
        domainType: 'custom_service',
        id: 'http_duration_on_web01',
        title: 'HTTP duration',
        extensions: STORED_EXTENSIONS
      },
      { headers: { ETag: 'etag-1' } }
    )
  ),
  http.put(OBJECT_URL, async ({ request }) => {
    updateRequests += 1
    lastBody = await request.json()
    lastIfMatch = request.headers.get('If-Match')
    return HttpResponse.json({
      domainType: 'custom_service',
      id: 'http_duration_on_web01',
      title: 'HTTP duration',
      extensions: STORED_EXTENSIONS
    })
  }),
  http.get(LIST_URL, () =>
    HttpResponse.json({
      value: [{ id: 'http_duration_on_web01', domainType: 'custom_service' }]
    })
  ),
  http.post(LIST_URL, () => {
    createRequests += 1
    return HttpResponse.json({
      domainType: 'custom_service',
      id: 'custom_service_2',
      title: 'otel.http.duration'
    })
  }),
  http.post(AUTOCOMPLETE_URL, () =>
    HttpResponse.json({ choices: [{ id: 'web01', value: 'web01' }] })
  ),
  http.post(METRIC_NAMES_URL, () =>
    HttpResponse.json({ choices: [{ name: 'otel.http.duration', types: ['sum'] }] })
  ),
  http.post(TEMPLATE_ATTRIBUTES_URL, () => {
    templateAttributesRequests += 1
    return HttpResponse.json({ availability: 'available', attributes: [], truncated: false })
  }),
  http.post(RESOLVE_URL, () =>
    HttpResponse.json({
      matching_hosts: ['cart'],
      unmatched_host_names: [],
      hidden_match_count: 0,
      truncated: false
    })
  ),
  http.post(GRAPH_DATA_URL, () =>
    HttpResponse.json({
      time_range: { start: 0, end: 3600, step: 60 },
      metrics: [],
      group_titles: [],
      horizontal_lines: [],
      warnings: [],
      errors: [],
      internal: '{"graphs":[]}'
    })
  )
)

beforeEach(() => {
  resetGlobalTimeState()
})

afterEach(() => {
  cleanup()
  resetGlobalTimeState()
  updateRequests = 0
  createRequests = 0
  templateAttributesRequests = 0
  lastBody = null
  lastIfMatch = null
  window.history.replaceState(null, '', window.location.pathname)
})

function renderWizard(
  configurationName: string | null = 'http_duration_on_web01',
  createAlertUrl: string | null = null
) {
  return render(CustomServicesWizardApp, {
    props: {
      activate_changes_url: 'wato.py?mode=changelog',
      configuration_name: configurationName,
      create_alert_url: createAlertUrl,
      time_picker: {
        custom_time_ranges: [],
        default_time_range: 4 * 3600,
        server_time_zone: 'UTC',
        first_day_of_week: null,
        refresh: {
          interval_seconds: null,
          interval_choices_seconds: [30, 60],
          starts_live: true,
          reloads_page_content: false
        }
      }
    },
    global: { stubs: { TimeSeriesGraph: true } }
  })
}

async function expectActiveStep(heading: string): Promise<void> {
  await waitFor(() =>
    expect(screen.getByText(heading).closest('li')?.getAttribute('aria-current')).toBe('step')
  )
}

async function goToHostStep(): Promise<void> {
  await expectActiveStep('Define metric')
  await userEvent.click(await screen.findByRole('button', { name: 'Next step' }))
  await expectActiveStep('Assign to host')
}

// A fragment, as jsdom only follows those, so the page the wizard went on to shows in the hash.
const CREATE_ALERT_URL = '#create_otel_alert'

function renderNewServiceWizard(createAlertUrl: string | null = CREATE_ALERT_URL) {
  return renderWizard(null, createAlertUrl)
}

// Takes the suggested configuration name, picks the metric and assigns the service to web01.
async function goToHostStepOfNewService(): Promise<void> {
  await expectActiveStep('General configuration properties')
  const nameInput = await screen.findByRole('textbox', { name: /Configuration name/ })
  await waitFor(() => expect(nameInput).not.toHaveValue(''))
  await userEvent.click(screen.getByRole('button', { name: 'Next step' }))
  await expectActiveStep('Define metric')
  await userEvent.click(await screen.findByRole('combobox', { name: 'Metric name' }))
  await userEvent.click(await screen.findByText('otel.http.duration (sum)'))
  await userEvent.click(await screen.findByRole('button', { name: 'Next step' }))
  await expectActiveStep('Assign to host')
  const hostSelect = await screen.findByRole('combobox', { name: 'Select host' })
  await waitFor(() => expect(hostSelect).toBeEnabled())
  void userEvent.click(hostSelect)
  await userEvent.click(await screen.findByRole('option', { name: 'web01' }))
}

test('starts at the metric step without the configuration name step', async () => {
  renderWizard()

  await expectActiveStep('Define metric')
  expect(screen.queryByText('General configuration properties')).toBeNull()
  expect(screen.queryByRole('button', { name: 'Previous step' })).toBeNull()
})

test('shows the stored service name, editable', async () => {
  renderWizard()
  await goToHostStep()

  const input = await screen.findByDisplayValue('HTTP duration')
  await userEvent.clear(input)
  await userEvent.type(input, 'Latency')

  expect(screen.getByDisplayValue('Latency')).toBeTruthy()
})

test('shows the stored host', async () => {
  renderWizard()
  await goToHostStep()

  expect(await screen.findAllByText('web01')).not.toHaveLength(0)
})

test('finishing writes the stored service back with the etag it was loaded with', async () => {
  renderWizard()
  await goToHostStep()

  await userEvent.click(await screen.findByRole('button', { name: 'Save & activate changes' }))

  await waitFor(() => expect(updateRequests).toBe(1))
  expect(lastIfMatch).toBe('etag-1')
  expect(lastBody).toEqual(WRITTEN_EXTENSIONS)
})

test('finishing writes the edited service name', async () => {
  renderWizard()
  await goToHostStep()
  const input = await screen.findByDisplayValue('HTTP duration')
  await userEvent.clear(input)
  await userEvent.type(input, 'Latency')

  await userEvent.click(await screen.findByRole('button', { name: 'Save & activate changes' }))

  await waitFor(() => expect(updateRequests).toBe(1))
  expect(lastBody).toEqual({
    ...WRITTEN_EXTENSIONS,
    configuration: { ...WRITTEN_EXTENSIONS.configuration, service_name_template: 'Latency' }
  })
})

test('a service that cannot be loaded shows the reason instead of the wizard', async () => {
  server.use(
    http.get(OBJECT_URL, () =>
      HttpResponse.json(
        {
          status: 404,
          title: 'Custom service not readable',
          detail: 'Its generated rule no longer exists.'
        },
        { status: 404 }
      )
    )
  )
  renderWizard()

  expect(await screen.findByText(/rule no longer exists/)).toBeTruthy()
  expect(screen.queryByRole('button', { name: 'Next step' })).toBeNull()
})

test('without a configuration name the wizard creates instead of saving', async () => {
  renderWizard(null)

  await expectActiveStep('General configuration properties')
  expect(screen.queryByRole('button', { name: 'Save & activate changes' })).toBeNull()
})

const TEMPLATE_ASSIGNMENT = {
  mode: 'host_name_template',
  host_name_template: '$RESOURCE_ATTR.service.name$'
}

function serveStoredTemplateService(): void {
  server.use(
    http.get(OBJECT_URL, () =>
      HttpResponse.json(
        {
          domainType: 'custom_service',
          id: 'http_duration_on_web01',
          title: 'HTTP duration',
          extensions: { ...STORED_EXTENSIONS, host_assignment: TEMPLATE_ASSIGNMENT }
        },
        { headers: { ETag: 'etag-1' } }
      )
    )
  )
}

test('a service assigned by host name template is written back with its template', async () => {
  serveStoredTemplateService()
  renderWizard()
  await goToHostStep()

  expect(await screen.findByDisplayValue('$RESOURCE_ATTR.service.name$')).toBeTruthy()
  expect(await screen.findByText('cart')).toBeTruthy()
  await userEvent.click(await screen.findByRole('button', { name: 'Save & activate changes' }))

  await waitFor(() => expect(updateRequests).toBe(1))
  expect(lastBody).toMatchObject({ host_assignment: TEMPLATE_ASSIGNMENT })
})

test('a refused host name template is shown at the template field', async () => {
  serveStoredTemplateService()
  server.use(
    http.put(OBJECT_URL, () =>
      HttpResponse.json(
        {
          status: 400,
          title: 'Bad Request',
          detail: 'These fields have problems: body.host_assignment.host_name_template',
          fields: {
            'body.host_assignment.host_name_template.host_name_template': {
              type: 'value_error',
              loc: ['body', 'host_assignment', 'host_name_template', 'host_name_template'],
              msg: "Value error, The host name template must not start with '.'.",
              input: '.$RESOURCE_ATTR.service.name$'
            }
          }
        },
        { status: 400 }
      )
    )
  )
  renderWizard()
  await goToHostStep()
  await screen.findByText('cart')

  await userEvent.click(await screen.findByRole('button', { name: 'Save & activate changes' }))

  expect(await screen.findByText("The host name template must not start with '.'.")).toBeTruthy()
  expect(screen.queryByText(/These fields have problems/)).toBeNull()
})

test('a service assigned by host name template asks for its attributes only at the host step', async () => {
  serveStoredTemplateService()
  renderWizard()
  await expectActiveStep('Define metric')
  await new Promise((resolve) => setTimeout(resolve, 100))

  expect(templateAttributesRequests).toBe(0)

  await goToHostStep()

  await waitFor(() => expect(templateAttributesRequests).toBe(1))
})

test('a host name template that matches no host cannot be saved', async () => {
  serveStoredTemplateService()
  server.use(
    http.post(RESOLVE_URL, () =>
      HttpResponse.json({
        matching_hosts: [],
        unmatched_host_names: ['crat'],
        hidden_match_count: 0,
        truncated: false
      })
    )
  )
  renderWizard()
  await goToHostStep()

  expect(await screen.findByText(/No configured host currently matches/)).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Save & activate changes' })).toBeDisabled()
})

test('a user who may not add alerts is not offered to add one', async () => {
  renderNewServiceWizard(null)
  await goToHostStepOfNewService()

  expect(await screen.findByRole('button', { name: 'Create & activate changes' })).toBeTruthy()
  expect(screen.queryByRole('button', { name: 'Create & add alert' })).toBeNull()
})

test('going on to add an alert creates the service, then opens the alert wizard', async () => {
  renderNewServiceWizard()
  await goToHostStepOfNewService()

  await userEvent.click(await screen.findByRole('button', { name: 'Create & add alert' }))

  await waitFor(() => expect(window.location.hash).toBe(CREATE_ALERT_URL))
  expect(createRequests).toBe(1)
})

test('a created service cannot be created again while the next page loads', async () => {
  renderNewServiceWizard()
  await goToHostStepOfNewService()

  await userEvent.click(await screen.findByRole('button', { name: 'Create & add alert' }))

  await waitFor(() => expect(window.location.hash).toBe(CREATE_ALERT_URL))
  expect(screen.getByRole('button', { name: 'Create & add alert' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Create & activate changes' })).toBeDisabled()
})

test('a service that cannot be created stays in the wizard instead of adding an alert', async () => {
  server.use(
    http.post(LIST_URL, () =>
      HttpResponse.json(
        { status: 400, title: 'Bad Request', detail: 'The service name is in use.' },
        { status: 400 }
      )
    )
  )
  renderNewServiceWizard()
  await goToHostStepOfNewService()

  await userEvent.click(await screen.findByRole('button', { name: 'Create & add alert' }))

  expect(await screen.findByText(/The service name is in use/)).toBeTruthy()
  expect(window.location.hash).toBe('')
})
