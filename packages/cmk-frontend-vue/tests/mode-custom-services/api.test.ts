/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Loading a custom service for editing, with the show endpoint stubbed at the network boundary
// (MSW). The ETag it returns is what the update's optimistic locking depends on.
import { CmkApiError, CmkSimpleError } from 'cmk-ui-library/lib/error'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'
import { describe, expect, test } from 'vitest'

import { loadCustomServiceDefinition } from '@/mode-custom-services/api'

const API_BASE = `${location.protocol}//${location.host}/api/internal`
const OBJECT_URL = `${API_BASE}/objects/custom_service/http_duration_on_web01`

const STORED_EXTENSIONS = {
  host_assignment: { mode: 'explicit_host', host_name: 'web01' },
  configuration: {
    metric_name: 'otel.http.duration',
    service_name_template: 'HTTP duration',
    consolidation: { type: 'sum', function: 'sum_rate', lookback_seconds: 300 }
  }
}

function serviceObject() {
  return {
    domainType: 'custom_service',
    id: 'http_duration_on_web01',
    title: 'HTTP duration',
    extensions: STORED_EXTENSIONS
  }
}

const server = useMswServer(
  http.get(OBJECT_URL, () => HttpResponse.json(serviceObject(), { headers: { ETag: 'etag-1' } }))
)

describe('loadCustomServiceDefinition', () => {
  test('returns the stored service and the etag from the response header', async () => {
    const result = await loadCustomServiceDefinition('http_duration_on_web01')
    expect(result).toEqual({ ok: true, extensions: STORED_EXTENSIONS, etag: 'etag-1' })
  })

  test('surfaces the backend error message when the service cannot be read', async () => {
    server.use(
      http.get(OBJECT_URL, () =>
        HttpResponse.json(
          {
            status: 404,
            title: 'Custom service not readable',
            detail: 'Its generated rule no longer exists.'
          },
          { status: 404 }
        )
      )
    )
    const result = await loadCustomServiceDefinition('http_duration_on_web01')
    expect(result.ok).toBe(false)
    expect(!result.ok && result.error).toContain('rule no longer exists')
  })

  test('refuses a response without an etag instead of disabling the locking', async () => {
    server.use(http.get(OBJECT_URL, () => HttpResponse.json(serviceObject())))
    await expect(loadCustomServiceDefinition('http_duration_on_web01')).rejects.toThrow(
      CmkSimpleError
    )
  })

  test('lets a server fault through so it keeps its crash report', async () => {
    server.use(
      http.get(OBJECT_URL, () =>
        HttpResponse.json(
          { status: 500, title: 'Internal Server Error', detail: 'boom' },
          { status: 500 }
        )
      )
    )
    await expect(loadCustomServiceDefinition('http_duration_on_web01')).rejects.toThrow(CmkApiError)
  })
})
