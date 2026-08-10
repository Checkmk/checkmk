/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { RescheduleApi } from '@/monitoring/shared/api/actions/reschedule'

const CONTENT_TYPE = { params: { header: { 'Content-Type': 'application/json' } } }

const HOSTS = [
  { site_id: 'local', name: 'db-1' },
  { site_id: 'remote', name: 'web-1' }
]

describe('RescheduleApi.rescheduleHosts', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let postSpy: any

  beforeEach(() => {
    postSpy = vi.spyOn(client, 'POST')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function mockRescheduled(rescheduled: number): void {
    postSpy.mockResolvedValueOnce({
      data: { rescheduled },
      error: undefined,
      response: new Response(null, { status: 200 })
    } as never)
  }

  it('posts the hosts and spread minutes and returns the rescheduled count', async () => {
    mockRescheduled(2)

    const count = await new RescheduleApi().rescheduleHosts(HOSTS, 5)

    expect(count).toBe(2)
    expect(postSpy).toHaveBeenCalledTimes(1)
    expect(postSpy).toHaveBeenCalledWith('/monitor/hosts/actions/reschedule', {
      ...CONTENT_TYPE,
      body: { hosts: HOSTS, spread_minutes: 5 }
    })
  })

  it('throws when the response is not ok', async () => {
    postSpy.mockResolvedValueOnce({
      data: undefined,
      error: {},
      response: new Response('', { status: 403, statusText: 'Forbidden' })
    } as never)

    await expect(new RescheduleApi().rescheduleHosts(HOSTS, 0)).rejects.toThrow()
  })
})

describe('RescheduleApi.rescheduleServices', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let postSpy: any

  beforeEach(() => {
    postSpy = vi.spyOn(client, 'POST')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function mockRescheduled(rescheduled: number): void {
    postSpy.mockResolvedValueOnce({
      data: { rescheduled },
      error: undefined,
      response: new Response(null, { status: 200 })
    } as never)
  }

  it('expands the names to services of the page host', async () => {
    mockRescheduled(2)

    const count = await new RescheduleApi().rescheduleServices(
      { site_id: 'local', name: 'web-1' },
      ['CPU load', 'Memory'],
      5
    )

    expect(count).toBe(2)
    expect(postSpy).toHaveBeenCalledTimes(1)
    expect(postSpy).toHaveBeenCalledWith('/monitor/services/actions/reschedule', {
      ...CONTENT_TYPE,
      body: {
        services: [
          { site_id: 'local', host_name: 'web-1', name: 'CPU load' },
          { site_id: 'local', host_name: 'web-1', name: 'Memory' }
        ],
        spread_minutes: 5
      }
    })
  })

  it('throws when the response is not ok', async () => {
    postSpy.mockResolvedValueOnce({
      data: undefined,
      error: {},
      response: new Response('', { status: 403, statusText: 'Forbidden' })
    } as never)

    await expect(
      new RescheduleApi().rescheduleServices({ site_id: 'local', name: 'web-1' }, ['CPU load'], 0)
    ).rejects.toThrow()
  })
})
