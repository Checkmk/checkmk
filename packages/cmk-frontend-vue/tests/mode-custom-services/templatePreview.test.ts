/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, delay, http } from 'msw'
import { afterEach, expect, test, vi } from 'vitest'
import { type EffectScope, effectScope, nextTick, ref } from 'vue'

import { useHostNameTemplatePreview } from '@/mode-custom-services/templatePreview'
import { type ServiceModel, emptyService } from '@/mode-custom-services/types'

const API_BASE = `${location.protocol}//${location.host}/api/internal`
const RESOLVE_URL = `${API_BASE}/domain-types/custom_service/actions/resolve_host_name_template/invoke`

const RESOLUTION = {
  matching_hosts: ['pod-cart'],
  unmatched_host_names: ['pod-search'],
  hidden_match_count: 0,
  truncated: false
}

let requests: unknown[] = []

const server = useMswServer(
  http.post(RESOLVE_URL, async ({ request }) => {
    requests.push(await request.json())
    return HttpResponse.json(RESOLUTION)
  })
)

const scopes: EffectScope[] = []

afterEach(() => {
  scopes.splice(0).forEach((scope) => scope.stop())
  requests = []
})

function templateService(hostNameTemplate: string | null): ServiceModel {
  return { ...emptyService(), metricName: 'k8s.pod.cpu.usage', hostNameTemplate }
}

function mount(initial: ServiceModel | null, { debounceMs = 0, timeoutMs = 10_000 } = {}) {
  const scope = effectScope()
  scopes.push(scope)
  const model = ref<ServiceModel | null>(initial)
  const { preview, refresh } = scope.run(() =>
    useHostNameTemplatePreview(() => model.value, { debounceMs, timeoutMs })
  )!
  return { model, preview, refresh }
}

test('looks nothing up without a host name template', async () => {
  const { preview } = mount(templateService(''))

  await new Promise((resolve) => setTimeout(resolve, 20))
  expect(preview.value).toEqual({ status: 'idle' })
  expect(requests).toEqual([])
})

test('looks nothing up without a model', () => {
  const { preview } = mount(null)

  expect(preview.value).toEqual({ status: 'idle' })
})

test('resolves the template of the metric', async () => {
  const { preview } = mount(templateService('pod-$RESOURCE_ATTR.k8s.pod.name$'))

  await vi.waitFor(() => expect(preview.value.status).toBe('resolved'))
  expect(preview.value).toEqual({ status: 'resolved', resolution: RESOLUTION })
  expect(requests).toEqual([
    { metric_name: 'k8s.pod.cpu.usage', host_name_template: 'pod-$RESOURCE_ATTR.k8s.pod.name$' }
  ])
})

test('sends the attribute filter of the metric step', async () => {
  const filter = {
    type: 'equals',
    key: { kind: 'resource', name: 'k8s.namespace.name' },
    value: 'shop'
  } as const
  mount({ ...templateService('$RESOURCE_ATTR.k8s.pod.name$'), attributeFilter: filter })

  await vi.waitFor(() => expect(requests).toHaveLength(1))
  expect(requests[0]).toMatchObject({ attribute_filter: filter })
})

test('an edit drops the previous list at once and waits for the typing to stop', async () => {
  const { model, preview } = mount(templateService('pod-$RESOURCE_ATTR.k8s.pod.name$'), {
    debounceMs: 200
  })
  await vi.waitFor(() => expect(preview.value.status).toBe('resolved'))

  model.value = templateService('pod-$RESOURCE_ATTR.k8s.pod.uid$')
  await nextTick()
  expect(preview.value.status).toBe('loading')

  await new Promise((resolve) => setTimeout(resolve, 100))
  model.value = templateService('pod-$RESOURCE_ATTR.k8s.pod.ip$')
  await new Promise((resolve) => setTimeout(resolve, 150))
  expect(requests).toHaveLength(1)

  await vi.waitFor(() => expect(preview.value.status).toBe('resolved'))
  expect(requests).toHaveLength(2)
  expect(requests[1]).toMatchObject({ host_name_template: 'pod-$RESOURCE_ATTR.k8s.pod.ip$' })
})

