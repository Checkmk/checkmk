/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { describe, expect, test } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import { untranslated } from '@/lib/i18n'

import FormMetricNameAutocompleter from '@/metric-backend/FormMetricNameAutocompleter.vue'

const METRIC_NAMES_URL = `${location.protocol}//${location.host}/api/internal/domain-types/metric_backend/actions/names_with_types/invoke`

const server = setupServer()

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

interface Choice {
  name: string
  types: string[]
}

function mockNamesWithTypes(choices: Choice[], warning: string | null = null): void {
  server.use(
    http.post(METRIC_NAMES_URL, async ({ request }) => {
      // Mirror the backend, which echoes the raw user input as the first free-text choice.
      const { value } = (await request.json()) as { value: string }
      const echoed =
        value.length > 0 && !choices.some((choice) => choice.name === value)
          ? [{ name: value, types: [] }, ...choices]
          : choices
      return HttpResponse.json({ choices: echoed, warning })
    })
  )
}

function renderFormMetricNameAutocompleter(initialName: string | null = null) {
  const metricName = ref<string | null>(initialName)
  const metricTypes = ref<string[]>([])
  const wrapper = defineComponent({
    setup() {
      return () =>
        h(FormMetricNameAutocompleter, {
          metricName: metricName.value,
          metricTypes: metricTypes.value,
          'onUpdate:metricName': (v: string | null) => (metricName.value = v),
          'onUpdate:metricTypes': (v: string[]) => (metricTypes.value = v),
          label: 'Metric name',
          placeholder: untranslated('Metric name')
        })
    }
  })
  render(wrapper)
  return { metricName, metricTypes }
}

describe('FormMetricNameAutocompleter', () => {
  test('shows the metric name and type(s) in the suggestions and on the selection', async () => {
    mockNamesWithTypes([
      { name: 'cpu', types: ['gauge'] },
      { name: 'requests', types: ['sum', 'gauge'] },
      { name: 'uptime', types: [] }
    ])
    const user = userEvent.setup()
    const { metricName, metricTypes } = renderFormMetricNameAutocompleter()

    await user.click(screen.getByRole('combobox', { name: 'Metric name' }))
    expect(await screen.findByText('cpu (gauge)')).toBeInTheDocument()
    expect(screen.getByText('requests (sum, gauge)')).toBeInTheDocument()
    // A metric without a type renders just its name.
    expect(screen.getByText('uptime')).toBeInTheDocument()

    await user.click(screen.getByText('requests (sum, gauge)'))

    // The selection is reflected both on the closed dropdown button and in the models. The
    // button label is split into truncated spans, so assert on its title attribute.
    expect(await screen.findByTitle('requests (sum, gauge)')).toBeInTheDocument()
    await waitFor(() => expect(metricName.value).toBe('requests'))
    await waitFor(() => expect(metricTypes.value).toEqual(['sum', 'gauge']))
  })

  test('keeps the free-text input available when the backend warns', async () => {
    mockNamesWithTypes([{ name: 'cpu', types: ['gauge'] }], 'Metric backend is disabled.')
    const user = userEvent.setup()
    renderFormMetricNameAutocompleter()

    await user.click(screen.getByRole('combobox', { name: 'Metric name' }))
    expect(await screen.findByText('Metric backend is disabled.')).toBeInTheDocument()

    const input = screen.getByRole('textbox', { name: 'filter' })
    await user.click(input)
    await user.keyboard('my_custom_metric')

    expect(await screen.findByText('my_custom_metric')).toBeInTheDocument()
  })

  test('shows an error when the request fails', async () => {
    server.use(
      http.post(METRIC_NAMES_URL, () =>
        HttpResponse.json({ title: 'Error', detail: 'boom' }, { status: 500 })
      )
    )
    const user = userEvent.setup()
    renderFormMetricNameAutocompleter()

    await user.click(screen.getByRole('combobox', { name: 'Metric name' }))
    expect(await screen.findByText('Error: boom')).toBeInTheDocument()
  })

  test('shows the metric name and type(s) when loading a saved value', async () => {
    mockNamesWithTypes([{ name: 'cpu', types: ['gauge'] }])
    renderFormMetricNameAutocompleter('cpu')

    // Loading a saved form is a distinct path: the dropdown re-queries the preset value on
    // mount to resolve and render its type(s) on the closed button.
    expect(await screen.findByTitle('cpu (gauge)')).toBeInTheDocument()
  })
})
