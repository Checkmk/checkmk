/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConsolidationFunction } from 'cmk-shared-typing/typescript/consolidation'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
// eslint-disable-next-line no-restricted-imports -- pre-existing violation: type these handlers, never copy this line
import { HttpResponse, http } from 'msw'
import { afterEach, expect, test, vi } from 'vitest'
import { type EffectScope, effectScope, ref } from 'vue'

import {
  type ServicesPreview,
  servicesPreviewBlocksSave,
  useServicesPreview
} from '@/mode-custom-services/servicesPreview'
import { type ServiceModel, emptyService } from '@/mode-custom-services/types'

const API_BASE = `${location.protocol}//${location.host}/api/internal`
const RESOLVE_URL = `${API_BASE}/domain-types/custom_service/actions/resolve_services/invoke`

const SERVICES = {
  services: [{ host_name: 'web01', service_name: 'Latency GET', new_host: false, clash: null }],
  total: 1,
  clashes: [],
  appended_attributes: { all_attributes: true, attributes: [] },
  complete: true
}

let requests: unknown[] = []

const server = useMswServer(
  http.post(RESOLVE_URL, async ({ request }) => {
    requests.push(await request.json())
    return HttpResponse.json(SERVICES)
  })
)

const scopes: EffectScope[] = []

afterEach(() => {
  scopes.splice(0).forEach((scope) => scope.stop())
  requests = []
})

function hostService(overrides: Partial<ServiceModel> = {}): ServiceModel {
  return {
    ...emptyService(),
    metricName: 'http.server.duration',
    serviceName: 'Latency',
    hostName: 'web01',
    ...overrides
  }
}

function mount(
  initial: ServiceModel | null,
  { configurationName = null as string | null, debounceMs = 0, timeoutMs = 10_000 } = {}
) {
  const scope = effectScope()
  scopes.push(scope)
  const model = ref<ServiceModel | null>(initial)
  const { preview } = scope.run(() =>
    useServicesPreview(() => model.value, configurationName, { debounceMs, timeoutMs })
  )!
  return { model, preview }
}

test.each<[string, Partial<ServiceModel>]>([
  ['no host', { hostName: null }],
  ['no service name', { serviceName: ' ' }],
  ['an empty host name template', { hostName: null, hostNameTemplate: '' }],
  [
    'thresholds missing',
    {
      consolidation: {
        type: 'histogram',
        function: 'histogram_fraction_below',
        lookback_seconds: 120
      } as ConsolidationFunction
    }
  ]
])('looks nothing up with %s', async (_, overrides) => {
  const { preview } = mount(hostService(overrides))

  await new Promise((resolve) => setTimeout(resolve, 20))
  expect(preview.value).toEqual({ status: 'idle' })
  expect(requests).toEqual([])
})

test('resolves the services of the host as saving would create them', async () => {
  const { preview } = mount(hostService())

  await vi.waitFor(() => expect(preview.value.status).toBe('resolved'))
  expect(preview.value).toEqual({ status: 'resolved', services: SERVICES })
  expect(requests).toEqual([
    {
      host_assignment: { mode: 'explicit_host', host_name: 'web01' },
      configuration: {
        metric_name: 'http.server.duration',
        service_name_template: 'Latency $SERIES_ATTRIBUTES$',
        consolidation: { type: 'gauge', function: 'gauge_last', lookback_seconds: 120 }
      }
    }
  ])
})

test('names the edited custom service, so it does not clash with itself', async () => {
  mount(hostService(), { configurationName: 'latency' })

  await vi.waitFor(() => expect(requests).toHaveLength(1))
  expect(requests[0]).toMatchObject({ configuration_name: 'latency' })
})

test('a changed service name resolves the services again', async () => {
  const { model, preview } = mount(hostService())
  await vi.waitFor(() => expect(preview.value.status).toBe('resolved'))

  model.value = hostService({ serviceName: 'Duration' })

  await vi.waitFor(() => expect(requests).toHaveLength(2))
  expect(requests[1]).toMatchObject({
    configuration: { service_name_template: 'Duration $SERIES_ATTRIBUTES$' }
  })
})

function answerWith(status: number): void {
  server.use(
    http.post(RESOLVE_URL, () => HttpResponse.json({ title: 'Error', status }, { status }))
  )
}

test.each<[string, number, Partial<ServiceModel>, ServicesPreview['status']]>([
  [
    'a refused template is left to the template preview to explain',
    400,
    { hostName: null, hostNameTemplate: '$SERIES_ID$' },
    'refused'
  ],
  ['a refused explicit host is reported, as no template preview explains it', 400, {}, 'failed'],
  ['a backend failure is reported', 503, {}, 'failed']
])('%s', async (_, status, overrides, expected) => {
  answerWith(status)
  const { preview } = mount(hostService(overrides))

  await vi.waitFor(() => expect(preview.value.status).toBe(expected))
})

const CLASH = { host_name: 'web01', service_name: 'Latency', message: 'clash' }

test.each<[string, ServicesPreview, boolean]>([
  ['idle', { status: 'idle' }, false],
  ['loading', { status: 'loading' }, false],
  ['resolved without clashes', { status: 'resolved', services: SERVICES }, false],
  [
    'resolved with a clash',
    { status: 'resolved', services: { ...SERVICES, clashes: [CLASH] } },
    true
  ],
  ['refused', { status: 'refused' }, false],
  ['failed', { status: 'failed', error: 'down' }, false]
])('a %s preview blocks saving: %s', (_, preview, blocks) => {
  expect(servicesPreviewBlocksSave(preview)).toBe(blocks)
})
