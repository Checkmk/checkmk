/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { SessionApi } from '@/maps/api/session'
import { MapsAuthService } from '@/maps/services/MapsAuthService'

import { aSession, fullCapabilities } from '../support/services'

// Simulating the session endpoint with msw runs the real transport, so URL
// building and the 401 -> hand off to the login are covered too.

const sampleCaps = fullCapabilities({
  may_edit: false,
  configure: false,
  commands: ['acknowledge', 'schedule_downtime']
})

const sampleSession = aSession({ capabilities: sampleCaps })

const SESSION_ENDPOINT = '/domain-types/maps_session/collections/all'

let sessionCalls: number

const server = useMswServer(
  restApiHttp.get(SESSION_ENDPOINT, ({ response }) => {
    sessionCalls += 1
    return response(200).json(sampleSession)
  })
)

const originalLocation = window.location
let assignMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  sessionCalls = 0
  assignMock = vi.fn()
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { href: 'http://localhost/heute/check_mk/maps.py', assign: assignMock }
  })
})

afterEach(() => {
  vi.useRealTimers()
  Object.defineProperty(window, 'location', { configurable: true, value: originalLocation })
})

function newService(): MapsAuthService {
  return new MapsAuthService(new SessionApi())
}

describe('MapsAuthService', () => {
  it('starts without a session', () => {
    expect(newService().user.value).toBeNull()
  })

  it('derives the user from the capabilities of the session', async () => {
    const auth = newService()

    expect(await auth.refresh()).toBe(true)

    expect(auth.user.value?.user_id).toBe('cmkadmin')
    expect(auth.user.value?.command_permissions).toEqual(sampleCaps.commands)
    expect(auth.isAdmin.value).toBe(false)
    expect(auth.canConfigure.value).toBe(false)
    expect(auth.canCreateMaps.value).toBe(false)
  })

  it('reports the commands the user may send', async () => {
    const auth = newService()
    await auth.refresh()
    expect(auth.mayCommand('acknowledge')).toBe(true)
    expect(auth.mayCommand('force_check')).toBe(false)
  })

  it('bounces to the Checkmk login when the session is gone', async () => {
    const auth = newService()
    await auth.refresh()
    // A dead session answers 401, which is what sends the SPA to the login.
    server.use(
      restApiHttp.get(SESSION_ENDPOINT, ({ response }) =>
        response.untyped(
          HttpResponse.json({ title: 'Unauthorized', detail: 'no session' }, { status: 401 })
        )
      )
    )

    expect(await auth.refresh()).toBe(false)
    expect(auth.user.value).toBeNull()
    expect(assignMock).toHaveBeenCalledWith(expect.stringContaining('/login.py?_origtarget='))
  })

  it('keeps the session on a transient failure', async () => {
    const auth = newService()
    await auth.refresh()
    // The failure is logged, which is part of the behaviour under test.
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    server.use(
      restApiHttp.get(SESSION_ENDPOINT, ({ response }) => response.untyped(HttpResponse.error()))
    )

    expect(await auth.refresh()).toBe(false)

    // A network blip must not brick the SPA until a reload.
    expect(auth.user.value?.user_id).toBe('cmkadmin')
    expect(assignMock).not.toHaveBeenCalled()
  })

  it('fetches the session exactly once however often init is awaited', async () => {
    const auth = newService()
    await auth.init()
    await auth.init()
    expect(sessionCalls).toBe(1)
    expect(auth.user.value).not.toBeNull()
  })

  it('fetches the session again while the SPA runs', async () => {
    // Only the interval, so the session request itself runs as usual.
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] })
    const auth = newService()
    await auth.init()

    vi.advanceTimersByTime(240_000)

    await vi.waitFor(() => expect(sessionCalls).toBe(2))
    auth.dispose()
  })

  it('fetches the session again after a transient failure', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] })
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    server.use(
      restApiHttp.get(SESSION_ENDPOINT, ({ response }) => response.untyped(HttpResponse.error()), {
        once: true
      })
    )
    const auth = newService()
    expect(await auth.refresh()).toBe(false)

    vi.advanceTimersByTime(240_000)

    await vi.waitFor(() => expect(auth.user.value?.user_id).toBe('cmkadmin'))
    auth.dispose()
  })

  it('stops fetching the session once disposed', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] })
    const auth = newService()
    await auth.init()
    auth.dispose()

    vi.advanceTimersByTime(240_000)

    expect(sessionCalls).toBe(1)
  })

  it('clears the session and redirects on logout', async () => {
    const auth = newService()
    await auth.refresh()

    auth.logout()

    expect(auth.user.value).toBeNull()
    expect(assignMock).toHaveBeenCalledWith(expect.stringContaining('/logout.py'))
  })

  it('surfaces an unexpected failure as a status-carrying error', async () => {
    server.use(
      restApiHttp.get(SESSION_ENDPOINT, ({ response }) =>
        response.untyped(new HttpResponse(null, { status: 500 }))
      )
    )
    await expect(new SessionApi().fetchSession()).rejects.toBeInstanceOf(CmkApiError)
  })
})
