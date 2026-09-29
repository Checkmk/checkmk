/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Api } from 'cmk-ui-library/lib/api-client'
import { StaleSession, StaleSessionError } from 'cmk-ui-library/lib/staleSession'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'
import { beforeEach, vi } from 'vitest'

const SITE = 'http://localhost:3000/mysite/check_mk/'

useMswServer(
  http.get(`${SITE}sidebar_snapin.py`, () =>
    HttpResponse.redirect(`${SITE}login.py?_origtarget=sidebar_snapin.py`, 302)
  ),
  http.get(`${SITE}login.py`, () => HttpResponse.html('<html>Login</html>')),
  http.get(`${SITE}ajax_fine.py`, () => HttpResponse.json({ result_code: 0, result: 'ok' })),
  http.all(`${SITE}endpoint`, ({ request }) => {
    return HttpResponse.json({ result: request.method })
  })
)

beforeEach(() => {
  delete (window as unknown as Record<string, unknown>)[StaleSession.REPORTED_KEY]
  vi.spyOn(console, 'warn').mockImplementation(() => {})
})

test('a request redirected to the login page fails as a stale session', async () => {
  await expect(new Api(SITE).get('sidebar_snapin.py')).rejects.toBeInstanceOf(StaleSessionError)
})

test('a raw request redirected to the login page fails as a stale session', async () => {
  await expect(new Api(SITE).getRaw('sidebar_snapin.py')).rejects.toBeInstanceOf(StaleSessionError)
})

test('a raw request with a valid session returns the ajax result', async () => {
  await expect(new Api(SITE).getRaw('ajax_fine.py')).resolves.toBe('ok')
})

test.each([
  { name: 'option', call: (api: Api) => api.option('endpoint'), method: 'OPTIONS' },
  { name: 'get', call: (api: Api) => api.get('endpoint'), method: 'GET' },
  { name: 'post', call: (api: Api) => api.post('endpoint', {}), method: 'POST' },
  { name: 'put', call: (api: Api) => api.put('endpoint', {}), method: 'PUT' },
  { name: 'delete', call: (api: Api) => api.delete('endpoint'), method: 'DELETE' },
  { name: 'getRaw', call: (api: Api) => api.getRaw('endpoint'), method: 'GET' },
  { name: 'postRaw', call: (api: Api) => api.postRaw('endpoint', {}), method: 'POST' }
])('$name sends a $method request', async ({ call, method }) => {
  const sentMethod = await call(new Api(SITE))
  expect(sentMethod).toBe(method)
})
