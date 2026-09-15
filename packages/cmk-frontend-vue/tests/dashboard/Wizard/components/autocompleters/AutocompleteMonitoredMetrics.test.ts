/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { Response } from 'cmk-ui-library/components/CmkSuggestions'
import { fetchSuggestions } from 'cmk-ui-library/components/FormAutocompleter/autocompleter'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AutocompleteMonitoredMetrics from '@/dashboard/components/Wizard/components/autocompleters/AutocompleteMonitoredMetrics.vue'
import { useMetric } from '@/dashboard/components/Wizard/wizards/metrics/stage1/MetricSelector/useMetric'

vi.mock('cmk-ui-library/components/FormAutocompleter/autocompleter', () => ({
  fetchSuggestions: vi.fn()
}))

const CHOICES = [{ name: 'util', title: 'CPU utilization' }]

/** Serve the dropdown its options, then leave every later lookup unresolved. */
const freezeLookupAfterFirstCall = (): void => {
  vi.mocked(fetchSuggestions)
    .mockResolvedValueOnce(new Response(CHOICES))
    .mockReturnValue(new Promise(() => {}))
}

const selectTheMetric = async (handler: ReturnType<typeof useMetric>): Promise<void> => {
  render(AutocompleteMonitoredMetrics, {
    props: {
      serviceMetrics: handler.metric.value,
      'onUpdate:serviceMetrics': (value: typeof handler.metric.value) => {
        handler.metric.value = value
      }
    }
  })

  await userEvent.click(screen.getByRole('combobox'))
  await userEvent.click(await screen.findByRole('option', { name: /CPU utilization/ }))
}

describe('AutocompleteMonitoredMetrics', () => {
  beforeEach(() => {
    vi.mocked(fetchSuggestions).mockReset()
  })

  it('validates the selected metric before its label lookup resolves', async () => {
    freezeLookupAfterFirstCall()
    const handler = useMetric()

    await selectTheMetric(handler)

    expect(handler.validate()).toBe(true)
  })

  it('shows no validation error for a metric whose label lookup is still pending', async () => {
    freezeLookupAfterFirstCall()
    const handler = useMetric()

    await selectTheMetric(handler)
    handler.validate()

    expect(handler.metricValidationError.value).toBe(false)
  })
})
