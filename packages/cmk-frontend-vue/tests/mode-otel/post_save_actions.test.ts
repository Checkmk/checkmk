/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import type { Mock } from 'vitest'

import { configEntityAPI } from '@/form'

import type { PasswordConfig } from '@/mode-otel/otel-configuration-steps/password_store_password.types.ts'
import {
  POST_SAVE_ACTIONS,
  buildPrometheusFinalizeActions,
  createOTelBundleAction,
  createOTelReceiverConfigAction,
  createPrometheusScrapeConfigAction
} from '@/mode-otel/otel-configuration-steps/post_save_actions.ts'

function makePasswordConfig(id: string, title = id): PasswordConfig {
  return {
    general_props: { id, title, comment: '', docu_url: '' },
    password_props: {
      password: ['secret', false],
      owned_by: ['admins', null],
      share_with: []
    }
  }
}

const IF_MATCH = { 'If-Match': '*' }
const JSON_HEADER = { 'Content-Type': 'application/json' }

type ClientResult = { data?: unknown; error?: unknown; response: Response }

/** A 2xx client result carrying `body` as the parsed payload. */
function makeOk(body: unknown = null, status = 200): ClientResult {
  return { data: body, error: undefined, response: new Response(null, { status }) }
}

/** A 204 client result, as returned by the update and delete endpoints. */
function makeNoContent(): ClientResult {
  return { data: undefined, error: undefined, response: new Response(null, { status: 204 }) }
}

/**
 * A non-2xx client result. `unwrap` turns a `{ title, detail }` error body into
 * a CmkApiError whose message is `"${title}: ${detail}"`, which is what
 * errorFromUnknown parses the detail back out of.
 */
