/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type FastApiEvent, createFastApiClient } from 'cmk-ui-library/lib/fastapi-client/client'
import { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'
import { describe, expect, expectTypeOf, test, vi } from 'vitest'

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
  '/things/{id}/events': {
    get: {
      parameters: { path: { id: string } }
      responses: {
        200: { content: { 'text/event-stream': ThingEvent } }
      }
    }
  }
}

type ThingEvent =
  | { event: 'renamed'; data: { name: string }; id?: string }
  | { event: 'deleted'; data: { reason: string }; id?: string }

const BASE_URL = 'https://example.invalid/api/v1'

function respondWith(response: (request: Request) => Response): Request[] {
  const sent: Request[] = []
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (request) => {
    sent.push(request as Request)
    return response(request as Request)
  })
  return sent
}

function eventStream(body: BodyInit): Response {
  return new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}

function idleEventStream(signal: AbortSignal): Response {
  return eventStream(
    new ReadableStream<Uint8Array>({
      start(controller) {
        signal.addEventListener('abort', () => controller.error(signal.reason))
      }
    })
  )
}

async function collect<T>(events: AsyncIterable<T>): Promise<T[]> {
  const collected: T[] = []
  for await (const event of events) {
    collected.push(event)
  }
  return collected
}

function json(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

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
  ])('rejects a $status with its string detail and status', async ({ status, detail }) => {
    respondWith(() => json({ detail }, status))
    const api = createFastApiClient<TestPaths>({ baseUrl: BASE_URL })

    const call = api.POST('/things', { body: { name: 'a' } })

    await expect(call).rejects.toMatchObject({
      name: 'CmkApiError',
      message: detail,
      statusCode: status
    })
  })

  test('rejects a 422 naming each invalid field and keeping the parsed body', async () => {
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
      message: 'name: field required; tags.0: unknown tag',
      body
    })
  })

  test('rejects an empty-body 503 with its status', async () => {
    respondWith(() => new Response(null, { status: 503 }))
    const api = createFastApiClient<TestPaths>({ baseUrl: BASE_URL })

    const call = api.GET('/thing')

    await expect(call).rejects.toMatchObject({
      name: 'CmkApiError',
      message: 'HTTP 503',
      statusCode: 503
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
      message: 'Conversation not found',
      statusCode: 404
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

describe('events', () => {
  test('yields each event with its name, data and id', async () => {
    respondWith(() =>
      eventStream(
        'event: renamed\ndata: {"name":"b"}\nid: 1\n\n: ping\n\nevent: deleted\ndata: {"reason":"gone"}\nid: 2\n\n'
      )
    )
    const api = createFastApiClient<TestPaths>({ baseUrl: BASE_URL })

    const events = await collect(
      api.events('/things/{id}/events', { params: { path: { id: 'a' } } })
    )

    expect(events).toEqual([
      { event: 'renamed', data: { name: 'b' }, id: '1' },
      { event: 'deleted', data: { reason: 'gone' }, id: '2' }
    ])
  })

  test('yields an event sent without an id without an id key', async () => {
    respondWith(() => eventStream('event: renamed\ndata: {"name":"b"}\n\n'))
    const api = createFastApiClient<TestPaths>({ baseUrl: BASE_URL })

    const events = await collect(
      api.events('/things/{id}/events', { params: { path: { id: 'a' } } })
    )

    expect(events).toStrictEqual([{ event: 'renamed', data: { name: 'b' } }])
  })

  test('requests the path with its parameters filled in', async () => {
    const sent = respondWith(() => eventStream(''))
    const api = createFastApiClient<TestPaths>({ baseUrl: BASE_URL })

    await collect(api.events('/things/{id}/events', { params: { path: { id: 'a' } } }))

    expect(sent.map((request) => request.url)).toEqual([`${BASE_URL}/things/a/events`])
  })

  test.each([
    { case: 'no headers', headers: {} },
    { case: 'an Accept header of its own', headers: { Accept: 'application/json' } }
  ])('asks for an event stream when init has $case', async ({ headers }) => {
    const sent = respondWith(() => eventStream(''))
    const api = createFastApiClient<TestPaths>({ baseUrl: BASE_URL })

    await collect(api.events('/things/{id}/events', { params: { path: { id: 'a' } }, headers }))

    expect(sent.map((request) => request.headers.get('Accept'))).toEqual(['text/event-stream'])
  })

  test('sends the headers of init', async () => {
    const sent = respondWith(() => eventStream(''))
    const api = createFastApiClient<TestPaths>({ baseUrl: BASE_URL })

    await collect(
      api.events('/things/{id}/events', {
        params: { path: { id: 'a' } },
        headers: { 'X-Trace': 'trace' }
      })
    )

    expect(sent.map((request) => request.headers.get('X-Trace'))).toEqual(['trace'])
  })

  test('rejects a failed call with its detail and status', async () => {
    respondWith(() => json({ detail: 'Thing not found' }, 404))
    const api = createFastApiClient<TestPaths>({ baseUrl: BASE_URL })

    const events = collect(api.events('/things/{id}/events', { params: { path: { id: 'a' } } }))

    await expect(events).rejects.toMatchObject({
      name: 'CmkApiError',
      message: 'Thing not found',
      statusCode: 404
    })
  })

  test('a response without a body fails the stream', async () => {
    respondWith(() => new Response(null, { status: 204 }))
    const api = createFastApiClient<TestPaths>({ baseUrl: BASE_URL })

    const events = collect(api.events('/things/{id}/events', { params: { path: { id: 'a' } } }))

    await expect(events).rejects.toThrow('returned no event stream')
  })

  test('yields no event read after the signal aborted', async () => {
    respondWith(() =>
      eventStream(
        'event: renamed\ndata: {"name":"b"}\nid: 1\n\nevent: renamed\ndata: {"name":"c"}\nid: 2\n\n'
      )
    )
    const api = createFastApiClient<TestPaths>({ baseUrl: BASE_URL })
    const controller = new AbortController()
    const events = api
      .events('/things/{id}/events', {
        params: { path: { id: 'a' } },
        signal: controller.signal
      })
      [Symbol.asyncIterator]()
    await events.next()

    controller.abort()

    await expect(events.next()).rejects.toBe(controller.signal.reason)
  })

  test('aborting the signal ends an idle stream with its reason', async () => {
    const sent = respondWith((request) => idleEventStream(request.signal))
    const api = createFastApiClient<TestPaths>({ baseUrl: BASE_URL })
    const controller = new AbortController()
    const events = collect(
      api.events('/things/{id}/events', {
        params: { path: { id: 'a' } },
        signal: controller.signal
      })
    )
    await vi.waitFor(() => expect(sent).toHaveLength(1))

    controller.abort()

    await expect(events).rejects.toBe(controller.signal.reason)
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

  test('events are typed by the schema', () => {
    const readEvents = () => api.events('/things/{id}/events', { params: { path: { id: 'a' } } })

    expectTypeOf(readEvents).returns.toEqualTypeOf<AsyncIterable<ThingEvent>>()
  })

  test('an event name with the data of another does not compile', () => {
    const event: FastApiEvent<TestPaths, '/things/{id}/events'> = {
      event: 'renamed',
      // @ts-expect-error a renamed event carries a name, not a reason
      data: { reason: 'gone' },
      id: '1'
    }

    void event
  })

  test('events of a path missing its required parameter do not compile', () => {
    // @ts-expect-error '/things/{id}/events' requires the id
    void (() => api.events('/things/{id}/events'))
  })

  test('a path without typed events cannot be read as events', () => {
    // @ts-expect-error '/events' declares no event of its stream
    void (() => api.events('/events'))
  })

  test('a path without a GET cannot be read as events', () => {
    // @ts-expect-error '/things' has no GET
    void (() => api.events('/things'))
  })

  test('the payload cannot be passed to the REST API unwrap', () => {
    const getThing = () => api.GET('/thing')

    expectTypeOf(getThing).returns.resolves.toEqualTypeOf<{ ok: boolean }>()
    // @ts-expect-error a payload carries no response to unwrap
    void (async () => unwrap(await getThing()))
  })
})
