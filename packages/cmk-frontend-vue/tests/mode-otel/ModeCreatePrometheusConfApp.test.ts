/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/vue'
import * as cmkFetch from 'cmk-ui-library/lib/cmkFetch'

import ModeCreatePrometheusConfApp from '@/mode-otel/ModeCreatePrometheusConfApp.vue'
import { _resetCaches } from '@/mode-otel/otel-configuration-steps/ConfigureGeneralProperties.vue'

const VALIDATION_ERROR = 'The form still contains invalid data. Please correct them and try again.'

const PROPS = { activate_changes_url: 'wato.py?mode=changelog' }

/**
 * Answer every collection the wizard loads on mount with an empty list. No sites
 * means `siteId` stays null, so step 1's validation fails - the deterministic way
 * to make an overview-mode save bail out before running any post-save action.
 */
function mockEmptyCollections() {
  return vi.spyOn(cmkFetch, 'fetchRestAPIDeprecated').mockResolvedValue({
    raiseForStatus: vi.fn().mockResolvedValue(undefined),
    json: vi.fn().mockResolvedValue({ value: [] })
  } as unknown as cmkFetch.CmkFetchResponse)
}

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
    mockEmptyCollections()
    render(ModeCreatePrometheusConfApp, { props: PROPS })

    await clickModeToggle('Overview')
    await clickSave()

    await waitFor(() => expect(screen.getByText(VALIDATION_ERROR)).toBeInTheDocument())
  })

  test('drops the validation error when switching back to guided mode', async () => {
    mockEmptyCollections()
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
