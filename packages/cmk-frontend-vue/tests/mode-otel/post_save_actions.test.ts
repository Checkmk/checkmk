/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as cmkFetch from '@/lib/cmkFetch'

import { POST_SAVE_ACTIONS } from '@/mode-otel/otel-configuration-steps/post_save_actions.ts'

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
