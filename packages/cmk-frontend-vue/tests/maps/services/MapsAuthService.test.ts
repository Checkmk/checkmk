/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import { TicketApi } from '@/maps/api/ticket'
import { MapsAuthService } from '@/maps/services/MapsAuthService'

import { fullCapabilities } from '../support/services'

// The handshake goes through the session-authenticated internal REST endpoint.
// Simulating that boundary with msw runs the real transport, so URL building and
// the 401 -> hand off to the login are covered too.

const sampleCaps = fullCapabilities({
  may_edit: false,
  configure: false,
  commands: ['acknowledge', 'schedule_downtime']
})

const sampleTicket = {
  ticket: 'tkt-abc',
  stream_token: 'stream-abc',
  user_id: 'cmkadmin',
  language: 'en',
  capabilities: sampleCaps
}

vi.mock('cmk-ui-library/lib/rest-api-client/client', async (importOriginal) => {
  const { interceptableRestClient } = await import('../support/http')
  return interceptableRestClient(await importOriginal<Record<string, unknown>>())
})

const TICKET_ENDPOINT = '*/api/internal/domain-types/maps_ticket/collections/all'

let ticketCalls: number

const server = setupServer(
  http.get(TICKET_ENDPOINT, () => {
    ticketCalls += 1
    return HttpResponse.json(sampleTicket)
  })
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

const originalLocation = window.location
let assignMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  vi.clearAllMocks()
  ticketCalls = 0
  assignMock = vi.fn()
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { href: 'http://localhost/heute/check_mk/maps.py', assign: assignMock }
  })
})

afterEach(() => {
  Object.defineProperty(window, 'location', { configurable: true, value: originalLocation })
})

function newService(): MapsAuthService {
  return new MapsAuthService(new TicketApi())
}

describe('MapsAuthService', () => {
  it('starts without a session', () => {
    const auth = newService()
    expect(auth.user.value).toBeNull()
    expect(auth.daemonHeaders()).toBeUndefined()
  })

  it('mints a ticket and derives the user from its capabilities', async () => {
    const auth = newService()

    expect(await auth.refresh()).toBe(true)

    expect(auth.user.value?.user_id).toBe('cmkadmin')
    expect(auth.user.value?.command_permissions).toEqual(sampleCaps.commands)
    expect(auth.isAdmin.value).toBe(false)
    expect(auth.canConfigure.value).toBe(false)
    expect(auth.canCreateMaps.value).toBe(false)
  })

  it('hands the daemon transport the ticket, and the stream its own token', async () => {
    const auth = newService()
    await auth.refresh()
    // The credential only ever leaves through the hook, never as a value a
    // component could pass on.
    expect(auth.daemonHeaders()).toEqual({ 'X-Maps-Ticket': 'tkt-abc' })
    expect(auth.streamToken.value).toBe('stream-abc')
  })

  it('reports the commands the ticket allows', async () => {
    const auth = newService()
    await auth.refresh()
    expect(auth.mayCommand('acknowledge')).toBe(true)
    expect(auth.mayCommand('force_check')).toBe(false)
  })

  it('bounces to the Checkmk login when the session is gone', async () => {
    // A dead session answers 401, which is what sends the SPA to the login.
    server.use(
      http.get(TICKET_ENDPOINT, () =>
        HttpResponse.json({ title: 'Unauthorized', detail: 'no session' }, { status: 401 })
      )
    )
    const auth = newService()
    await auth.refresh()

    expect(await auth.refresh()).toBe(false)
    expect(auth.user.value).toBeNull()
    expect(auth.daemonHeaders()).toBeUndefined()
    expect(assignMock).toHaveBeenCalledWith(expect.stringContaining('/login.py?_origtarget='))
  })

  it('keeps the ticket on a transient failure so the next tick can retry', async () => {
    const auth = newService()
    await auth.refresh()
    // The retry is logged, which is part of the behaviour under test.
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    server.use(http.get(TICKET_ENDPOINT, () => HttpResponse.error()))

    expect(await auth.refresh()).toBe(false)

    // A network blip must not brick the SPA until a reload.
    expect(auth.daemonHeaders()).toEqual({ 'X-Maps-Ticket': 'tkt-abc' })
    expect(assignMock).not.toHaveBeenCalled()
  })

  it('mints exactly once however often init is awaited', async () => {
    const auth = newService()
    await auth.init()
    await auth.init()
    expect(ticketCalls).toBe(1)
    expect(auth.user.value).not.toBeNull()
  })

  it('re-mints when the stream is scoped to another map', async () => {
    const auth = newService()
    await auth.init('dc1')
    await auth.setStreamMap('dc1')
    expect(ticketCalls).toBe(1)
    await auth.setStreamMap('dc2')
    expect(ticketCalls).toBe(2)
  })

  it('clears the session and redirects on logout', async () => {
    const auth = newService()
    await auth.refresh()

    auth.logout()

    expect(auth.user.value).toBeNull()
    expect(auth.daemonHeaders()).toBeUndefined()
    expect(assignMock).toHaveBeenCalledWith(expect.stringContaining('/logout.py'))
  })

  it('surfaces an unexpected failure as a status-carrying error', async () => {
    server.use(http.get(TICKET_ENDPOINT, () => new HttpResponse(null, { status: 500 })))
    await expect(new TicketApi().fetchTicket()).rejects.toBeInstanceOf(CmkApiError)
  })
})
