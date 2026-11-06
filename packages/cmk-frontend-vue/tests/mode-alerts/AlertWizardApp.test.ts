/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import { untypedHttp, useMswServer } from 'cmk-ui-library/vitest.msw'
// eslint-disable-next-line no-restricted-imports -- pre-existing violation: type these handlers, never copy this line
import { HttpResponse, http } from 'msw'
import { afterEach, beforeEach, expect, test } from 'vitest'

import { resetGlobalTimeState } from '@/graphing/GlobalTimePicker/globalTimeState'
import AlertWizardApp from '@/mode-alerts/AlertWizardApp.vue'

import { CONDITIONS_SPEC, FOLDER_PATHS, MAIN_FOLDER } from './conditions-spec'
import { PREDICTION_PERIODS, THRESHOLDS_SPEC } from './thresholds-spec'
import { TIME_PICKER } from './time-picker'

const API_BASE = `${location.protocol}//${location.host}/api/internal`
const ENDPOINT = `${API_BASE}/domain-types/service/collections/all`
const CREATE_ENDPOINT = `${API_BASE}/domain-types/telemetry_alert/collections/all`
const PREVIEW_ENDPOINT = `${API_BASE}/domain-types/telemetry_alert/actions/preview_data/invoke`
const ALERT_ENDPOINT = `${API_BASE}/objects/telemetry_alert/:name`

const server = useMswServer(
  http.post(ENDPOINT, () =>
    HttpResponse.json({
      id: 'all',
      links: [],
      value: [{ extensions: { host_name: 'web01', description: 'HTTP request duration' } }]
    })
  ),
  untypedHttp.post(PREVIEW_ENDPOINT, () =>
    HttpResponse.json({
      time_range: { start: 0, end: 3600, step: 60 },
      metrics: [],
      horizontal_lines: [],
      service_units: [],
      notice: null,
      warnings: [],
      errors: []
    })
  )
)

beforeEach(() => {
  resetGlobalTimeState()
})

afterEach(() => {
  cleanup()
  resetGlobalTimeState()
})

function renderApp(configurationName: string | null = null) {
  render(AlertWizardApp, {
    props: {
      configuration_name: configurationName,
      conditions_form: { spec: CONDITIONS_SPEC, data: { folder_path: MAIN_FOLDER } },
      thresholds_form: { spec: THRESHOLDS_SPEC, data: {} },
      folder_paths: FOLDER_PATHS,
      prediction_periods: PREDICTION_PERIODS,
      time_picker: TIME_PICKER,
      warning_color: '#ffd000',
      critical_color: '#ff3232',
      activate_changes_url: 'wato.py?mode=changelog'
    },
    global: { stubs: { TimeSeriesGraph: true } }
  })
}

test('the wizard opens on naming the alert', () => {
  renderApp()

  expect(screen.getByRole('textbox', { name: /Alert name/ })).toBeVisible()
})

test('the service and threshold steps are offered alongside it', () => {
  renderApp()

  expect(screen.getByRole('heading', { name: 'Select services' })).toBeVisible()
  expect(screen.getByRole('heading', { name: 'Define threshold' })).toBeVisible()
})

async function completeNameAndServiceSteps(beforeNext: () => Promise<void> = async () => {}) {
  await userEvent.type(screen.getByRole('textbox', { name: /Alert name/ }), 'Latency too high')
  await userEvent.click(screen.getByRole('button', { name: /next step/i }))

  const serviceName = screen.getByRole('combobox', { name: 'Service name' })
  await waitFor(() => expect(serviceName).toBeEnabled())
  void userEvent.click(serviceName)
  await userEvent.click(await screen.findByRole('option', { name: 'HTTP request duration' }))

  await waitFor(() => {
    expect(screen.getByText('web01')).toBeInTheDocument()
  })
  await beforeNext()

  await userEvent.click(screen.getByRole('button', { name: /next step/i }))
}

test('completing the name and service steps advances to the threshold step', async () => {
  renderApp()

  await completeNameAndServiceSteps()

  await waitFor(() => {
    expect(screen.getByRole('checkbox', { name: 'Upper levels' })).toBeVisible()
  })
})

async function defineUpperLevels(warn: string, crit: string) {
  await userEvent.click(await screen.findByRole('checkbox', { name: 'Upper levels' }))
  if (warn !== '') {
    await userEvent.type(screen.getByRole('spinbutton', { name: 'Warning at' }), warn)
  }
  if (crit !== '') {
    await userEvent.type(screen.getByRole('spinbutton', { name: 'Critical at' }), crit)
  }
}

