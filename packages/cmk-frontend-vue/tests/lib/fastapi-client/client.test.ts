/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, describe, expect, expectTypeOf, test, vi } from 'vitest'

import { createFastApiClient } from '@/lib/fastapi-client/client'
import { unwrap } from '@/lib/rest-api-client/client'

interface TestPaths {
  '/thing': {
    get: {
      responses: {
        200: { content: { 'application/json': { ok: boolean } } }
      }
    }
  }
  '/things/{id}': {
    get: {
      parameters: { path: { id: string } }
      responses: {
        200: { content: { 'application/json': { id: string } } }
      }
    }
    delete: {
      parameters: { path: { id: string } }
      responses: {
        204: { content?: never }
      }
    }
  }
  '/things': {
    post: {
      requestBody: { content: { 'application/json': { name: string } } }
      responses: {
        201: { content: { 'application/json': { id: string } } }
        409: { content: { 'application/json': { detail: string } } }
        422: { content: { 'application/json': { detail: { loc: unknown[]; msg: string }[] } } }
      }
    }
  }
  '/events': {
    get: {
      responses: {
        200: { content: { 'text/event-stream': unknown } }
      }
    }
  }
}

const BASE_URL = 'https://example.invalid/api/v1'

function respondWith(response: () => Response): Request[] {
  const sent: Request[] = []
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (request) => {
    sent.push(request as Request)
    return response()
  })
  return sent
}

function json(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('createFastApiClient', () => {
  test('resolves to the success payload', async () => {
    respondWith(() => json({ ok: true }, 200))
    const api = createFastApiClient<TestPaths>({ baseUrl: BASE_URL })

    const payload = await api.GET('/thing')

    expect(payload).toEqual({ ok: true })
  })

  test.each([
    { status: 409, detail: 'Thing already exists' },
    { status: 500, detail: 'Internal failure' }
  ])('rejects a $status with its string detail', async ({ status, detail }) => {
    respondWith(() => json({ detail }, status))
    const api = createFastApiClient<TestPaths>({ baseUrl: BASE_URL })

    const call = api.POST('/things', { body: { name: 'a' } })

    await expect(call).rejects.toMatchObject({
      name: 'CmkApiError',
      message: detail
    })
  })

  test('rejects a 422 naming each invalid field', async () => {
    const body = {
      detail: [
        { loc: ['body', 'name'], msg: 'field required' },
        { loc: ['body', 'tags', 0], msg: 'Value error, unknown tag' }
      ]
    }
    respondWith(() => json(body, 422))
    const api = createFastApiClient<TestPaths>({ baseUrl: BASE_URL })

    const call = api.POST('/things', { body: { name: 'a' } })

    await expect(call).rejects.toMatchObject({
      name: 'CmkApiError',
      message: 'name: field required; tags.0: unknown tag'
    })
  })

  test('rejects an empty-body 503 with its status', async () => {
    respondWith(() => new Response(null, { status: 503 }))
    const api = createFastApiClient<TestPaths>({ baseUrl: BASE_URL })

    const call = api.GET('/thing')

    await expect(call).rejects.toMatchObject({
      name: 'CmkApiError',
      message: 'HTTP 503'
    })
  })

  test('resolves a 204 to undefined', async () => {
    respondWith(() => new Response(null, { status: 204 }))
    const api = createFastApiClient<TestPaths>({ baseUrl: BASE_URL })

    const payload = await api.DELETE('/things/{id}', { params: { path: { id: 'a' } } })

    expect(payload).toBeUndefined()
  })

  test('resolves a stream call to the response body stream', async () => {
    respondWith(
      () =>
        new Response('data: {}\n\n', {
          status: 200,
          headers: { 'Content-Type': 'text/event-stream' }
        })
    )
    const api = createFastApiClient<TestPaths>({ baseUrl: BASE_URL })

    const payload = await api.GET('/events', { parseAs: 'stream' })

    expect(payload).toBeInstanceOf(ReadableStream)
  })

  test('rejects a failed stream call like a JSON call', async () => {
    respondWith(() => json({ detail: 'Conversation not found' }, 404))
    const api = createFastApiClient<TestPaths>({ baseUrl: BASE_URL })

    const call = api.GET('/events', { parseAs: 'stream' })

    await expect(call).rejects.toMatchObject({
      name: 'CmkApiError',
      message: 'Conversation not found'
    })
  })

  test('asks the auth hook per request, so a rotated credential is picked up', async () => {
    const sent = respondWith(() => json({ ok: true }, 200))
    const tokens = ['first', 'second']
    const api = createFastApiClient<TestPaths>({
      baseUrl: BASE_URL,
      auth: { headers: () => ({ 'X-Ticket': tokens.shift()! }) }
    })

    await api.GET('/thing')
    await api.GET('/thing')

    expect(sent.map((request) => request.headers.get('X-Ticket'))).toEqual(['first', 'second'])
  })
})

describe('the schema types each call', () => {
  const api = createFastApiClient<TestPaths>({ baseUrl: BASE_URL })

  test('an unknown path does not compile', () => {
    // @ts-expect-error '/unknown' is not a path of the schema
    void (() => api.GET('/unknown'))
  })

  test('a missing required path parameter does not compile', () => {
    // @ts-expect-error '/things/{id}' requires the id
    void (() => api.GET('/things/{id}'))
  })

  test('a body of the wrong shape does not compile', () => {
    // @ts-expect-error name has to be a string
    void (() => api.POST('/things', { body: { name: 1 } }))
  })

  test('the payload is typed by the schema', () => {
    const getThing = () => api.GET('/thing')

    expectTypeOf(getThing).returns.resolves.toEqualTypeOf<{ ok: boolean }>()
    // @ts-expect-error the schema declares no such field
    void (async () => (await getThing()).missing)
  })

  test('the payload cannot be passed to the REST API unwrap', () => {
    const getThing = () => api.GET('/thing')

    expectTypeOf(getThing).returns.resolves.toEqualTypeOf<{ ok: boolean }>()
    // @ts-expect-error a payload carries no response to unwrap
    void (async () => unwrap(await getThing()))
  })
})
