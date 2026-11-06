/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AcknowledgeApi } from '@/monitoring/shared/api/actions/acknowledge'

const CONTENT_TYPE = { params: { header: { 'Content-Type': 'application/json' } } }

const BASE_OPTIONS = {
  comment: 'expected downtime',
  sticky: true,
  persistent: false,
  notify: true
}

// A host name two sites monitor: each row must keep its own site.
const HOSTS = [
  { site_id: 'local', name: 'web-1' },
  { site_id: 'remote', name: 'web-1' }
]

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

beforeEach(() => {
  postSpy = vi.spyOn(client, 'POST').mockResolvedValue({
    data: { acknowledged: 2 },
    error: undefined,
    response: new Response(null, { status: 200 })
  } as never)
})

describe('AcknowledgeApi.acknowledgeHosts', () => {
  it('posts each host with its site and returns the count', async () => {
    expect(await new AcknowledgeApi().acknowledgeHosts(HOSTS, BASE_OPTIONS)).toBe(2)

    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts/actions/acknowledge', {
      ...CONTENT_TYPE,
      body: { hosts: HOSTS, ...BASE_OPTIONS }
    })
  })

  it('includes expire_on when an expiry is provided', async () => {
    await new AcknowledgeApi().acknowledgeHosts(HOSTS, {
      ...BASE_OPTIONS,
      expireOn: '2026-05-20T07:30:00.000Z'
    })

    expect(postSpy.mock.calls[0][1].body.expire_on).toBe('2026-05-20T07:30:00.000Z')
  })

  it('omits expire_on when no expiry is provided', async () => {
    await new AcknowledgeApi().acknowledgeHosts(HOSTS, BASE_OPTIONS)

    expect(postSpy.mock.calls[0][1].body).not.toHaveProperty('expire_on')
  })

  it('throws when the response is not ok', async () => {
    postSpy.mockResolvedValueOnce({
      data: undefined,
      error: {},
      response: new Response('', { status: 403, statusText: 'Forbidden' })
    } as never)

    await expect(new AcknowledgeApi().acknowledgeHosts(HOSTS, BASE_OPTIONS)).rejects.toThrow()
  })
})

describe('AcknowledgeApi.acknowledgeServices', () => {
  it('posts each service with the site of its host and returns the count', async () => {
    expect(
      await new AcknowledgeApi().acknowledgeServices(
        HOSTS.map((host) => ({ host, description: 'CPU load' })),
        BASE_OPTIONS
      )
    ).toBe(2)

    expect(postSpy).toHaveBeenCalledWith('/monitor/services/actions/acknowledge', {
      ...CONTENT_TYPE,
      body: {
        services: [
          { site_id: 'local', host_name: 'web-1', name: 'CPU load' },
          { site_id: 'remote', host_name: 'web-1', name: 'CPU load' }
        ],
        ...BASE_OPTIONS
      }
    })
  })
})