function makeError(status: number, body: unknown = {}): ClientResult {
  return { data: undefined, error: body, response: new Response(null, { status }) }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function spyOnClient(method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'): any {
  return vi.spyOn(client, method)
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

  test('enableDataBackend action is present as the second registry entry', () => {
    expect(POST_SAVE_ACTIONS[1]!.key).toBe('enableDataBackend')
    expect(POST_SAVE_ACTIONS[1]!.label()).toBe('Data backend connection')
  })

  describe('enableCollector.execute', () => {
    test('PUTs to the collector update endpoint with the selected site', async () => {
      spyOnClient('GET').mockResolvedValueOnce(makeOk({ activation: { mode: 'disabled' } }))
      const putSpy = spyOnClient('PUT').mockResolvedValueOnce(makeNoContent())

      const action = POST_SAVE_ACTIONS.find((a) => a.key === 'enableCollector')!
      const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

      expect(result.ok).toBe(true)
      expect(putSpy).toHaveBeenCalledWith('/domain-types/otel_collector/actions/update/invoke', {
        params: { header: JSON_HEADER },
        body: { site_id: 'prod', activation: { mode: 'enabled' } }
      })
    })

    test('returns no rollback when the collector was already enabled', async () => {
      spyOnClient('GET').mockResolvedValueOnce(makeOk({ activation: { mode: 'enabled' } }))
      spyOnClient('PUT').mockResolvedValueOnce(makeNoContent())

      const action = POST_SAVE_ACTIONS.find((a) => a.key === 'enableCollector')!
      const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

      expect(result.ok).toBe(true)
      if (result.ok) {
        expect(result.rollback).toBeUndefined()
      }
    })

    test('returns a rollback that disables the collector when it was previously disabled', async () => {
      spyOnClient('GET').mockResolvedValueOnce(makeOk({ activation: { mode: 'disabled' } }))
      const putSpy = spyOnClient('PUT').mockResolvedValue(makeNoContent())

      const action = POST_SAVE_ACTIONS.find((a) => a.key === 'enableCollector')!
      const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

      expect(result.ok).toBe(true)
      if (result.ok) {
        expect(result.rollback).toBeDefined()
        await result.rollback!()
        expect(putSpy).toHaveBeenLastCalledWith(
          '/domain-types/otel_collector/actions/update/invoke',
          {
            params: { header: JSON_HEADER },
            body: { site_id: 'prod', activation: { mode: 'disabled' } }
          }
        )
      }
    })

    test('returns a structured error when the endpoint returns a REST problem', async () => {
      spyOnClient('GET').mockResolvedValue(
        makeError(400, { title: 'Bad request', detail: 'Site does not exist' })
      )

      const action = POST_SAVE_ACTIONS.find((a) => a.key === 'enableCollector')!
      const result = await action.execute({ siteId: 'ghost', configName: 'test-config' })

      expect(result.ok).toBe(false)
      if (!result.ok) {
        // The action-specific fallback is the headline; only the REST detail is kept.
        expect(result.error.title).toBe('Could not enable the OpenTelemetry Collector')
        expect(result.error.detail).toBe('Site does not exist')
      }
    })

    test('returns a generic error for unexpected failures', async () => {
      spyOnClient('GET').mockRejectedValue(new Error('Network down'))

      const action = POST_SAVE_ACTIONS.find((a) => a.key === 'enableCollector')!
      const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

      expect(result.ok).toBe(false)
      if (!result.ok) {
        // A non-CmkApiError (network throw) surfaces no noisy detail.
        expect(result.error.title).toBe('Could not enable the OpenTelemetry Collector')
        expect(result.error.detail).toBe('')
      }
    })
  })

  describe('enableDataBackend.execute', () => {
    test('PATCHes the data backend update endpoint with the selected site', async () => {
      spyOnClient('GET').mockResolvedValueOnce(makeOk({ type: 'disabled' }))
      const patchSpy = spyOnClient('PATCH').mockResolvedValueOnce(makeNoContent())

      const action = POST_SAVE_ACTIONS.find((a) => a.key === 'enableDataBackend')!
      const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

      expect(result.ok).toBe(true)
      expect(patchSpy).toHaveBeenCalledWith('/domain-types/data_backend/actions/update/invoke', {
        params: { header: JSON_HEADER },
        body: { site_id: 'prod', config: { type: 'enabled' } }
      })
    })

    test('returns no rollback when the data backend was already enabled', async () => {
      spyOnClient('GET').mockResolvedValueOnce(makeOk({ type: 'enabled' }))
      spyOnClient('PATCH').mockResolvedValueOnce(makeNoContent())

      const action = POST_SAVE_ACTIONS.find((a) => a.key === 'enableDataBackend')!
      const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

      expect(result.ok).toBe(true)
      if (result.ok) {
        expect(result.rollback).toBeUndefined()
      }
    })

    test('returns a rollback that disables the data backend when it was previously disabled', async () => {
      spyOnClient('GET').mockResolvedValueOnce(makeOk({ type: 'disabled' }))
      const patchSpy = spyOnClient('PATCH').mockResolvedValue(makeNoContent())

      const action = POST_SAVE_ACTIONS.find((a) => a.key === 'enableDataBackend')!
      const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

      expect(result.ok).toBe(true)
      if (result.ok) {
        expect(result.rollback).toBeDefined()
        await result.rollback!()
        expect(patchSpy).toHaveBeenLastCalledWith(
          '/domain-types/data_backend/actions/update/invoke',
          {
            params: { header: JSON_HEADER },
            body: { site_id: 'prod', config: { type: 'disabled' } }
          }
        )
      }
    })

    test('returns a structured error when the endpoint returns a REST problem', async () => {
      spyOnClient('GET').mockResolvedValue(
        makeError(400, { title: 'Bad request', detail: 'Site does not exist' })
      )

      const action = POST_SAVE_ACTIONS.find((a) => a.key === 'enableDataBackend')!
      const result = await action.execute({ siteId: 'ghost', configName: 'test-config' })

      expect(result.ok).toBe(false)
      if (!result.ok) {
        expect(result.error.title).toBe('Could not enable the data backend')
        expect(result.error.detail).toBe('Site does not exist')
      }
    })

    test('returns a generic error for unexpected failures', async () => {
      spyOnClient('GET').mockRejectedValue(new Error('Network down'))

      const action = POST_SAVE_ACTIONS.find((a) => a.key === 'enableDataBackend')!
      const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

      expect(result.ok).toBe(false)
      if (!result.ok) {
        expect(result.error.title).toBe('Could not enable the data backend')
        expect(result.error.detail).toBe('')
      }
    })
  })
})