function captureCreateRequests(): unknown[] {
  const sentBodies: unknown[] = []
  server.use(
    http.post(CREATE_ENDPOINT, async ({ request }) => {
      sentBodies.push(await request.json())
      return HttpResponse.json({})
    })
  )
  return sentBodies
}

test('creating the alert sends its name, service match, conditions and thresholds', async () => {
  const sentBodies = captureCreateRequests()
  renderApp()
  await completeNameAndServiceSteps()
  await defineUpperLevels('80', '90')

  await userEvent.click(screen.getByRole('button', { name: 'Create & activate changes' }))

  await waitFor(() => expect(sentBodies).toHaveLength(1))
  expect(sentBodies).toEqual([
    {
      configuration_name: 'latency_too_high',
      alert_name: 'Latency too high',
      service_match: { mode: 'exact', pattern: 'HTTP request duration' },
      conditions: { folder: '/', host_tags: [], host_label_groups: [] },
      thresholds: { upper: { type: 'fixed', warn: 80, crit: 90 } }
    }
  ])
})

test('an alert cannot be created without thresholds, and the step says why', async () => {
  renderApp()
  await completeNameAndServiceSteps()

  expect(await screen.findByRole('button', { name: 'Create & activate changes' })).toBeDisabled()
  expect(
    screen.getByText('Define at least one threshold: upper levels, lower levels or both.')
  ).toBeVisible()
})

test('defining a threshold allows creating the alert', async () => {
  renderApp()
  await completeNameAndServiceSteps()

  await defineUpperLevels('80', '90')

  expect(screen.getByRole('button', { name: 'Create & activate changes' })).toBeEnabled()
  expect(
    screen.queryByText('Define at least one threshold: upper levels, lower levels or both.')
  ).toBeNull()
})

test('an alert with incomplete levels cannot be created, and the step says why', async () => {
  renderApp()
  await completeNameAndServiceSteps()

  await defineUpperLevels('80', '')

  expect(screen.getByRole('button', { name: 'Create & activate changes' })).toBeDisabled()
  expect(screen.getByText('Fill in the warning and critical levels.')).toBeVisible()
})

