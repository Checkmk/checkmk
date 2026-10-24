/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useMswServer } from 'cmk-ui-library/vitest.msw'
// eslint-disable-next-line no-restricted-imports -- pre-existing violation: type these handlers, never copy this line
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'

import { CommandsApi } from '@/maps/api/commands'

import { type SeenRequest, snapshot } from '../support/http'

const commands = new CommandsApi()

const server = useMswServer()

describe('api client — commands about one object', () => {
  function recordPost(path: string): SeenRequest[] {
    const seen: SeenRequest[] = []
    server.use(
      http.post(`*/api/internal${path}`, async ({ request }) => {
        seen.push(await snapshot(request))
        return new HttpResponse(null, { status: 204 })
      })
    )
    return seen
  }

  it('schedules a service downtime through the downtime collection', async () => {
    const seen = recordPost('/domain-types/downtime/collections/service')

    await commands.downtimeService('web01', 'CPU', {
      startTime: '2026-09-23T08:00:00Z',
      endTime: '2026-09-23T10:00:00Z',
      comment: 'patching',
      durationMinutes: 0,
      recur: 'fixed'
    })

    expect(JSON.parse(seen[0]!.body)).toEqual({
      downtime_type: 'service',
      host_name: 'web01',
      service_descriptions: ['CPU'],
      start_time: '2026-09-23T08:00:00Z',
      end_time: '2026-09-23T10:00:00Z',
      comment: 'patching',
      duration: 0,
      recur: 'fixed'
    })
  })

  it('comments on a host through the comment collection', async () => {
    const seen = recordPost('/domain-types/comment/collections/host')

    await commands.addCommentHost('web01', 'rebooted')

    expect(JSON.parse(seen[0]!.body)).toEqual({
      comment_type: 'host',
      host_name: 'web01',
      comment: 'rebooted',
      persistent: false
    })
  })

  it('removes a service acknowledgement through the acknowledge delete action', async () => {
    const seen = recordPost('/domain-types/acknowledge/actions/delete/invoke')

    await commands.removeAcknowledgementService('web01', 'CPU')

    expect(JSON.parse(seen[0]!.body)).toEqual({
      acknowledge_type: 'service',
      host_name: 'web01',
      service_description: 'CPU'
    })
  })

  it('reschedules a check through the Maps endpoint, at the object site', async () => {
    const seen = recordPost('/domain-types/maps_command/actions/run/invoke')

    await commands.forceCheckService('web01', 'CPU', 'remote')

    expect(JSON.parse(seen[0]!.body)).toEqual({
      action: 'force_check',
      host_name: 'web01',
      service_description: 'CPU',
      site_id: 'remote'
    })
  })
})

describe('api client — Checkmk REST API transport', () => {
  const CMK_BASE = 'http://cmk.example.com/heute'
  const API_BASE = `${CMK_BASE}/check_mk/api/1.0`

  it('schedules a repeating, flexible group downtime at the connection site', async () => {
    const seen: SeenRequest[] = []
    server.use(
      http.post(`${API_BASE}/domain-types/downtime/collections/host`, async ({ request }) => {
        seen.push(await snapshot(request))
        return new HttpResponse(null, { status: 204 })
      })
    )

    await commands.downtimeHostgroup(CMK_BASE, 'linux', {
      startTime: '2026-09-23T08:00:00Z',
      endTime: '2026-09-23T10:00:00Z',
      comment: 'patching',
      durationMinutes: 30,
      recur: 'week'
    })

    expect(JSON.parse(seen[0]!.body)).toEqual({
      downtime_type: 'hostgroup',
      hostgroup_name: 'linux',
      start_time: '2026-09-23T08:00:00Z',
      end_time: '2026-09-23T10:00:00Z',
      comment: 'patching',
      duration: 30,
      recur: 'week'
    })
  })

  it('schedules a group downtime and its child hosts in one request', async () => {
    const seen: SeenRequest[] = []
    server.use(
      http.post(`${API_BASE}/domain-types/downtime/collections/host`, async ({ request }) => {
        seen.push(await snapshot(request))
        return new HttpResponse(null, { status: 204 })
      })
    )

    await commands.downtimeHostgroup(
      CMK_BASE,
      'linux',
      {
        startTime: '2026-09-23T08:00:00Z',
        endTime: '2026-09-23T10:00:00Z',
        comment: 'patching',
        durationMinutes: 0,
        recur: 'fixed'
      },
      ['access01']
    )

    expect(seen).toHaveLength(1)
    expect(JSON.parse(seen[0]!.body)).toMatchObject({
      downtime_type: 'host_by_query',
      query: {
        op: 'or',
        expr: [
          { op: '>=', left: 'groups', right: 'linux' },
          { op: 'or', expr: [{ op: '=', left: 'name', right: 'access01' }] }
        ]
      }
    })
  })

  it('looks up child hosts at the connection site', async () => {
    const replies = [[{ id: 'access01' }], []]
    server.use(
      http.post(`${API_BASE}/domain-types/host/collections/all`, () =>
        HttpResponse.json({ value: replies.shift() ?? [] })
      )
    )

    await expect(commands.childHosts(CMK_BASE, ['core01'])).resolves.toEqual(['access01'])
  })

  it('asks the connection site for every host of a host group', async () => {
    const seen: SeenRequest[] = []
    server.use(
      http.post(`${API_BASE}/domain-types/host/collections/all`, async ({ request }) => {
        seen.push(await snapshot(request))
        return HttpResponse.json({ value: [{ id: 'core01' }, { id: 'core02' }] })
      })
    )

    await expect(commands.hostgroupHosts(CMK_BASE, 'switches')).resolves.toEqual([
      'core01',
      'core02'
    ])
    expect(JSON.parse(seen[0]!.body)).toEqual({
      columns: ['name'],
      query: { op: '>=', left: 'groups', right: 'switches' }
    })
  })

  it('sends REST commands as a JSON POST to the addressed site', async () => {
    const seen: SeenRequest[] = []
    server.use(
      http.post(`${API_BASE}/domain-types/downtime/actions/delete/invoke`, async ({ request }) => {
        seen.push(await snapshot(request))
        return HttpResponse.json({})
      })
    )

    await commands.removeDowntimeHost(CMK_BASE, 'srv01')

    expect(seen[0]!.headers.get('Content-Type')).toBe('application/json')
    expect(JSON.parse(seen[0]!.body)).toEqual({
      delete_type: 'params',
      host_name: 'srv01',
      service_descriptions: null
    })
  })

  it('maps REST error bodies to a status-carrying error', async () => {
    server.use(
      http.post(`${API_BASE}/domain-types/downtime/actions/delete/invoke`, () =>
        HttpResponse.json({ title: 'Not Found', detail: 'No such downtime' }, { status: 404 })
      )
    )

    await expect(commands.removeDowntimeHost(CMK_BASE, 'srv01')).rejects.toMatchObject({
      name: 'CmkApiError',
      statusCode: 404,
      message: 'Not Found: No such downtime'
    })
  })
})
