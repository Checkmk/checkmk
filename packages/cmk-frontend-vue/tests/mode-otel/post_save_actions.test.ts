/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Mock } from 'vitest'

import * as cmkFetch from '@/lib/cmkFetch'

import { configEntityAPI } from '@/components/user-input/CmkConfigurationEntityDropdown'

import type { PasswordConfig } from '@/mode-otel/otel-configuration-steps/password_store_password.types.ts'
import {
  POST_SAVE_ACTIONS,
  createOTelReceiverConfigAction,
  createPrometheusScrapeConfigAction
} from '@/mode-otel/otel-configuration-steps/post_save_actions.ts'

function makePasswordConfig(id: string, title = id): PasswordConfig {
  return {
    general_props: { id, title, comment: '', docu_url: '' },
    password_props: {
      password: 'secret',
      owned_by: ['admins', null],
      share_with: []
    }
  }
}

function makeFetchResponse(status: number, body: unknown = null): cmkFetch.CmkFetchResponse {
  return {
    status,
    raiseForStatus: vi.fn(async () => {
      if (status >= 200 && status <= 299) {
        return
      }
      const err = new Error(
        typeof body === 'object' && body !== null && 'title' in body && 'detail' in body
          ? `${(body as { title: string }).title}: ${(body as { detail: string }).detail}`
          : `HTTP ${status}`
      )
      throw err
    }),
    json: vi.fn().mockResolvedValue(body)
  } as unknown as cmkFetch.CmkFetchResponse
}

describe('POST_SAVE_ACTIONS', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  test('enableCollector action is present as the first registry entry', () => {
    expect(POST_SAVE_ACTIONS.length).toBeGreaterThanOrEqual(2)
    expect(POST_SAVE_ACTIONS[0]!.key).toBe('enableCollector')
    expect(POST_SAVE_ACTIONS[0]!.label()).toBe('OpenTelemetry Collector activation')
  })

  test('enableMetricBackend action is present as the second registry entry', () => {
    expect(POST_SAVE_ACTIONS[1]!.key).toBe('enableMetricBackend')
    expect(POST_SAVE_ACTIONS[1]!.label()).toBe('Metric backend connection')
  })

  describe('enableCollector.execute', () => {
    test('PUTs to the collector update endpoint with the selected site', async () => {
      const spy = vi.spyOn(cmkFetch, 'fetchRestAPI').mockResolvedValue(makeFetchResponse(204))

      const action = POST_SAVE_ACTIONS.find((a) => a.key === 'enableCollector')!
      const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

      expect(result.ok).toBe(true)
      expect(spy).toHaveBeenCalledWith(
        'api/internal/domain-types/otel_collector/actions/update/invoke',
        'PUT',
        { site_id: 'prod', activation: { mode: 'enabled' } }
      )
    })

    test('returns a structured error when the endpoint returns a REST problem', async () => {
      vi.spyOn(cmkFetch, 'fetchRestAPI').mockResolvedValue(
        makeFetchResponse(400, { title: 'Bad request', detail: 'Site does not exist' })
      )

      const action = POST_SAVE_ACTIONS.find((a) => a.key === 'enableCollector')!
      const result = await action.execute({ siteId: 'ghost', configName: 'test-config' })

      expect(result.ok).toBe(false)
      if (!result.ok) {
        expect(result.error.title).toBe('Bad request')
        expect(result.error.detail).toBe('Site does not exist')
      }
    })

    test('returns a generic error for unexpected failures', async () => {
      vi.spyOn(cmkFetch, 'fetchRestAPI').mockRejectedValue(new Error('Network down'))

      const action = POST_SAVE_ACTIONS.find((a) => a.key === 'enableCollector')!
      const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

      expect(result.ok).toBe(false)
      if (!result.ok) {
        expect(result.error.title).toBe('Could not enable the OpenTelemetry Collector')
        expect(result.error.detail).toBe('Network down')
      }
    })
  })

  describe('enableMetricBackend.execute', () => {
    test('PATCHes the metric backend update endpoint with the selected site', async () => {
      const spy = vi.spyOn(cmkFetch, 'fetchRestAPI').mockResolvedValue(makeFetchResponse(204))

      const action = POST_SAVE_ACTIONS.find((a) => a.key === 'enableMetricBackend')!
      const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

      expect(result.ok).toBe(true)
      expect(spy).toHaveBeenCalledWith(
        'api/internal/domain-types/metric_backend/actions/update/invoke',
        'PATCH',
        { site_id: 'prod', config: { type: 'enabled' } }
      )
    })

    test('returns a structured error when the endpoint returns a REST problem', async () => {
      vi.spyOn(cmkFetch, 'fetchRestAPI').mockResolvedValue(
        makeFetchResponse(400, { title: 'Bad request', detail: 'Site does not exist' })
      )

      const action = POST_SAVE_ACTIONS.find((a) => a.key === 'enableMetricBackend')!
      const result = await action.execute({ siteId: 'ghost', configName: 'test-config' })

      expect(result.ok).toBe(false)
      if (!result.ok) {
        expect(result.error.title).toBe('Bad request')
        expect(result.error.detail).toBe('Site does not exist')
      }
    })

    test('returns a generic error for unexpected failures', async () => {
      vi.spyOn(cmkFetch, 'fetchRestAPI').mockRejectedValue(new Error('Network down'))

      const action = POST_SAVE_ACTIONS.find((a) => a.key === 'enableMetricBackend')!
      const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

      expect(result.ok).toBe(false)
      if (!result.ok) {
        expect(result.error.title).toBe('Could not enable the metric backend')
        expect(result.error.detail).toBe('Network down')
      }
    })
  })
})

