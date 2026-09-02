/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { HttpResponse, http } from 'msw'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ImagesApi } from '@/maps/api/images'
import { TicketApi, checkmkLoginUrl, checkmkLogoutUrl } from '@/maps/api/ticket'

import { type SeenRequest, snapshot, useMswServer } from '../support/http'
import { fullCapabilities } from '../support/services'

const sampleTicket = {
  ticket: 'tkt',
  user_id: 'cmkadmin',
  language: 'en',
  capabilities: fullCapabilities()
}

vi.mock('cmk-ui-library/lib/rest-api-client/client', async (importOriginal) => {
  const { interceptableRestClient } = await import('../support/http')
  return interceptableRestClient(await importOriginal<Record<string, unknown>>())
})

const server = useMswServer()

describe('handing off to the Checkmk GUI', () => {
  const originalLocation = window.location

  afterEach(() => {
    Object.defineProperty(window, 'location', { configurable: true, value: originalLocation })
  })

  // The SPA is a page of the GUI it hands off to, so login and logout resolve
  // against its own URL rather than a configured base.
  it('derives the login and logout URLs from the page it is served on', () => {
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: new URL('http://mon.example/heute/check_mk/maps.py?name=dc1')
    })
    expect(checkmkLoginUrl()).toContain('http://mon.example/heute/check_mk/login.py')
    expect(checkmkLogoutUrl()).toBe('http://mon.example/heute/check_mk/logout.py')
  })
})

// Everything the SPA asks Checkmk itself for is an endpoint of the internal REST
// API, rooted at /api/internal (no base injected under jsdom, so the URL
// resolves against the page origin). These assert the HTTP shape the SPA
// depends on.
describe('the internal REST transport', () => {
  it('scopes the ticket handshake to the open map', async () => {
    const seen: SeenRequest[] = []
    server.use(
      http.get('*/api/internal/domain-types/maps_ticket/collections/all', async ({ request }) => {
        seen.push(await snapshot(request))
        return HttpResponse.json(sampleTicket)
      })
    )

    const ticket = await new TicketApi().fetchTicket('My Map')

    expect(seen).toHaveLength(1)
    expect(seen[0]!.url.searchParams.get('name')).toBe('My Map')
    expect(ticket).toEqual(sampleTicket)
  })

  // A session that ended answers 401, which is what makes the auth service hand
  // off to the Checkmk login instead of retrying.
  it('reports a lost session as a 401', async () => {
    server.use(
      http.get('*/api/internal/domain-types/maps_ticket/collections/all', () =>
        HttpResponse.json(
          { title: 'Unauthorized', detail: 'You are not authorized' },
          { status: 401 }
        )
      )
    )

    await expect(new TicketApi().fetchTicket()).rejects.toMatchObject({
      name: 'CmkApiError',
      statusCode: 401,
      message: 'Unauthorized: You are not authorized'
    })
  })

  it('sends an uploaded file base64-encoded in the JSON body', async () => {
    const seen: SeenRequest[] = []
    server.use(
      http.post('*/api/internal/domain-types/maps_image/collections/all', async ({ request }) => {
        seen.push(await snapshot(request))
        return HttpResponse.json({ name: 'server.svg', url: 'images/server.svg', builtin: false })
      })
    )

    await new ImagesApi().upload(new File(['<svg />'], 'server.svg', { type: 'image/svg+xml' }))

    expect(seen[0]!.headers.get('Content-Type')).toBe('application/json')
    expect(JSON.parse(seen[0]!.body)).toEqual({
      filename: 'server.svg',
      content_type: 'image/svg+xml',
      content: btoa('<svg />')
    })
  })

  it('asks to force a delete only once the operator confirmed the usage', async () => {
    const seen: SeenRequest[] = []
    server.use(
      http.delete('*/api/internal/objects/maps_image/server.svg', async ({ request }) => {
        seen.push(await snapshot(request))
        return new HttpResponse(null, { status: 204 })
      })
    )

    expect(await new ImagesApi().delete('server.svg')).toEqual([])
    await new ImagesApi().delete('server.svg', true)

    expect(seen[0]!.url.searchParams.get('force')).toBe('false')
    expect(seen[1]!.url.searchParams.get('force')).toBe('true')
  })

  // A refused delete is a 409, not a 200 that deleted nothing — the maps it
  // would have broken ride in the problem body so the dialog can name them.
  it('reads the blocking maps off a refused delete instead of raising', async () => {
    const usage = [{ map: 'dc1', alias: 'Data center', object_ids: ['o1'], is_background: false }]
    server.use(
      http.delete('*/api/internal/objects/maps_image/server.svg', () =>
        HttpResponse.json(
          { title: 'Conflict', detail: 'still in use', ext: { usage } },
          { status: 409 }
        )
      )
    )

    expect(await new ImagesApi().delete('server.svg')).toEqual(usage)
  })

  it('maps a REST error body to a status-carrying error', async () => {
    server.use(
      http.delete('*/api/internal/objects/maps_image/server.svg', () =>
        HttpResponse.json({ title: 'Forbidden', detail: 'denied' }, { status: 403 })
      )
    )

    await expect(new ImagesApi().delete('server.svg')).rejects.toMatchObject({
      name: 'CmkApiError',
      statusCode: 403,
      message: 'Forbidden: denied'
    })
  })
})
