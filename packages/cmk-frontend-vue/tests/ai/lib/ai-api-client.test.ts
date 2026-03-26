/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, vi } from 'vitest'

import { AiApiClient } from '@/ai/lib/ai-api-client'
import type { AiServiceAction, InfoResponse, StreamEvent } from '@/ai/lib/ai-api-client'

const SITE_NAME = 'test-site'
const ACTION: AiServiceAction = { action_id: 'explain', action_name: 'Explain' }
const CONTEXT_DATA = { host: 'myhost' }

function mockJsonResponse(body: unknown, ok = true): Response {
  return {
    ok,
    status: ok ? 200 : 500,
    body: null,
    json: vi.fn().mockResolvedValue(body),
    text: vi.fn().mockResolvedValue(JSON.stringify(body))
  } as unknown as Response
}

function makeStream(...events: unknown[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      for (const event of events) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`))
      }
      controller.close()
    }
  })
}

function mockStreamResponse(stream: ReadableStream<Uint8Array> | null, ok = true): Response {
  return {
    ok,
    status: ok ? 200 : 503,
    body: stream,
    text: vi.fn().mockResolvedValue('error body'),
    json: vi.fn()
  } as unknown as Response
}

let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Constructor', () => {
  test('sets baseUrl to ai-service/api/v1/', () => {
    const client = new AiApiClient(SITE_NAME)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((client as any).baseUrl).toBe('ai-service/api/v1/')
  })

  test('defaultHeaders contains required production headers with correct siteName', () => {
    const client = new AiApiClient('my-site')
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const headers = (client as any).defaultHeaders as Record<string, string>
    expect(headers['Content-Type']).toBe('application/json')
    expect(headers['Accept']).toBe('application/json')
    expect(headers['x-checkmk-site-name']).toBe('my-site')
  })

  test('defaultHeaders does not include local-testing-only headers', () => {
    const client = new AiApiClient(SITE_NAME)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const headers = (client as any).defaultHeaders as Record<string, string>
    expect(headers['x-forwarded-host']).toBeUndefined()
    expect(headers['x-forwarded-proto']).toBeUndefined()
  })
})

describe('getInfo', () => {
  test('calls GET info and returns the result as InfoResponse', async () => {
    const infoResponse: InfoResponse = {
      service_name: 'ai-service',
      version: '1.0.0',
      models: ['gpt-4'],
      provider: 'openai'
    }
    fetchMock.mockResolvedValue(mockJsonResponse(infoResponse))

    const client = new AiApiClient(SITE_NAME)
    const result = await client.getInfo()

    expect(fetchMock).toHaveBeenCalledOnce()
    expect(fetchMock.mock.calls[0]![0]).toBe('ai-service/api/v1/info')
    expect(result).toEqual(infoResponse)
  })
})

describe('getUserActions', () => {
  test('calls GET enumerate-action-types with the correct templateId', async () => {
    const actions: AiServiceAction[] = [{ action_id: 'explain', action_name: 'Explain' }]
    fetchMock.mockResolvedValue(mockJsonResponse({ all_possible_action_types: actions }))

    const client = new AiApiClient(SITE_NAME)
    await client.getUserActions('my-template')

    expect(fetchMock).toHaveBeenCalledOnce()
    expect(fetchMock.mock.calls[0]![0]).toBe(
      'ai-service/api/v1/enumerate-action-types?template_id=my-template'
    )
  })

  test('returns the list from all_possible_action_types', async () => {
    const actions: AiServiceAction[] = [
      { action_id: 'explain', action_name: 'Explain' },
      { action_id: 'summarize', action_name: 'Summarize' }
    ]
    fetchMock.mockResolvedValue(mockJsonResponse({ all_possible_action_types: actions }))

    const client = new AiApiClient(SITE_NAME)
    const result = await client.getUserActions('any-template')

    expect(result).toEqual(actions)
  })
})

describe('streamInference', () => {
  test('makes a POST to stream-inference with correct URL, method, headers, and body', async () => {
    fetchMock.mockResolvedValue(mockStreamResponse(makeStream()))
    const client = new AiApiClient(SITE_NAME)

    await client.streamInference(ACTION, CONTEXT_DATA, vi.fn())

    expect(fetchMock).toHaveBeenCalledOnce()
    const [url, init] = fetchMock.mock.calls[0]! as [string, RequestInit]
    expect(url).toBe('ai-service/api/v1/stream-inference')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({
      action_type: ACTION,
      context_data: CONTEXT_DATA
    })
    const headers = init.headers as Record<string, string>
    expect(headers['Content-Type']).toBe('application/json')
    expect(headers['Accept']).toBe('application/json')
    expect(headers['x-checkmk-site-name']).toBe(SITE_NAME)
    expect(headers['x-saas-request-id']).toBeDefined()
    expect(headers['x-forwarded-host']).toBeUndefined()
  })

  test('passes the AbortSignal to fetch when provided', async () => {
    fetchMock.mockResolvedValue(mockStreamResponse(makeStream()))
    const controller = new AbortController()
    const client = new AiApiClient(SITE_NAME)

    await client.streamInference(
      ACTION,
      CONTEXT_DATA,
      vi.fn(),
      undefined,
      undefined,
      controller.signal
    )

    const [, init] = fetchMock.mock.calls[0]! as [string, RequestInit]
    expect(init.signal).toBe(controller.signal)
  })

  test('passes null as signal when AbortSignal is not provided', async () => {
    fetchMock.mockResolvedValue(mockStreamResponse(makeStream()))
    const client = new AiApiClient(SITE_NAME)

    await client.streamInference(ACTION, CONTEXT_DATA, vi.fn())

    const [, init] = fetchMock.mock.calls[0]! as [string, RequestInit]
    expect(init.signal).toBeNull()
  })

  test('calls onEvent for each parsed StreamEvent yielded by the stream', async () => {
    const events: StreamEvent[] = [
      { type: 'thinking', text: 'reasoning...' },
      { type: 'answer', text: 'final answer' },
      { type: 'finish' }
    ]
    fetchMock.mockResolvedValue(mockStreamResponse(makeStream(...events)))
    const onEvent = vi.fn()
    const client = new AiApiClient(SITE_NAME)

    await client.streamInference(ACTION, CONTEXT_DATA, onEvent)

    expect(onEvent).toHaveBeenCalledTimes(3)
    expect(onEvent).toHaveBeenNthCalledWith(1, events[0])
    expect(onEvent).toHaveBeenNthCalledWith(2, events[1])
    expect(onEvent).toHaveBeenNthCalledWith(3, events[2])
  })

  test('calls onComplete when the last event is a finish event', async () => {
    fetchMock.mockResolvedValue(
      mockStreamResponse(makeStream({ type: 'answer', text: 'done' }, { type: 'finish' }))
    )
    const onComplete = vi.fn()
    const client = new AiApiClient(SITE_NAME)

    await client.streamInference(ACTION, CONTEXT_DATA, vi.fn(), undefined, onComplete)

    expect(onComplete).toHaveBeenCalledOnce()
  })

  test('calls onError when stream ends without a finish event', async () => {
    fetchMock.mockResolvedValue(mockStreamResponse(makeStream({ type: 'answer', text: 'partial' })))
    const onEvent = vi.fn()
    const onError = vi.fn()
    const onComplete = vi.fn()
    const client = new AiApiClient(SITE_NAME)

    await client.streamInference(ACTION, CONTEXT_DATA, onEvent, onError, onComplete)

    expect(onEvent).toHaveBeenCalledOnce()
    expect(onComplete).not.toHaveBeenCalled()
    expect(onError).toHaveBeenCalledOnce()
    expect((onError.mock.calls[0]![0] as Error).message).toBe(
      'Stream did not complete successfully'
    )
  })

  test('calls onError when an error event is received', async () => {
    fetchMock.mockResolvedValue(
      mockStreamResponse(
        makeStream(
          { type: 'answer', text: 'partial' },
          { type: 'error', message: 'something broke' }
        )
      )
    )
    const onEvent = vi.fn()
    const onError = vi.fn()
    const onComplete = vi.fn()
    const client = new AiApiClient(SITE_NAME)

    await client.streamInference(ACTION, CONTEXT_DATA, onEvent, onError, onComplete)

    expect(onComplete).not.toHaveBeenCalled()
    expect(onError).toHaveBeenCalledOnce()
    expect((onError.mock.calls[0]![0] as Error).message).toContain('something broke')
  })

  test('does not forward the error event to onEvent', async () => {
    fetchMock.mockResolvedValue(
      mockStreamResponse(
        makeStream({ type: 'answer', text: 'before error' }, { type: 'error', message: 'fail' })
      )
    )
    const onEvent = vi.fn()
    const client = new AiApiClient(SITE_NAME)

    await client.streamInference(ACTION, CONTEXT_DATA, onEvent, vi.fn())

    expect(onEvent).toHaveBeenCalledOnce()
    expect(onEvent).toHaveBeenCalledWith({ type: 'answer', text: 'before error' })
  })

  test('calls onError when fetch rejects with a network error', async () => {
    const networkError = new Error('Network failure')
    fetchMock.mockRejectedValue(networkError)
    const onError = vi.fn()
    const client = new AiApiClient(SITE_NAME)

    await client.streamInference(ACTION, CONTEXT_DATA, vi.fn(), onError)

    expect(onError).toHaveBeenCalledOnce()
    expect(onError).toHaveBeenCalledWith(networkError)
  })

  test('calls onError when res.ok is false and includes the response text in the error message', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 503,
      text: vi.fn().mockResolvedValue('Service Unavailable'),
      body: null
    } as unknown as Response)
    const onError = vi.fn()
    const client = new AiApiClient(SITE_NAME)

    await client.streamInference(ACTION, CONTEXT_DATA, vi.fn(), onError)

    expect(onError).toHaveBeenCalledOnce()
    expect((onError.mock.calls[0]![0] as Error).message).toContain('Service Unavailable')
  })

  test('calls onError when res.body is null', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      body: null,
      text: vi.fn()
    } as unknown as Response)
    const onError = vi.fn()
    const client = new AiApiClient(SITE_NAME)

    await client.streamInference(ACTION, CONTEXT_DATA, vi.fn(), onError)

    expect(onError).toHaveBeenCalledOnce()
    expect((onError.mock.calls[0]![0] as Error).message).toBe(
      'Stream inference response body is null'
    )
  })
})