describe('createOTelReceiverConfigAction', () => {
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
    const postSpy = spyOnClient('POST').mockResolvedValue(makeOk({}))

    const action = createOTelReceiverConfigAction({
      id: 'cfg1',
      siteId: 'prod',
      grpc: null,
      http: null,
      passwords: []
    })
    const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

    expect(result.ok).toBe(true)
    expect(postSpy).toHaveBeenCalledWith(
      '/domain-types/otel_collector_config_receivers/collections/all',
      {
        params: { header: JSON_HEADER },
        body: {
          id: 'cfg1',
          title: 'cfg1',
          disabled: false,
          site: ['prod']
        }
      }
    )
  })

  test('sends the cloud body shape when extended options are absent', async () => {
    const postSpy = spyOnClient('POST').mockResolvedValue(makeOk({}))

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

    expect(postSpy).toHaveBeenCalledWith(
      '/domain-types/otel_collector_config_receivers/collections/all',
      {
        params: { header: JSON_HEADER },
        body: {
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
        }
      }
    )
  })

  test('sends the ultimate body shape with custom socket address, encryption and event console', async () => {
    const postSpy = spyOnClient('POST').mockResolvedValue(makeOk({}))

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

    expect(postSpy).toHaveBeenCalledWith(
      '/domain-types/otel_collector_config_receivers/collections/all',
      {
        params: { header: JSON_HEADER },
        body: {
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
        }
      }
    )
  })

  test('sends the default-IPv4 socket address as a marker without address or port', async () => {
    const postSpy = spyOnClient('POST').mockResolvedValue(makeOk({}))

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

    expect(postSpy).toHaveBeenCalledWith(
      '/domain-types/otel_collector_config_receivers/collections/all',
      {
        params: { header: JSON_HEADER },
        body: {
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
        }
      }
    )
  })

  test('sends the default-IPv6 socket address as a marker without address or port', async () => {
    const postSpy = spyOnClient('POST').mockResolvedValue(makeOk({}))

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

    expect(postSpy).toHaveBeenCalledWith(
      '/domain-types/otel_collector_config_receivers/collections/all',
      {
        params: { header: JSON_HEADER },
        body: {
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
        }
      }
    )
  })

  test('returns a structured error when the endpoint returns a REST problem', async () => {
    spyOnClient('POST').mockResolvedValue(
      makeError(409, { title: 'Object already exists', detail: 'ID cfg1 in use' })
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
      expect(result.error.title).toBe('Could not create the OpenTelemetry Collector configuration')
      expect(result.error.detail).toBe('ID cfg1 in use')
    }
  })

  test('returns a generic error for unexpected failures', async () => {
    spyOnClient('POST').mockRejectedValue(new Error('Network down'))

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
      expect(result.error.detail).toBe('')
    }
  })

  test('returns a rollback that DELETEs the receiver config on success', async () => {
    spyOnClient('POST').mockResolvedValueOnce(makeOk({}))
    const deleteSpy = spyOnClient('DELETE').mockResolvedValueOnce(makeNoContent())

    const action = createOTelReceiverConfigAction({
      id: 'cfg1',
      siteId: 'prod',
      grpc: null,
      http: null,
      passwords: []
    })
    const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.rollback).toBeDefined()
      await result.rollback!()
      // The receiver DELETE must carry If-Match — the endpoint enforces ETag locking.
      expect(deleteSpy).toHaveBeenLastCalledWith(
        '/objects/otel_collector_config_receivers/{config_id}',
        { params: { header: IF_MATCH, path: { config_id: 'cfg1' } } }
      )
    }
  })

  test('rollback deletes created passwords with an If-Match header when a later action fails', async () => {
    // Simulates the user's scenario: the receiver config (incl. passwords)
    // succeeds, then a later step (e.g. the DCD connector) fails and the
    // FinalizeConfiguration state machine invokes this action's rollback.
    spyOnClient('POST').mockResolvedValue(makeOk({}))
    const deleteSpy = spyOnClient('DELETE').mockResolvedValue(makeNoContent())
    vi.spyOn(configEntityAPI, 'createEntity').mockResolvedValue({
      type: 'success',
      entity: { ident: 'pw_id_a', description: 'My password', hide_edit: false }
    })

    const action = createOTelReceiverConfigAction({
      id: 'cfg1',
      siteId: 'prod',
      grpc: { auth: { method: 'basicauth', username: 'alice', passwordId: 'pw_id_a' } },
      http: null,
      passwords: [makePasswordConfig('pw_id_a', 'My password')]
    })
    const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.rollback).toBeDefined()
      await result.rollback!()
      // The password DELETE must carry If-Match — the endpoint enforces ETag
      // locking and silently rejects the delete otherwise.
      expect(deleteSpy).toHaveBeenCalledWith('/objects/password/{name}', {
        params: { header: IF_MATCH, path: { name: 'pw_id_a' } }
      })
    }
  })

  describe('password store handling', () => {
    test('persists each pending password before the receiver POST', async () => {
      const postSpy = spyOnClient('POST').mockResolvedValue(makeOk({}))
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
      const fetchOrder = (postSpy as Mock).mock.invocationCallOrder[0]!
      expect(createOrder).toBeLessThan(fetchOrder)
    })

    test('skips the receiver POST when a password fails and surfaces a password-specific error', async () => {
      const postSpy = spyOnClient('POST').mockResolvedValue(makeOk({}))
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
      expect(postSpy).not.toHaveBeenCalled()
    })

    test('rolls back already-created passwords and returns an error when a later password throws', async () => {
      const postSpy = spyOnClient('POST').mockResolvedValue(makeOk({}))
      const deleteSpy = spyOnClient('DELETE').mockResolvedValue(makeNoContent())
      // First password saves; the second throws (e.g. network / 5xx, which
      // `createEntity` surfaces as a throw rather than a `type: 'error'`).
      vi.spyOn(configEntityAPI, 'createEntity')
        .mockResolvedValueOnce({
          type: 'success',
          entity: { ident: 'pw_id_a', description: 'first', hide_edit: false }
        })
        .mockRejectedValueOnce(new Error('Network down'))

      const action = createOTelReceiverConfigAction({
        id: 'cfg1',
        siteId: 'prod',
        grpc: { auth: { method: 'basicauth', username: 'alice', passwordId: 'pw_id_a' } },
        http: null,
        passwords: [makePasswordConfig('pw_id_a', 'first'), makePasswordConfig('pw_id_b', 'second')]
      })
      const result = await action.execute({ siteId: 'prod', configName: 'test-config' })

      expect(result.ok).toBe(false)
      // The first password was deleted with an If-Match header (the password
      // endpoint enforces ETag locking); the receiver POST never ran.
      expect(deleteSpy).toHaveBeenCalledWith('/objects/password/{name}', {
        params: { header: IF_MATCH, path: { name: 'pw_id_a' } }
      })
      expect(postSpy).not.toHaveBeenCalledWith(
        '/domain-types/otel_collector_config_receivers/collections/all',
        { params: { header: JSON_HEADER }, body: expect.anything() }
      )
    })

    test('runs the receiver POST normally when there are no pending passwords', async () => {
      const postSpy = spyOnClient('POST').mockResolvedValue(makeOk({}))
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
      expect(postSpy).toHaveBeenCalledTimes(1)
    })
  })
})

