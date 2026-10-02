/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cmkFetch } from 'cmk-ui-library/lib/cmkFetch'
import { CmkApiError } from 'cmk-ui-library/lib/error'
import { StaleSession, StaleSessionError } from 'cmk-ui-library/lib/staleSession'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, beforeEach, vi } from 'vitest'

const SITE = 'http://localhost:3000/mysite/check_mk'

const server = setupServer(
  http.get(`${SITE}/ajax_poll.py`, () =>
    HttpResponse.redirect(`${SITE}/login.py?_origtarget=ajax_poll.py`, 302)
  ),
  http.get(`${SITE}/login.py`, () => HttpResponse.html('<html>Login</html>')),
  http.get(`${SITE}/moved.py`, () => HttpResponse.redirect(`${SITE}/index.py`, 302)),
  http.get(`${SITE}/index.py`, () => HttpResponse.html('<html>Index</html>')),
  http.get(`${SITE}/denied.py`, () =>
    HttpResponse.text('Permission denied', { status: 401, statusText: 'Unauthorized' })
  ),
  http.get(`${SITE}/api/internal/version`, () =>
    HttpResponse.json({ title: 'Unauthorized', status: 401 }, { status: 401 })
  ),
  http.get(`${SITE}/ajax_fine.py`, () => HttpResponse.json({ result_code: 0, result: 'ok' }))
)

let warn: ReturnType<typeof vi.spyOn>

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterAll(() => server.close())

beforeEach(() => {
  delete (window as unknown as Record<string, unknown>)[StaleSession.REPORTED_KEY]
  warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
})

afterEach(() => {
  server.resetHandlers()
})

test('a request redirected to the login page fails as a stale session', async () => {
  await expect(cmkFetch(`${SITE}/ajax_poll.py`, {})).rejects.toBeInstanceOf(StaleSessionError)
})

test('a REST API request answered with 401 fails as a stale session', async () => {
  await expect(cmkFetch(`${SITE}/api/internal/version`, {})).rejects.toBeInstanceOf(
    StaleSessionError
  )
})

test('a stale session names the request that hit it, not the login page', async () => {
  await expect(cmkFetch(`${SITE}/ajax_poll.py`, {})).rejects.toSatisfy(
    (error) => error instanceof StaleSessionError && error.getContext() === `${SITE}/ajax_poll.py`
  )
})

test('a stale session reads as a 401 to callers that handle one', async () => {
  await expect(cmkFetch(`${SITE}/ajax_poll.py`, {})).rejects.toSatisfy(
    (error) => error instanceof CmkApiError && error.statusCode === 401
  )
})

test('a page denying access with 401 is not taken for a stale session', async () => {
  const response = await cmkFetch(`${SITE}/denied.py`, {})

  expect(response.status).toBe(401)
  expect(warn).not.toHaveBeenCalled()
})

test('a redirect to another page than the login is not taken for a stale session', async () => {
  const response = await cmkFetch(`${SITE}/moved.py`, {})

  expect(response.status).toBe(200)
  expect(warn).not.toHaveBeenCalled()
})

test('concurrent requests that hit a stale session report it once', async () => {
  await Promise.allSettled([
    cmkFetch(`${SITE}/ajax_poll.py`, {}),
    cmkFetch(`${SITE}/ajax_poll.py`, {}),
    cmkFetch(`${SITE}/api/internal/version`, {})
  ])

  expect(warn).toHaveBeenCalledTimes(1)
})

test('a request with a valid session reports nothing', async () => {
  const response = await cmkFetch(`${SITE}/ajax_fine.py`, {})

  expect(await response.json()).toEqual({ result_code: 0, result: 'ok' })
  expect(warn).not.toHaveBeenCalled()
})