describe('createOTelReceiverConfigAction', () => {
  const OTEL_URL = 'api/internal/domain-types/otel_collector_config_receivers/collections/all'

  afterEach(() => {
    vi.restoreAllMocks()
  })

  test('labels the checklist item and uses a stable key', () => {
    const action = createOTelReceiverConfigAction({
      id: 'cfg1',
      siteId: 'prod',
      grpc: null,
      http: null,
      passwords: []
    })
    expect(action.key).toBe('createOTelReceiverConfig')
    expect(action.label()).toBe('Collector configuration')
  })

  test('omits both receiver protocols when neither is configured', async () => {
    const spy = vi.spyOn(cmkFetch, 'fetchRestAPI').mockResolvedValue(makeFetchResponse(200, {}))

    const action = createOTelReceiverConfigAction({
      id: 'cfg1',
      siteId: 'prod',
      grpc: null,
      http: null,
      passwords: []
    })
    const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

    expect(result.ok).toBe(true)
    expect(spy).toHaveBeenCalledWith(OTEL_URL, 'POST', {
      id: 'cfg1',
      title: 'cfg1',
      disabled: false,
      site: ['prod']
    })
  })

  test('sends the cloud body shape when extended options are absent', async () => {
    const spy = vi.spyOn(cmkFetch, 'fetchRestAPI').mockResolvedValue(makeFetchResponse(200, {}))

    const action = createOTelReceiverConfigAction({
      id: 'cloud_cfg',
      siteId: 'prod',
      grpc: {
        auth: { method: 'basicauth', username: 'alice', passwordId: 'pw_id_a' }
      },
      http: null,
      passwords: []
    })
    await action.execute({ siteId: 'prod', configName: 'test-config' })

    expect(spy).toHaveBeenCalledWith(OTEL_URL, 'POST', {
      id: 'cloud_cfg',
      title: 'cloud_cfg',
      disabled: false,
      site: ['prod'],
      receiver_protocol_grpc: {
        endpoint: {
          auth: {
            type: 'basicauth',
            userlist: [{ username: 'alice', password: { type: 'store', value: 'pw_id_a' } }]
          }
        }
      }
    })
  })

  test('sends the ultimate body shape with custom socket address, encryption and event console', async () => {
    const spy = vi.spyOn(cmkFetch, 'fetchRestAPI').mockResolvedValue(makeFetchResponse(200, {}))

    const action = createOTelReceiverConfigAction({
      id: 'ult_cfg',
      siteId: 'prod',
      grpc: {
        auth: { method: 'none' },
        extended: {
          socketAddress: { type: 'custom', address: '0.0.0.0', port: 4317 },
          encryption: false,
          eventConsole: null
        }
      },
      http: {
        auth: { method: 'basicauth', username: 'bob', passwordId: 'pw_id_b' },
        extended: {
          socketAddress: { type: 'custom', address: '0.0.0.0', port: 4318 },
          encryption: true,
          eventConsole: { resourceAttribute: 'host.name' }
        }
      },
      passwords: []
    })
    await action.execute({ siteId: 'prod', configName: 'test-config' })

    expect(spy).toHaveBeenCalledWith(OTEL_URL, 'POST', {
      id: 'ult_cfg',
      title: 'ult_cfg',
      disabled: false,
      site: ['prod'],
      receiver_protocol_grpc: {
        endpoint: {
          auth: { type: 'none' },
          socket_address: { type: 'custom', address: '0.0.0.0', port: 4317 },
          encryption: false,
          event_console: null
        }
      },
      receiver_protocol_http: {
        endpoint: {
          auth: {
            type: 'basicauth',
            userlist: [{ username: 'bob', password: { type: 'store', value: 'pw_id_b' } }]
          },
          socket_address: { type: 'custom', address: '0.0.0.0', port: 4318 },
          encryption: true,
          event_console: { host_name_resource_attribute_key: 'host.name' }
        }
      }
    })
  })

  test('sends the default-IPv4 socket address as a marker without address or port', async () => {
    const spy = vi.spyOn(cmkFetch, 'fetchRestAPI').mockResolvedValue(makeFetchResponse(200, {}))

    const action = createOTelReceiverConfigAction({
      id: 'ult_cfg',
      siteId: 'prod',
      grpc: {
        auth: { method: 'none' },
        extended: {
          socketAddress: { type: 'default_ipv4' },
          encryption: false,
          eventConsole: null
        }
      },
      http: null,
      passwords: []
    })
    await action.execute({ siteId: 'prod', configName: 'test-config' })

    expect(spy).toHaveBeenCalledWith(OTEL_URL, 'POST', {
      id: 'ult_cfg',
      title: 'ult_cfg',
      disabled: false,
      site: ['prod'],
      receiver_protocol_grpc: {
        endpoint: {
          auth: { type: 'none' },
          socket_address: { type: 'default_ipv4' },
          encryption: false,
          event_console: null
        }
      }
    })
  })

  test('sends the default-IPv6 socket address as a marker without address or port', async () => {
    const spy = vi.spyOn(cmkFetch, 'fetchRestAPI').mockResolvedValue(makeFetchResponse(200, {}))

    const action = createOTelReceiverConfigAction({
      id: 'ult_cfg',
      siteId: 'prod',
      grpc: null,
      http: {
        auth: { method: 'none' },
        extended: {
          socketAddress: { type: 'default_ipv6' },
          encryption: true,
          eventConsole: null
        }
      },
      passwords: []
    })
    await action.execute({ siteId: 'prod', configName: 'test-config' })

    expect(spy).toHaveBeenCalledWith(OTEL_URL, 'POST', {
      id: 'ult_cfg',
      title: 'ult_cfg',
      disabled: false,
      site: ['prod'],
      receiver_protocol_http: {
        endpoint: {
          auth: { type: 'none' },
          socket_address: { type: 'default_ipv6' },
          encryption: true,
          event_console: null
        }
      }
    })
  })

  test('returns a structured error when the endpoint returns a REST problem', async () => {
    vi.spyOn(cmkFetch, 'fetchRestAPI').mockResolvedValue(
      makeFetchResponse(409, { title: 'Object already exists', detail: 'ID cfg1 in use' })
    )

    const action = createOTelReceiverConfigAction({
      id: 'cfg1',
      siteId: 'prod',
      grpc: null,
      http: null,
      passwords: []
    })
    const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.error.title).toBe('Object already exists')
      expect(result.error.detail).toBe('ID cfg1 in use')
    }
  })

  test('returns a generic error for unexpected failures', async () => {
    vi.spyOn(cmkFetch, 'fetchRestAPI').mockRejectedValue(new Error('Network down'))

    const action = createOTelReceiverConfigAction({
      id: 'cfg1',
      siteId: 'prod',
      grpc: null,
      http: null,
      passwords: []
    })
    const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.error.title).toBe('Could not create the OpenTelemetry Collector configuration')
      expect(result.error.detail).toBe('Network down')
    }
  })

  describe('password store handling', () => {
    test('persists each pending password before the receiver POST', async () => {
      const fetchSpy = vi
        .spyOn(cmkFetch, 'fetchRestAPI')
        .mockResolvedValue(makeFetchResponse(200, {}))
      const createSpy = vi.spyOn(configEntityAPI, 'createEntity').mockResolvedValue({
        type: 'success',
        entity: { ident: 'pw_id_a', description: 'My password', hide_edit: false }
      })

      const password = makePasswordConfig('pw_id_a', 'My password')
      const action = createOTelReceiverConfigAction({
        id: 'cfg1',
        siteId: 'prod',
        grpc: {
          auth: { method: 'basicauth', username: 'alice', passwordId: 'pw_id_a' }
        },
        http: null,
        passwords: [password]
      })
      const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

      expect(result.ok).toBe(true)
      expect(createSpy).toHaveBeenCalledWith(
        'passwordstore_password',
        'passwordstore_password',
        password
      )
      // Password creation precedes the receiver POST.
      const createOrder = (createSpy as Mock).mock.invocationCallOrder[0]!
      const fetchOrder = (fetchSpy as Mock).mock.invocationCallOrder[0]!
      expect(createOrder).toBeLessThan(fetchOrder)
    })

    test('skips the receiver POST when a password fails and surfaces a password-specific error', async () => {
      const fetchSpy = vi
        .spyOn(cmkFetch, 'fetchRestAPI')
        .mockResolvedValue(makeFetchResponse(200, {}))
      vi.spyOn(configEntityAPI, 'createEntity').mockResolvedValue({
        type: 'error',
        validationMessages: [
          {
            location: ['password_props', 'password'],
            message: 'Too short',
            replacement_value: ''
          }
        ]
      })

      const action = createOTelReceiverConfigAction({
        id: 'cfg1',
        siteId: 'prod',
        grpc: {
          auth: { method: 'basicauth', username: 'alice', passwordId: 'pw_bad' }
        },
        http: null,
        passwords: [makePasswordConfig('pw_bad', 'My password')]
      })
      const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

      expect(result.ok).toBe(false)
      if (!result.ok) {
        expect(result.error.title).toBe('Could not save password "My password"')
        expect(result.error.detail).toBe('Too short')
      }
      expect(fetchSpy).not.toHaveBeenCalled()
    })

    test('runs the receiver POST normally when there are no pending passwords', async () => {
      const fetchSpy = vi
        .spyOn(cmkFetch, 'fetchRestAPI')
        .mockResolvedValue(makeFetchResponse(200, {}))
      const createSpy = vi.spyOn(configEntityAPI, 'createEntity')

      const action = createOTelReceiverConfigAction({
        id: 'cfg1',
        siteId: 'prod',
        grpc: null,
        http: null,
        passwords: []
      })
      const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

      expect(result.ok).toBe(true)
      expect(createSpy).not.toHaveBeenCalled()
      expect(fetchSpy).toHaveBeenCalledTimes(1)
    })
  })
})

