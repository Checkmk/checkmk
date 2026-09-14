/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'

import ModeCreatePrometheusConfApp from '@/mode-otel/ModeCreatePrometheusConfApp.vue'
import { _resetCaches } from '@/mode-otel/otel-configuration-steps/ConfigureGeneralProperties.vue'

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

const API_BASE = `${location.protocol}//${location.host}/api/internal`

const server = setupServer()

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

/**
 * Answer every collection the wizard loads on mount with an empty list. No sites
 * means `siteId` stays null, so step 1's validation fails - the deterministic way
 * to make an overview-mode save bail out before running any post-save action.
 */
function serveEmptyCollections() {
  server.use(
    http.get(`${API_BASE}/domain-types/site_connection/collections/all`, () =>
      HttpResponse.json({ value: [] })
    ),
    http.get(`${API_BASE}/domain-types/otel_collector_config_receivers/collections/all`, () =>
      HttpResponse.json({ value: [] })
    ),
    http.get(`${API_BASE}/domain-types/otel_collector_config_prom_scrape/collections/all`, () =>
      HttpResponse.json({ value: [] })
    ),
    http.get(
      `${API_BASE}/domain-types/passwordstore_password/collections/:entity_type_specifier`,
      () => HttpResponse.json({ value: [] })
    )
  )
}

const VALIDATION_ERROR = 'The form still contains invalid data. Please correct them and try again.'

const PROPS = { activate_changes_url: 'wato.py?mode=changelog' }

function clickModeToggle(mode: 'Guided' | 'Overview') {
  return fireEvent.click(screen.getByRole('button', { name: `Toggle ${mode}` }))
}

function clickSave() {
  return fireEvent.click(screen.getByRole('button', { name: /Save Prometheus configuration/ }))
}

describe('ModeCreatePrometheusConfApp', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
    _resetCaches()
  })

  test('surfaces the validation error when an overview-mode save fails', async () => {
    serveEmptyCollections()
    render(ModeCreatePrometheusConfApp, { props: PROPS })

    await clickModeToggle('Overview')
    await clickSave()

    await waitFor(() => expect(screen.getByText(VALIDATION_ERROR)).toBeInTheDocument())
  })

  test('drops the validation error when switching back to guided mode', async () => {
    serveEmptyCollections()
    render(ModeCreatePrometheusConfApp, { props: PROPS })

    await clickModeToggle('Overview')
    await clickSave()
    await waitFor(() => expect(screen.getByText(VALIDATION_ERROR)).toBeInTheDocument())

    await clickModeToggle('Guided')

    // Guided mode keeps every step's actions slot mounted inside a collapsed
    // CmkCollapsible (v-show), so a stale alert would still be queryable here.
    expect(screen.queryByText(VALIDATION_ERROR)).not.toBeInTheDocument()
  })
})
