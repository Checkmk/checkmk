/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { HttpResponse, http } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { CommandsApi } from '@/maps/api/commands'

import { type SeenRequest, snapshot, useMswServer } from '../support/http'

vi.mock('cmk-ui-library/lib/rest-api-client/client', async (importOriginal) => {
  const { interceptableRestClient } = await import('../support/http')
  return interceptableRestClient(await importOriginal<Record<string, unknown>>())
})

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
      comment: 'patching'
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

  it('lists downtimes via the REST collection and maps the wire items', async () => {
    const seen: SeenRequest[] = []
    server.use(
      http.get(`${API_BASE}/domain-types/downtime/collections/all`, async ({ request }) => {
        seen.push(await snapshot(request))
        return HttpResponse.json({
          value: [
            {
              id: '42',
              extensions: {
                site_id: 'heute',
                host_name: 'srv01',
                author: 'cmkadmin',
                comment: 'maintenance',
                start_time: '2026-07-02T10:00:00+00:00',
                end_time: '2026-07-02T12:00:00+00:00',
                is_service: false
              }
            }
          ]
        })
      })
    )

    const entries = await commands.listDowntimesHost(CMK_BASE, 'srv01')

    expect(seen[0]!.url.searchParams.get('host_name')).toBe('srv01')
    expect(seen[0]!.url.searchParams.get('downtime_type')).toBe('host')
    expect(entries).toEqual([
      {
        id: '42',
        site_id: 'heute',
        host_name: 'srv01',
        author: 'cmkadmin',
        comment: 'maintenance',
        start_time: '2026-07-02T10:00:00+00:00',
        end_time: '2026-07-02T12:00:00+00:00',
        type: 'host'
      }
    ])
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
