/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import type { Aggregator } from 'cmk-shared-typing/typescript/aggregation'
import type { ConsolidationFunction } from 'cmk-shared-typing/typescript/consolidation'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'
import { afterEach, expect, test } from 'vitest'
import { defineComponent, ref } from 'vue'

import AssignHostStep from '@/mode-custom-services/steps/AssignHostStep.vue'

const API_BASE = `${location.protocol}//${location.host}/api/internal`

// Hosts the injected otel_custom_service_host autocompleter offers ("name (ip)"
// label, host name as id — matching the backend autocompleter's Choices shape).
const HOSTS: Array<[string, string]> = [
  ['web01', 'web01 (10.0.0.1)'],
  ['db01', 'db01 (10.0.0.2)']
]

useMswServer(
  http.post(`${API_BASE}/objects/autocomplete/:ident`, async ({ request }) => {
    const { value: query } = (await request.json()) as { value: string }
    const matching = HOSTS.filter(([, label]) => !query || label.includes(query))
    return HttpResponse.json({ choices: matching.map(([id, value]) => ({ id, value })) })
  })
)

afterEach(() => {
  cleanup()
})

const GAUGE: ConsolidationFunction = {
  type: 'gauge',
  function: 'gauge_last',
  lookback_seconds: 120
}

function renderStep(
  serviceName = '',
  hostName: string | null = null,
  {
    aggregator = undefined,
    appendSeriesAttributes = true
  }: { aggregator?: Aggregator | undefined; appendSeriesAttributes?: boolean } = {}
) {
  const service = ref(serviceName)
  const host = ref<string | null>(hostName)
  const wrapper = defineComponent({
    components: { AssignHostStep },
    setup() {
      return { service, host, consolidation: GAUGE, aggregator, appendSeriesAttributes }
    },
    template: `<AssignHostStep
      v-model:service-name="service"
      v-model:host-name="host"
      :consolidation="consolidation"
      :aggregator="aggregator"
      :append-series-attributes="appendSeriesAttributes"
    />`
  })
  render(wrapper)
  return { service, host }
}

test('edits the service name', async () => {
  const { service } = renderStep('HTTP duration')
  const input = screen.getByDisplayValue('HTTP duration')
  await userEvent.clear(input)
  await userEvent.type(input, 'Latency')
  expect(service.value).toBe('Latency')
})

test('selects a host from the injected autocompleter suggestions', async () => {
  const { host } = renderStep('HTTP duration')
  const combobox = await screen.findByRole('combobox')
  await waitFor(() => expect(combobox).toBeEnabled(), { timeout: 10000 })
  void userEvent.click(combobox)
  await userEvent.click(
    await screen.findByRole('option', { name: 'web01 (10.0.0.1)' }, { timeout: 10000 })
  )
  expect(host.value).toBe('web01')
})

test('summarizes the service to be created once a host is chosen', () => {
  renderStep('HTTP duration', 'web01')
  expect(screen.getByText(/Services to be created/)).toHaveTextContent('(1)')
  expect(screen.getByText('web01')).toBeTruthy()
})

test('tells that all attribute values are appended to the service name', () => {
  renderStep('HTTP duration')
  expect(screen.getByText('+ all attributes')).toBeTruthy()
})

test('tells which group-by attribute values are appended to the service name', () => {
  renderStep('HTTP duration', null, {
    aggregator: {
      stages: [
        {
          aggregate_by: [
            { kind: 'data_point', name: 'http.status_code' },
            { kind: 'data_point', name: 'http.method' }
          ],
          aggregation_fn: { type: 'scalar', name: 'avg' }
        }
      ]
    }
  })
  expect(screen.getByText('+ http.method + http.status_code')).toBeTruthy()
})

test('explains that very long service names are shortened', () => {
  renderStep('HTTP duration')
  expect(screen.getByText(/shortened and end in a short hash/)).toBeTruthy()
})

test('a service name without appended attributes shows neither indicator nor explanation', () => {
  renderStep('Pod CPU usage', null, { appendSeriesAttributes: false })
  expect(screen.queryByText('+ all attributes')).toBeNull()
  expect(screen.queryByText(/short hash/)).toBeNull()
})
