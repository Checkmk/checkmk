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

import { CONDITIONS_SPEC, FOLDER_PATHS, MAIN_FOLDER } from './conditions-spec'
import { PREDICTION_PERIODS, THRESHOLDS_SPEC } from './thresholds-spec'

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
  render(AlertWizardApp, {
    props: {
      conditions_form: { spec: CONDITIONS_SPEC, data: { folder_path: MAIN_FOLDER } },
      thresholds_form: { spec: THRESHOLDS_SPEC, data: {} },
      folder_paths: FOLDER_PATHS,
      prediction_periods: PREDICTION_PERIODS,
      activate_changes_url: 'wato.py?mode=changelog'
    }
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
