/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'

import type { CmkApiError } from '@/lib/error'
import { createClient, unwrap } from '@/lib/rest-api-client/client'

const EXAMPLE_DATA = {
  some_random_playload: 123
}

const BASE_URL = 'http://foo.bar'
const VALID_ENDPOINT = '/valid-endpoint'
const BROKEN_ENDPOINT = '/broken-endpoint'
const BROKEN_ENDPOINT_WITH_CRASHREPORT = '/broken-endpoint-with-crashreport'

const restHandlers = [
  http.get(`${BASE_URL}${VALID_ENDPOINT}`, () => {
    return HttpResponse.json(EXAMPLE_DATA, { status: 200 })
  }),
  http.get(`${BASE_URL}${BROKEN_ENDPOINT}`, () => {
    return HttpResponse.json(EXAMPLE_DATA, { status: 418 })
  }),
  http.get(`${BASE_URL}${BROKEN_ENDPOINT_WITH_CRASHREPORT}`, () => {
    return HttpResponse.json(
      {
        detail: 'some_detail',
        title: 'some_title',
        ext: { details: { crash_report_url: { href: 'random_href' } } }
      },
      { status: 500 }
    )
  })
]

const server = setupServer(...restHandlers)
let client: ReturnType<typeof createClient>

beforeAll(() => {
  // NOTE: server.listen must be called before `createClient` is used to ensure
  // the msw can inject its version of `fetch` to intercept the requests.
  server.listen({ onUnhandledRequest: 'error' })
  client = createClient({ baseUrl: BASE_URL })
})
afterAll(() => server.close())
afterEach(() => server.resetHandlers())

test('simple get', async () => {
  /* @ts-expect-error Testing mock endpoint */
  const { data, error } = await client.GET(VALID_ENDPOINT)

  expect(error).toBeUndefined()
  expect(data).toEqual(EXAMPLE_DATA)
})

test('simple get with unwrap', async () => {
  /* @ts-expect-error Testing mock endpoint */
  const data = unwrap(await client.GET(VALID_ENDPOINT))
  expect(data).toEqual(EXAMPLE_DATA)
})

test('unwrap throws CmkApiError with status and context', async () => {
  /* @ts-expect-error Testing mock endpoint */
  const result = await client.GET(BROKEN_ENDPOINT)

  try {
    unwrap(result)
    throw new Error('Expected unwrap to throw')
  } catch (e) {
    const apiError = e as CmkApiError
    expect(apiError.context).toContain(`${BASE_URL}${BROKEN_ENDPOINT}`)
    expect(apiError.context).toContain("STATUS 418: I'm a Teapot")
    expect(apiError.message).toBe('Error in fetch response')
  }
})

test('unwrap includes crash report details in error', async () => {
  /* @ts-expect-error Testing mock endpoint */
  const result = await client.GET(BROKEN_ENDPOINT_WITH_CRASHREPORT)

  try {
    unwrap(result)
    throw new Error('Expected unwrap to throw')
  } catch (e) {
    const apiError = e as CmkApiError
    expect(apiError.context).toContain('STATUS 500: Internal Server Error')
    expect(apiError.context).toContain('Crash report: random_href')
    expect(apiError.message).toBe('some_title: some_detail')
  }
})