describe('createPrometheusScrapeConfigAction', () => {
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
    const postSpy = spyOnClient('POST').mockResolvedValue(makeOk({}))

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

    expect(postSpy).toHaveBeenCalledWith(
      '/domain-types/otel_collector_config_prom_scrape/collections/all',
      {
        params: { header: JSON_HEADER },
        body: {
          id: 'p1',
          comment: null,
          docu_url: null,
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
        }
      }
    )
  })

  test('returns a rollback that DELETEs the prom-scrape config with an If-Match header', async () => {
    spyOnClient('POST').mockResolvedValueOnce(makeOk({}))
    const deleteSpy = spyOnClient('DELETE').mockResolvedValueOnce(makeNoContent())

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

    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.rollback).toBeDefined()
      await result.rollback!()
      // The prom-scrape DELETE must carry If-Match — the endpoint enforces ETag locking.
      expect(deleteSpy).toHaveBeenLastCalledWith(
        '/objects/otel_collector_config_prom_scrape/{config_id}',
        { params: { header: IF_MATCH, path: { config_id: 'p1' } } }
      )
    }
  })

  test('returns a structured error when the endpoint returns a REST problem', async () => {
    spyOnClient('POST').mockResolvedValue(
      makeError(400, { title: 'Site conflict', detail: 'already configured' })
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
      expect(result.error.title).toBe('Could not create the Prometheus scraper configuration')
      expect(result.error.detail).toBe('already configured')
    }
  })

  test('returns a generic error for unexpected failures', async () => {
    spyOnClient('POST').mockRejectedValue(new Error('Network down'))

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
      expect(result.error.detail).toBe('')
    }
  })
})

