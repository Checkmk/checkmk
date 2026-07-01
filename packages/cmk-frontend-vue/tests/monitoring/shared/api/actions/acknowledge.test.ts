/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import client from '@/lib/rest-api-client/client'

import { AcknowledgeApi } from '@/monitoring/shared/api/actions/acknowledge'

const CONTENT_TYPE = { params: { header: { 'Content-Type': 'application/json' } } }

const BASE_OPTIONS = {
  comment: 'expected downtime',
  sticky: true,
  persistent: false,
  notify: true
}

describe('AcknowledgeApi.acknowledgeHosts', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let postSpy: any

  beforeEach(() => {
    postSpy = vi.spyOn(client, 'POST')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function mockNoContent(): void {
    postSpy.mockResolvedValueOnce({
      data: undefined,
      error: undefined,
      response: new Response(null, { status: 204 })
    } as never)
  }

  it('acknowledges multiple hosts in a single host_by_query request', async () => {
    mockNoContent()

    await new AcknowledgeApi().acknowledgeHosts(['db-1', 'web-1'], BASE_OPTIONS)

    expect(postSpy).toHaveBeenCalledTimes(1)
    expect(postSpy).toHaveBeenCalledWith('/domain-types/acknowledge/collections/host', {
      ...CONTENT_TYPE,
      body: {
        acknowledge_type: 'host_by_query',
        query: {
          op: 'or',
          expr: [
            { op: '=', left: 'name', right: 'db-1' },
            { op: '=', left: 'name', right: 'web-1' }
          ]
        },
        comment: 'expected downtime',
        sticky: true,
        persistent: false,
        notify: true
      }
    })
  })

  it('builds a single-condition query for one host', async () => {
    mockNoContent()

    await new AcknowledgeApi().acknowledgeHosts(['db-1'], BASE_OPTIONS)

    expect(postSpy).toHaveBeenCalledWith('/domain-types/acknowledge/collections/host', {
      ...CONTENT_TYPE,
      body: {
        acknowledge_type: 'host_by_query',
        query: { op: 'or', expr: [{ op: '=', left: 'name', right: 'db-1' }] },
        comment: 'expected downtime',
        sticky: true,
        persistent: false,
        notify: true
      }
    })
  })

  it('includes expire_on when an expiry is provided', async () => {
    mockNoContent()

    await new AcknowledgeApi().acknowledgeHosts(['db-1'], {
      ...BASE_OPTIONS,
      expireOn: '2026-05-20T07:30:00.000Z'
    })

    const body = postSpy.mock.calls[0][1].body
    expect(body.expire_on).toBe('2026-05-20T07:30:00.000Z')
  })

  it('omits expire_on when no expiry is provided', async () => {
    mockNoContent()

    await new AcknowledgeApi().acknowledgeHosts(['db-1'], BASE_OPTIONS)

    const body = postSpy.mock.calls[0][1].body
    expect(body).not.toHaveProperty('expire_on')
  })

  it('throws when the response is not ok', async () => {
    postSpy.mockResolvedValueOnce({
      data: undefined,
      error: {},
      response: new Response('', { status: 403, statusText: 'Forbidden' })
    } as never)

    await expect(new AcknowledgeApi().acknowledgeHosts(['db-1'], BASE_OPTIONS)).rejects.toThrow()
  })
})