test('creating the alert sends the chosen folder', async () => {
  let sentBody: { conditions?: unknown } = {}
  server.use(
    http.post(CREATE_ENDPOINT, async ({ request }) => {
      sentBody = (await request.json()) as { conditions?: unknown }
      return HttpResponse.json({})
    })
  )
  renderApp()
  await completeNameAndServiceSteps(async () => {
    void userEvent.click(screen.getByRole('combobox', { name: 'Folder' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Main/Linux' }))
  })
  await defineUpperLevels('80', '90')

  await userEvent.click(await screen.findByRole('button', { name: 'Create & activate changes' }))

  await waitFor(() => expect(sentBody.conditions).toBeDefined())
  expect(sentBody.conditions).toEqual({ folder: '/linux', host_tags: [], host_label_groups: [] })
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
  await completeNameAndServiceSteps()
  await defineUpperLevels('80', '90')

  await userEvent.click(await screen.findByRole('button', { name: 'Create & activate changes' }))

  expect(await screen.findByText(/already exists/)).toBeVisible()
})

const STORED_ALERT = {
  domainType: 'telemetry_alert',
  id: 'latency_too_high',
  title: 'Latency too high',
  links: [],
  extensions: {
    alert_name: 'Latency too high',
    service_match: { mode: 'exact', pattern: 'HTTP request duration' },
    conditions: { folder: '/linux', host_tags: [], host_label_groups: [] },
    thresholds: { upper: { type: 'fixed', warn: 80, crit: 90 } }
  }
}

function serveStoredAlert() {
  server.use(
    http.get(ALERT_ENDPOINT, () => HttpResponse.json(STORED_ALERT, { headers: { ETag: '"v1"' } }))
  )
}

async function waitForServicesStep() {
  const serviceName = await screen.findByRole('combobox', { name: 'Service name' })
  await waitFor(() => expect(serviceName).toBeEnabled())
}

test('editing an alert does not offer naming it', async () => {
  serveStoredAlert()
  renderApp('latency_too_high')

  await waitForServicesStep()

  // The wizard lists every step by its heading, even while showing another one.
  expect(screen.queryByRole('heading', { name: 'Name the alert' })).toBeNull()
})

test('editing an alert offers no step before its services', async () => {
  serveStoredAlert()
  renderApp('latency_too_high')

  await waitForServicesStep()

  expect(screen.getByRole('button', { name: /next step/i })).toBeVisible()
  expect(screen.queryByRole('button', { name: /previous step/i })).toBeNull()
})

test('editing an alert opens on its services, prefilled', async () => {
  serveStoredAlert()
  renderApp('latency_too_high')

  await waitForServicesStep()

  // The service name's title is looked up like the user's input is, so it shows once found.
  await waitFor(() =>
    expect(screen.getByRole('combobox', { name: 'Service name' })).toHaveTextContent(
      'HTTP request duration'
    )
  )
  expect(screen.getByRole('combobox', { name: 'Folder' })).toHaveTextContent('Main/Linux')
})

test('editing an alert lists the services it matches without changing anything', async () => {
  serveStoredAlert()
  renderApp('latency_too_high')

  await waitForServicesStep()

  expect(await screen.findByText(/Matching services/)).toHaveTextContent('(1)')
  expect(screen.getByText('web01')).toBeInTheDocument()
})

test('saving an edited alert sends the update guarded by its ETag, without its name', async () => {
  serveStoredAlert()
  const sent: { body: unknown; ifMatch: string | null }[] = []
  server.use(
    http.put(ALERT_ENDPOINT, async ({ request }) => {
      sent.push({ body: await request.json(), ifMatch: request.headers.get('If-Match') })
      return HttpResponse.json({})
    })
  )
  renderApp('latency_too_high')
  await waitForServicesStep()
  await userEvent.click(screen.getByRole('button', { name: /next step/i }))

  await userEvent.click(await screen.findByRole('button', { name: 'Save & activate changes' }))

  await waitFor(() => expect(sent).toHaveLength(1))
  expect(sent).toEqual([
    {
      body: {
        service_match: { mode: 'exact', pattern: 'HTTP request duration' },
        conditions: { folder: '/linux', host_tags: [], host_label_groups: [] },
        thresholds: { upper: { type: 'fixed', warn: 80, crit: 90 } }
      },
      ifMatch: '"v1"'
    }
  ])
})

test('an alert that cannot be loaded shows why instead of the wizard', async () => {
  server.use(
    http.get(ALERT_ENDPOINT, () =>
      HttpResponse.json(
        {
          title: 'Alert not found',
          detail: 'No alert named "latency_too_high" exists.',
          status: 404
        },
        { status: 404 }
      )
    )
  )
  renderApp('latency_too_high')

  expect(await screen.findByText(/No alert named/)).toBeVisible()
  expect(screen.queryByRole('heading', { name: 'Select services' })).toBeNull()
})

test('an edit rejected for a concurrent change shows the reason', async () => {
  serveStoredAlert()
  server.use(
    http.put(ALERT_ENDPOINT, () =>
      HttpResponse.json(
        {
          title: 'Precondition failed',
          detail: 'The ETag "\\"v1\\"" is not current.',
          status: 412
        },
        { status: 412 }
      )
    )
  )
  renderApp('latency_too_high')
  await waitForServicesStep()
  await userEvent.click(screen.getByRole('button', { name: /next step/i }))

  await userEvent.click(await screen.findByRole('button', { name: 'Save & activate changes' }))

  expect(await screen.findByText(/is not current/)).toBeVisible()
})

test('an alert in a folder the editor does not offer says so instead of the wizard', async () => {
  const conditions = { ...STORED_ALERT.extensions.conditions, folder: '/hidden' }
  server.use(
    http.get(ALERT_ENDPOINT, () =>
      HttpResponse.json(
        { ...STORED_ALERT, extensions: { ...STORED_ALERT.extensions, conditions } },
        { headers: { ETag: '"v1"' } }
      )
    )
  )
  renderApp('latency_too_high')

  expect(await screen.findByText(/uses conditions the editor cannot show/)).toBeVisible()
  expect(screen.queryByRole('heading', { name: 'Select services' })).toBeNull()
})

test('an alert loaded without a version identifier says so instead of the wizard', async () => {
  server.use(http.get(ALERT_ENDPOINT, () => HttpResponse.json(STORED_ALERT)))
  renderApp('latency_too_high')

  expect(await screen.findByText(/without a version identifier/)).toBeVisible()
  expect(screen.queryByRole('heading', { name: 'Select services' })).toBeNull()
})