describe('createOTelBundleAction', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  test('returns a rollback that DELETEs the bundle when the response contains a bundle_id', async () => {
    spyOnClient('POST').mockResolvedValueOnce(makeOk({ extensions: { bundle_id: 'bnd-42' } }))
    const deleteSpy = spyOnClient('DELETE').mockResolvedValueOnce(makeNoContent())

    const action = createOTelBundleAction({ configName: 'my-cfg', siteId: 'prod', passwordIds: [] })
    const result = await action.execute({ siteId: 'prod', configName: 'my-cfg' })

    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.rollback).toBeDefined()
      await result.rollback!()
      expect(deleteSpy).toHaveBeenLastCalledWith(
        '/objects/otel_collector_config_bundles/{bundle_id}',
        { params: { path: { bundle_id: 'bnd-42' } } }
      )
    }
  })

  test('returns no rollback when the response carries an empty bundle_id', async () => {
    // bundle_id is non-optional in the spec, so the "missing" case is an empty
    // string rather than an absent key.
    spyOnClient('POST').mockResolvedValueOnce(makeOk({ extensions: { bundle_id: '' } }))

    const action = createOTelBundleAction({ configName: 'my-cfg', siteId: 'prod', passwordIds: [] })
    const result = await action.execute({ siteId: 'prod', configName: 'my-cfg' })

    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.rollback).toBeUndefined()
    }
  })
})

