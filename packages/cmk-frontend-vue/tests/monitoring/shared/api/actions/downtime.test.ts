/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  ScheduleDowntimeApi,
  type ScheduleDowntimeOptions
} from '@/monitoring/shared/api/actions/downtime'

const CONTENT_TYPE = { params: { header: { 'Content-Type': 'application/json' } } }

const OPTIONS: ScheduleDowntimeOptions = {
  comment: 'planned maintenance',
  startTime: '2026-07-01T10:00:00.000Z',
  endTime: '2026-07-01T14:00:00.000Z',
  durationMinutes: 0,
  recur: 'fixed'
}

describe('ScheduleDowntimeApi.scheduleDowntime', () => {
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

  it('schedules a downtime for the hosts via a host_by_query request', async () => {
    mockNoContent()

    await new ScheduleDowntimeApi().scheduleDowntime(['db-1', 'web-1'], OPTIONS)

    expect(postSpy).toHaveBeenCalledTimes(1)
    expect(postSpy).toHaveBeenCalledWith('/domain-types/downtime/collections/host', {
      ...CONTENT_TYPE,
      body: {
        downtime_type: 'host_by_query',
        query: {
          op: 'or',
          expr: [
            { op: '=', left: 'name', right: 'db-1' },
            { op: '=', left: 'name', right: 'web-1' }
          ]
        },
        start_time: '2026-07-01T10:00:00.000Z',
        end_time: '2026-07-01T14:00:00.000Z',
        recur: 'fixed',
        duration: 0,
        comment: 'planned maintenance'
      }
    })
  })

  it('sends a positive duration for a flexible downtime', async () => {
    mockNoContent()

    await new ScheduleDowntimeApi().scheduleDowntime(['db-1'], { ...OPTIONS, durationMinutes: 240 })

    const body = postSpy.mock.calls[0][1].body
    expect(body.duration).toBe(240)
  })

  it('throws when the response is not ok', async () => {
    postSpy.mockResolvedValueOnce({
      data: undefined,
      error: {},
      response: new Response('', { status: 403, statusText: 'Forbidden' })
    } as never)

    await expect(new ScheduleDowntimeApi().scheduleDowntime(['db-1'], OPTIONS)).rejects.toThrow()
  })
})

describe('ScheduleDowntimeApi.resolveChildHosts', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let postSpy: any

  beforeEach(() => {
    postSpy = vi.spyOn(client, 'POST')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function mockHosts(names: string[]): void {
    postSpy.mockResolvedValueOnce({
      data: { value: names.map((name) => ({ id: name })) },
      error: undefined,
      response: new Response(null, { status: 200 })
    } as never)
  }

  it('queries hosts by parents and recurses until no new children appear', async () => {
    mockHosts(['child-1']) // children of parent-1
    mockHosts(['grandchild-1']) // children of child-1
    mockHosts([]) // children of grandchild-1

    const children = await new ScheduleDowntimeApi().resolveChildHosts(['parent-1'])

    expect(children).toEqual(['child-1', 'grandchild-1'])
    expect(postSpy).toHaveBeenCalledTimes(3)
    expect(postSpy).toHaveBeenNthCalledWith(1, '/domain-types/host/collections/all', {
      ...CONTENT_TYPE,
      body: {
        columns: ['name'],
        query: { op: 'or', expr: [{ op: '>=', left: 'parents', right: 'parent-1' }] }
      }
    })
  })

  it('does not revisit hosts that were already seen', async () => {
    mockHosts(['parent-1']) // cycle back to the seed host

    const children = await new ScheduleDowntimeApi().resolveChildHosts(['parent-1'])

    expect(children).toEqual([])
    expect(postSpy).toHaveBeenCalledTimes(1)
  })
})
