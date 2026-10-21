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

const TEMPLATE_ATTRIBUTES_URL = `${API_BASE}/domain-types/custom_service/actions/template_attributes/invoke`

let templateAttributesRequest: unknown = null

const server = useMswServer(
  http.post(`${API_BASE}/objects/autocomplete/:ident`, async ({ request }) => {
    const { value: query } = (await request.json()) as { value: string }
    const matching = HOSTS.filter(([, label]) => !query || label.includes(query))
    return HttpResponse.json({ choices: matching.map(([id, value]) => ({ id, value })) })
  }),
  http.post(TEMPLATE_ATTRIBUTES_URL, async ({ request }) => {
    templateAttributesRequest = await request.json()
    return HttpResponse.json({
      availability: 'available',
      attributes: [
        { kind: 'resource', key: 'service.name' },
        { kind: 'data_point', key: 'http.route' }
      ],
      truncated: false
    })
  })
)

afterEach(() => {
  cleanup()
  templateAttributesRequest = null
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
    appendSeriesAttributes = true,
    hostNameTemplate = null,
    templateErrors = []
  }: {
    aggregator?: Aggregator | undefined
    appendSeriesAttributes?: boolean
    hostNameTemplate?: string | null
    templateErrors?: string[]
  } = {}
) {
  const service = ref(serviceName)
  const host = ref<string | null>(hostName)
  const template = ref<string | null>(hostNameTemplate)
  const wrapper = defineComponent({
    components: { AssignHostStep },
    setup() {
      return {
        service,
        host,
        template,
        metricName: 'otel.http.duration',
        consolidation: GAUGE,
        aggregator,
        appendSeriesAttributes,
        templateErrors
      }
    },
    template: `<AssignHostStep
      v-model:service-name="service"
      v-model:host-name="host"
      v-model:host-name-template="template"
      :metric-name="metricName"
      :attribute-filter="undefined"
      :consolidation="consolidation"
      :aggregator="aggregator"
      :append-series-attributes="appendSeriesAttributes"
      :template-errors="templateErrors"
    />`
  })
  render(wrapper)
  return { service, host, template }
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

test('choosing automatic assignment asks for a host name template instead of a host', async () => {
  const { host, template } = renderStep('HTTP duration', 'web01')

  await userEvent.click(screen.getByRole('tab', { name: 'Automatic' }))

  expect(host.value).toBeNull()
  expect(template.value).toBe('')
  expect(screen.getByLabelText('Host name template')).toBeTruthy()
  expect(screen.queryByText('Select host')).toBeNull()
})

test('clicking the active tab keeps the chosen host', async () => {
  const { host } = renderStep('HTTP duration', 'web01')

  await userEvent.click(screen.getByRole('tab', { name: 'Manual' }))

  expect(host.value).toBe('web01')
})

test('edits the host name template', async () => {
  const { template } = renderStep('HTTP duration', null, { hostNameTemplate: '' })

  await userEvent.type(
    screen.getByLabelText('Host name template'),
    'pod-$RESOURCE_ATTR.k8s.pod.name$'
  )

  expect(template.value).toBe('pod-$RESOURCE_ATTR.k8s.pod.name$')
})

test('switching back to manual assignment discards the host name template', async () => {
  const { template } = renderStep('HTTP duration', null, {
    hostNameTemplate: '$RESOURCE_ATTR.service.name$'
  })

  await userEvent.click(screen.getByRole('tab', { name: 'Manual' }))

  expect(template.value).toBeNull()
  expect(screen.queryByLabelText('Host name template')).toBeNull()
})

test('shows why the host name template was refused at the template field', () => {
  renderStep('HTTP duration', null, {
    hostNameTemplate: 'fixed-name',
    templateErrors: ['The host name template must reference at least one attribute.']
  })

  expect(
    screen.getByText('The host name template must reference at least one attribute.')
  ).toBeTruthy()
})

test('asks for the attributes of the metric step', async () => {
  renderStep('HTTP duration', null, { hostNameTemplate: '' })

  await waitFor(() =>
    expect(templateAttributesRequest).toEqual({
      metric_name: 'otel.http.duration',
      consolidation: GAUGE
    })
  )
})

test('clicking an attribute inserts its placeholder into the host name template', async () => {
  const { template } = renderStep('HTTP duration', null, { hostNameTemplate: 'pod-' })

  await userEvent.click(await screen.findByRole('button', { name: '+ http.route' }))

  expect(template.value).toBe('pod-$DATA_POINT_ATTR.http.route$')
})

test('explains that merged series offer no attribute', async () => {
  server.use(
    http.post(TEMPLATE_ATTRIBUTES_URL, () =>
      HttpResponse.json({ availability: 'series_merged', attributes: [], truncated: false })
    )
  )
  renderStep('HTTP duration', null, { hostNameTemplate: '' })

  expect(await screen.findByText(/combines all series into one/)).toBeTruthy()
})

test('asks for no attributes while the host is assigned by hand', async () => {
  renderStep('HTTP duration', 'web01')

  await screen.findByText('web01')
  expect(templateAttributesRequest).toBeNull()
})