describe('createDCDConnectorAction', () => {
  const FOLDER_COLLECTION = '/domain-types/folder_config/collections/all'
  const DCD_COLLECTION = '/domain-types/dcd_telemetry_metrics/collections/all'

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function dcdAction() {
    return POST_SAVE_ACTIONS.find((a) => a.key === 'createDCDConnector')!
  }

  test('creates the telemetry folder before the connector that stores hosts in it', async () => {
    const postSpy = spyOnClient('POST').mockResolvedValue(makeOk({}))

    const result = await dcdAction().execute({ siteId: 'prod', configName: 'my-cfg' })

    expect(result.ok).toBe(true)
    expect(postSpy.mock.calls.map((call: unknown[]) => call[0])).toEqual([
      FOLDER_COLLECTION,
      DCD_COLLECTION
    ])
  })

  test('creates the telemetry folder at the root', async () => {
    const postSpy = spyOnClient('POST').mockResolvedValue(makeOk({}))

    await dcdAction().execute({ siteId: 'prod', configName: 'my-cfg' })

    expect(postSpy).toHaveBeenCalledWith(FOLDER_COLLECTION, {
      params: { header: JSON_HEADER },
      body: { title: 'Telemetry', parent: '/', name: 'telemetry' }
    })
  })

  test('sends the connector tuning the backend would otherwise default to', async () => {
    const postSpy = spyOnClient('POST').mockResolvedValue(makeOk({}))

    await dcdAction().execute({ siteId: 'prod', configName: 'my-cfg' })

    expect(postSpy).toHaveBeenCalledWith(DCD_COLLECTION, {
      params: { header: JSON_HEADER },
      body: {
        title: 'my-cfg',
        comment: '',
        documentation_url: '',
        disabled: false,
        site: 'prod',
        dcd_id: 'quick_setup_my-cfg',
        connector: {
          connector_type: 'telemetry_metrics',
          interval: 60,
          discover_on_creation: true,
          validity_period: 3600,
          maximum_number_of_hosts: 500,
          host_name_lookup_rules: [{ host_name_template: '$RESOURCE_ATTR.service.name$' }],
          creation_rules: [{ folder_path: '/telemetry', delete_hosts: true }]
        }
      }
    })
  })

  test('rolls the connector back before the folder it stores hosts in', async () => {
    spyOnClient('POST').mockResolvedValue(makeOk({}))
    const deleteSpy = spyOnClient('DELETE').mockResolvedValue(makeNoContent())

    const result = await dcdAction().execute({ siteId: 'prod', configName: 'my-cfg' })

    expect(result.ok).toBe(true)
    if (result.ok) {
      await result.rollback!()
      expect(deleteSpy.mock.calls.map((call: unknown[]) => call[0])).toEqual([
        '/objects/dcd_telemetry_metrics/{dcd_id}',
        '/objects/folder_config/{folder}'
      ])
    }
  })

  test('keeps a pre-existing telemetry folder out of the rollback', async () => {
    spyOnClient('POST')
      .mockResolvedValueOnce(makeError(400, { title: 'Conflict', detail: 'exists' }))
      .mockResolvedValueOnce(makeOk({}))
    spyOnClient('GET').mockResolvedValue(makeOk({ id: 'telemetry' }))
    const deleteSpy = spyOnClient('DELETE').mockResolvedValue(makeNoContent())

    const result = await dcdAction().execute({ siteId: 'prod', configName: 'my-cfg' })

    expect(result.ok).toBe(true)
    if (result.ok) {
      await result.rollback!()
      expect(deleteSpy.mock.calls.map((call: unknown[]) => call[0])).toEqual([
        '/objects/dcd_telemetry_metrics/{dcd_id}'
      ])
    }
  })

  test('treats an existing connector as success without a rollback for it', async () => {
    spyOnClient('POST')
      .mockResolvedValueOnce(makeOk({}))
      .mockResolvedValueOnce(makeError(409, { title: 'Conflict', detail: 'dcd exists' }))
    const deleteSpy = spyOnClient('DELETE').mockResolvedValue(makeNoContent())

    const result = await dcdAction().execute({ siteId: 'prod', configName: 'my-cfg' })

    expect(result.ok).toBe(true)
    if (result.ok) {
      await result.rollback!()
      expect(deleteSpy.mock.calls.map((call: unknown[]) => call[0])).toEqual([
        '/objects/folder_config/{folder}'
      ])
    }
  })

  test('removes the folder it just created when the connector cannot be created', async () => {
    spyOnClient('POST')
      .mockResolvedValueOnce(makeOk({}))
      .mockResolvedValueOnce(makeError(400, { title: 'Bad request', detail: 'no such site' }))
    const deleteSpy = spyOnClient('DELETE').mockResolvedValue(makeNoContent())

    const result = await dcdAction().execute({ siteId: 'ghost', configName: 'my-cfg' })

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.error.title).toBe('Could not create the telemetry metrics connector')
      expect(result.error.detail).toBe('no such site')
    }
    expect(deleteSpy.mock.calls.map((call: unknown[]) => call[0])).toEqual([
      '/objects/folder_config/{folder}'
    ])
  })

  test('reports the folder failure and never reaches the connector', async () => {
    const postSpy = spyOnClient('POST').mockResolvedValue(
      makeError(400, { title: 'Bad request', detail: 'folder rejected' })
    )
    spyOnClient('GET').mockResolvedValue(makeError(404, { title: 'Not found', detail: 'nope' }))

    const result = await dcdAction().execute({ siteId: 'prod', configName: 'my-cfg' })

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.error.title).toBe('Could not create the Telemetry hosts folder')
    }
    expect(postSpy.mock.calls.map((call: unknown[]) => call[0])).toEqual([FOLDER_COLLECTION])
  })
})

describe('buildPrometheusFinalizeActions', () => {
  test('returns the expected action order', () => {
    const actions = buildPrometheusFinalizeActions({
      id: 'cfg',
      siteId: 'mysite',
      jobName: 'my_job',
      metricsPath: '/metrics',
      address: '10.0.0.1',
      port: 9090,
      encryption: false
    })

    expect(actions.map((a) => a.key)).toEqual([
      'enableCollector',
      'enableDataBackend',
      'createPrometheusScrapeConfig',
      'createDCDConnector',
      'createOTelBundle'
    ])
  })
})