test('the same filter with its keys in another order looks nothing up again', async () => {
  const template = '$RESOURCE_ATTR.k8s.pod.name$'
  const { model, preview } = mount({
    ...templateService(template),
    attributeFilter: {
      type: 'equals',
      key: { kind: 'resource', name: 'k8s.namespace.name' },
      value: 'shop'
    }
  })
  await vi.waitFor(() => expect(preview.value.status).toBe('resolved'))

  model.value = {
    ...templateService(template),
    attributeFilter: {
      value: 'shop',
      key: { name: 'k8s.namespace.name', kind: 'resource' },
      type: 'equals'
    }
  }
  await new Promise((resolve) => setTimeout(resolve, 20))

  expect(preview.value.status).toBe('resolved')
  expect(requests).toHaveLength(1)
})

test('a superseded lookup is dropped, not reported as failed', async () => {
  server.use(
    http.post(RESOLVE_URL, async ({ request }) => {
      const body = (await request.json()) as { host_name_template: string }
      await delay(body.host_name_template.startsWith('slow-') ? 'infinite' : 50)
      return HttpResponse.json(RESOLUTION)
    })
  )
  const { model, preview } = mount(templateService('slow-$RESOURCE_ATTR.k8s.pod.name$'))
  await new Promise((resolve) => setTimeout(resolve, 20))

  model.value = templateService('pod-$RESOURCE_ATTR.k8s.pod.name$')
  await new Promise((resolve) => setTimeout(resolve, 20))

  expect(preview.value).toEqual({ status: 'loading' })
  await vi.waitFor(() =>
    expect(preview.value).toEqual({ status: 'resolved', resolution: RESOLUTION })
  )
})

test('refresh looks the template up again', async () => {
  const { preview, refresh } = mount(templateService('pod-$RESOURCE_ATTR.k8s.pod.name$'))
  await vi.waitFor(() => expect(preview.value.status).toBe('resolved'))

  refresh()

  expect(preview.value.status).toBe('loading')
  await vi.waitFor(() => expect(preview.value.status).toBe('resolved'))
  expect(requests).toHaveLength(2)
})

test('a backend failure is reported', async () => {
  server.use(
    http.post(RESOLVE_URL, () =>
      HttpResponse.json(
        {
          status: 503,
          title: 'Data backend unavailable',
          detail: 'The data backend is not reachable.'
        },
        { status: 503 }
      )
    )
  )
  const { preview } = mount(templateService('pod-$RESOURCE_ATTR.k8s.pod.name$'))

  await vi.waitFor(() => expect(preview.value.status).toBe('failed'))
  expect(preview.value).toEqual({
    status: 'failed',
    error: 'Data backend unavailable: The data backend is not reachable.'
  })
})

test('a refused template is reported with the reason only', async () => {
  server.use(
    http.post(RESOLVE_URL, () =>
      HttpResponse.json(
        {
          status: 400,
          title: 'Bad Request',
          detail: 'These fields have problems: body.host_name_template',
          fields: {
            'body.host_name_template': {
              type: 'value_error',
              loc: ['body', 'host_name_template'],
              msg: "Value error, The host name template must not start with '.'.",
              input: '.pod'
            }
          }
        },
        { status: 400 }
      )
    )
  )
  const { preview } = mount(templateService('.pod'))

  await vi.waitFor(() => expect(preview.value.status).toBe('failed'))
  expect(preview.value).toEqual({
    status: 'failed',
    error: "The host name template must not start with '.'."
  })
})

test('a lookup that takes too long is reported', async () => {
  server.use(http.post(RESOLVE_URL, () => delay('infinite')))
  const { preview } = mount(templateService('pod-$RESOURCE_ATTR.k8s.pod.name$'), {
    timeoutMs: 20
  })

  await vi.waitFor(() => expect(preview.value.status).toBe('failed'))
  expect(preview.value).toEqual({
    status: 'failed',
    error: 'Looking up the matching hosts took too long.'
  })
})
