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
// eslint-disable-next-line no-restricted-imports -- pre-existing violation: type these handlers, never copy this line
import { HttpResponse, http } from 'msw'
import { afterEach, expect, test } from 'vitest'
import { defineComponent, nextTick, ref } from 'vue'

import type { ServicesPreview } from '@/mode-custom-services/servicesPreview'
import AssignHostStep from '@/mode-custom-services/steps/AssignHostStep.vue'
import type { TemplatePreview } from '@/mode-custom-services/templatePreview'

const API_BASE = `${location.protocol}//${location.host}/api/internal`

// Hosts the injected otel_custom_service_host autocompleter offers ("name (ip)"
// label, host name as id — matching the backend autocompleter's Choices shape).
const HOSTS: Array<[string, string]> = [
  ['web01', 'web01 (10.0.0.1)'],
  ['db01', 'db01 (10.0.0.2)']
]

const TEMPLATE_ATTRIBUTES_URL = `${API_BASE}/domain-types/custom_service/actions/template_attributes/invoke`
const OPENTELEMETRY_DATA_URL = `${API_BASE}/domain-types/custom_service/actions/opentelemetry_data/invoke`

function openTelemetryDataHandler(state: 'enabled' | 'to_enable') {
  return http.post(OPENTELEMETRY_DATA_URL, async ({ request }) => {
    const { host_names: hostNames } = (await request.json()) as { host_names: string[] }
    return HttpResponse.json({
      hosts: hostNames.map((hostName) => ({
        host_name: hostName,
        opentelemetry_data: state,
        dcd_connection: null
      }))
    })
  })
}

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
  }),
  openTelemetryDataHandler('enabled')
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
    templateErrors = [],
    templatePreview = { status: 'idle' },
    servicesPreview = { status: 'idle' }
  }: {
    aggregator?: Aggregator | undefined
    appendSeriesAttributes?: boolean
    hostNameTemplate?: string | null
    templateErrors?: string[]
    templatePreview?: TemplatePreview
    servicesPreview?: ServicesPreview
  } = {}
) {
  const service = ref(serviceName)
  const host = ref<string | null>(hostName)
  const template = ref<string | null>(hostNameTemplate)
  const preview = ref<ServicesPreview>(servicesPreview)
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
        templateErrors,
        templatePreview,
        preview
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
      :template-preview="templatePreview"
      :services-preview="preview"
    />`
  })
  render(wrapper)
  return { service, host, template, preview }
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

const WEB01_SERVICE: ServicesPreview = {
  status: 'resolved',
  services: {
    services: [
      { host_name: 'web01', service_name: 'HTTP duration GET', new_host: false, clash: null }
    ],
    total: 1,
    clashes: [],
    appended_attributes: { all_attributes: true, attributes: [] },
    complete: true
  }
}

test('lists the services to be created below the tabs', () => {
  renderStep('HTTP duration', 'web01', { servicesPreview: WEB01_SERVICE })

  const service = screen.getByText('HTTP duration GET')
  expect(screen.getByText(/Services to be created/)).toHaveTextContent('(1)')
  expect(screen.getByRole('tabpanel').contains(service)).toBe(false)
})

function appending(
  allAttributes: boolean,
  dataPointKeys: string[] = []
): Extract<ServicesPreview, { status: 'resolved' }> {
  return {
    status: 'resolved',
    services: {
      services: [],
      total: 0,
      clashes: [],
      appended_attributes: {
        all_attributes: allAttributes,
        attributes: dataPointKeys.map((key) => ({ kind: 'data_point', key }))
      },
      complete: true
    }
  }
}

async function appendedAttributesHelp(): Promise<HTMLElement> {
  await userEvent.click(screen.getByRole('button', { name: 'About the appended attributes' }))
  return screen.findByRole('tooltip')
}

test('tells that all attribute values are appended to the service name', () => {
  renderStep('HTTP duration', null, { servicesPreview: appending(true) })

  expect(screen.getByText('+ all attributes')).toBeTruthy()
})

test('explains which values of ungrouped series are left out', async () => {
  renderStep('HTTP duration', null, { servicesPreview: appending(true) })

  expect(await appendedAttributesHelp()).toHaveTextContent(
    /part of the host name, fixed by the filter or already shown in the name are left out/
  )
})

test('names the one grouped attribute whose value is appended', () => {
  renderStep('HTTP duration', null, { servicesPreview: appending(false, ['http.route']) })

  expect(screen.getByText('+ http.route')).toBeTruthy()
})

test('explains which grouped attribute value is appended', async () => {
  renderStep('HTTP duration', null, { servicesPreview: appending(false, ['http.route']) })

  expect(await appendedAttributesHelp()).toHaveTextContent(
    /value of the grouped attribute http\.route is appended/
  )
})

test('sums up several grouped attributes whose values are appended', () => {
  renderStep('HTTP duration', null, {
    servicesPreview: appending(false, ['http.method', 'http.route'])
  })

  expect(screen.getByText('+ grouped attributes')).toBeTruthy()
})

test('lists the grouped attributes whose values are appended', async () => {
  renderStep('HTTP duration', null, {
    servicesPreview: appending(false, ['http.method', 'http.route'])
  })

  expect(await appendedAttributesHelp()).toHaveTextContent('(http.method, http.route)')
})

test('tells apart grouped attributes of different kinds sharing a key', async () => {
  renderStep('HTTP duration', null, {
    servicesPreview: {
      status: 'resolved',
      services: {
        services: [],
        total: 0,
        clashes: [],
        appended_attributes: {
          all_attributes: false,
          attributes: [
            { kind: 'data_point', key: 'service.name' },
            { kind: 'resource', key: 'service.name' }
          ]
        },
        complete: true
      }
    }
  })

  expect(await appendedAttributesHelp()).toHaveTextContent(
    '($DATA_POINT_ATTR.service.name$, $RESOURCE_ATTR.service.name$)'
  )
})

test('explains that very long service names are shortened', async () => {
  renderStep('HTTP duration', null, { servicesPreview: appending(false, ['http.route']) })

  expect(await appendedAttributesHelp()).toHaveTextContent(/shortened and end in a short hash/)
})

test('explains that nothing is appended when no attribute is left to append', async () => {
  renderStep('Pod CPU usage', null, { servicesPreview: appending(false) })

  expect(screen.queryByText(/^\+ /)).toBeNull()
  expect(await appendedAttributesHelp()).toHaveTextContent(/Nothing is appended to this name/)
})

test('guesses from the grouping what is appended until the services resolve', () => {
  renderStep('HTTP duration', null, {
    aggregator: {
      stages: [
        {
          aggregate_by: [{ kind: 'data_point', name: 'http.route' }],
          aggregation_fn: { type: 'scalar', name: 'avg' }
        }
      ]
    }
  })

  expect(screen.getByText('+ http.route')).toBeTruthy()
})

test('guesses that ungrouped series append all attributes until the services resolve', () => {
  renderStep('HTTP duration')

  expect(screen.getByText('+ all attributes')).toBeTruthy()
})

test('guesses that a name without series attributes appends nothing', async () => {
  renderStep('HTTP duration', null, { appendSeriesAttributes: false })

  expect(screen.queryByText(/^\+ /)).toBeNull()
  expect(await appendedAttributesHelp()).toHaveTextContent(/Nothing is appended to this name/)
})

test('keeps telling what is appended while the services are looked up again', async () => {
  const { preview } = renderStep('HTTP duration', null, {
    servicesPreview: appending(false, ['http.route'])
  })

  preview.value = { status: 'loading' }
  await nextTick()

  expect(screen.getByText('+ http.route')).toBeTruthy()
})

test('keeps telling what is appended while the services are looked up for a chosen folder', async () => {
  const { services } = appending(false, ['http.route'])
  const { preview } = renderStep('HTTP duration', null, {
    servicesPreview: { status: 'resolved', services }
  })

  preview.value = { status: 'refreshing', services }
  await nextTick()

  expect(screen.getByText('+ http.route')).toBeTruthy()
})

test('tells what the next answer appends once the services are looked up again', async () => {
  const { preview } = renderStep('HTTP duration', null, {
    servicesPreview: appending(false, ['http.route'])
  })

  preview.value = { status: 'loading' }
  await nextTick()
  preview.value = appending(false, ['http.method'])
  await nextTick()

  expect(screen.getByText('+ http.method')).toBeTruthy()
  expect(screen.queryByText('+ http.route')).toBeNull()
})

test('guesses from the grouping again when the services cannot be looked up', async () => {
  const { preview } = renderStep('HTTP duration', null, {
    servicesPreview: appending(false, ['http.route'])
  })

  preview.value = { status: 'failed', error: 'down' }
  await nextTick()

  expect(screen.getByText('+ all attributes')).toBeTruthy()
})

test('choosing automatic assignment asks for a host name template instead of a host', async () => {
  const { host, template } = renderStep('HTTP duration', 'web01')

  await userEvent.click(screen.getByRole('tab', { name: 'Automatic' }))

  expect(host.value).toBeNull()
  expect(template.value).toBe('')
  expect(screen.getByLabelText(/^Host name template/)).toBeTruthy()
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
    screen.getByLabelText(/^Host name template/),
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
  expect(screen.queryByLabelText(/^Host name template/)).toBeNull()
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
  renderStep('HTTP duration', 'web01', { servicesPreview: WEB01_SERVICE })

  await screen.findByText('HTTP duration GET')
  expect(templateAttributesRequest).toBeNull()
})

test('names the hosts the template matches below the tabs', () => {
  renderStep('HTTP duration', null, {
    hostNameTemplate: 'pod-$RESOURCE_ATTR.k8s.pod.name$',
    templatePreview: {
      status: 'resolved',
      resolution: {
        matching_hosts: ['pod-cart', 'pod-search'],
        unmatched_host_names: [],
        hidden_match_count: 0,
        truncated: false,
        creatable_folders: [{ path: '/', title: 'Main' }],
        host_creation_refusal: null
      }
    }
  })

  const targetHosts = screen.getByText(/Target hosts:/)
  expect(targetHosts).toHaveTextContent('Target hosts: pod-cart, pod-search')
  expect(screen.getByRole('tabpanel').contains(targetHosts)).toBe(false)
})

test('tells that saving enables OpenTelemetry data on the chosen host', async () => {
  server.use(openTelemetryDataHandler('to_enable'))

  renderStep('HTTP duration', 'web01')

  expect(
    await screen.findByText('OpenTelemetry data will be enabled on web01 when you save.')
  ).toBeTruthy()
})

test('tells that saving enables OpenTelemetry data on the hosts the template matches', async () => {
  server.use(openTelemetryDataHandler('to_enable'))

  renderStep('HTTP duration', null, {
    hostNameTemplate: 'pod-$RESOURCE_ATTR.k8s.pod.name$',
    templatePreview: {
      status: 'resolved',
      resolution: {
        matching_hosts: ['pod-cart', 'pod-search'],
        unmatched_host_names: [],
        hidden_match_count: 0,
        truncated: false,
        creatable_folders: [{ path: '/', title: 'Main' }],
        host_creation_refusal: null
      }
    }
  })

  expect(
    await screen.findByText(
      'OpenTelemetry data will be enabled on pod-cart, pod-search when you save.'
    )
  ).toBeTruthy()
})