describe('createPrometheusScrapeConfigAction', () => {
  const PROM_URL = 'api/internal/domain-types/otel_collector_config_prom_scrape/collections/all'

  afterEach(() => {
    vi.restoreAllMocks()
  })

  test('labels the checklist item and uses a stable key', () => {
    const action = createPrometheusScrapeConfigAction({
      id: 'p1',
      siteId: 'prod',
      jobName: 'job',
      metricsPath: '/metrics',
      address: '10.0.0.1',
      port: 9090,
      encryption: false
    })
    expect(action.key).toBe('createPrometheusScrapeConfig')
    expect(action.label()).toBe('Prometheus scraper configuration')
  })

  test('POSTs the prom-scrape body with a default scrape_interval of 60s', async () => {
    const spy = vi.spyOn(cmkFetch, 'fetchRestAPI').mockResolvedValue(makeFetchResponse(200, {}))

    const action = createPrometheusScrapeConfigAction({
      id: 'p1',
      siteId: 'prod',
      jobName: 'node',
      metricsPath: '/metrics',
      address: '10.0.0.1',
      port: 9090,
      encryption: true
    })
    await action.execute({ siteId: 'prod', configName: 'test-config' })

    expect(spy).toHaveBeenCalledWith(PROM_URL, 'POST', {
      id: 'p1',
      title: 'p1',
      disabled: false,
      site: ['prod'],
      prometheus_scrape_configs: [
        {
          job_name: 'node',
          scrape_interval: 60,
          metrics_path: '/metrics',
          targets: [{ address: '10.0.0.1', port: 9090 }],
          encryption: true
        }
      ]
    })
  })

  test('returns a structured error when the endpoint returns a REST problem', async () => {
    vi.spyOn(cmkFetch, 'fetchRestAPI').mockResolvedValue(
      makeFetchResponse(400, { title: 'Site conflict', detail: 'already configured' })
    )

    const action = createPrometheusScrapeConfigAction({
      id: 'p1',
      siteId: 'prod',
      jobName: 'node',
      metricsPath: '/metrics',
      address: '10.0.0.1',
      port: 9090,
      encryption: false
    })
    const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.error.title).toBe('Site conflict')
      expect(result.error.detail).toBe('already configured')
    }
  })

  test('returns a generic error for unexpected failures', async () => {
    vi.spyOn(cmkFetch, 'fetchRestAPI').mockRejectedValue(new Error('Network down'))

    const action = createPrometheusScrapeConfigAction({
      id: 'p1',
      siteId: 'prod',
      jobName: 'node',
      metricsPath: '/metrics',
      address: '10.0.0.1',
      port: 9090,
      encryption: false
    })
    const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.error.title).toBe('Could not create the Prometheus scraper configuration')
      expect(result.error.detail).toBe('Network down')
    }
  })
})
