/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  createDaemonClient,
  formatDaemonError,
  unwrapDaemonResponse
} from 'cmk-ui-library/lib/daemon-client/client'
import { CmkApiError } from 'cmk-ui-library/lib/error'
import { afterEach, describe, expect, test, vi } from 'vitest'

function responseWith(status: number): Response {
  return new Response(null, { status })
}

describe('formatDaemonError', () => {
  test('uses a string detail as-is', () => {
    expect(formatDaemonError({ detail: 'Map not found' }, 404)).toBe('Map not found')
  })

  test('falls back to a message field', () => {
    expect(formatDaemonError({ message: 'boom' }, 500)).toBe('boom')
  })

  test('renders a validation list with its field locations', () => {
    const body = {
      detail: [
        { loc: ['body', 'objects', 0, 'name'], msg: 'field required' },
        { loc: ['body', 'view', 'type'], msg: 'Value error, unknown type' }
      ]
    }
    // The framework's own root element is dropped; what is left is what points the operator at
    // the offending field.
    expect(formatDaemonError(body, 422)).toBe(
      'objects.0.name: field required; view.type: unknown type'
    )
  })

  test('states the status when the body says nothing usable', () => {
    expect(formatDaemonError(null, 503)).toBe('HTTP 503')
    expect(formatDaemonError({ detail: [] }, 422)).toBe('HTTP 422')
  })
})

describe('unwrapDaemonResponse', () => {
  test('returns the data on success', () => {
    expect(unwrapDaemonResponse({ data: { a: 1 }, response: responseWith(200) })).toEqual({ a: 1 })
  })

  test('returns undefined for a no-content response', () => {
    expect(unwrapDaemonResponse({ response: responseWith(204) })).toBeUndefined()
  })

  test('throws an error carrying the status, so callers can branch on it', () => {
    // The reason this is not lib/rest-api-client's unwrap: a create dialog has to tell 409
    // "already exists" from 422 "invalid" to say anything useful.
    try {
      unwrapDaemonResponse({ error: { detail: 'already exists' }, response: responseWith(409) })
      expect.unreachable('should have thrown')
    } catch (e) {
      expect(e).toBeInstanceOf(CmkApiError)
      expect((e as CmkApiError).statusCode).toBe(409)
      expect((e as CmkApiError).message).toBe('already exists')
    }
  })

  test('throws on a non-ok response even when the body parsed', () => {
    expect(() => unwrapDaemonResponse({ data: {}, response: responseWith(500) })).toThrow(
      CmkApiError
    )
  })
})

/** The smallest shape openapi-fetch needs to type a GET — enough to call the client honestly. */
interface TestPaths {
  '/thing': {
    get: {
      responses: {
        200: { content: { 'application/json': { ok: boolean } } }
      }
    }
  }
}

describe('createDaemonClient', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  test('asks the auth hook per request, so a rotated credential is picked up', async () => {
    const tokens = ['first', 'second']
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation(async () => new Response('{}', { status: 200 }))

    const client = createDaemonClient<TestPaths>({
      baseUrl: 'https://example.invalid/api/v1',
      auth: { headers: () => ({ 'X-Ticket': tokens.shift()! }) }
    })

    await client.GET('/thing')
    await client.GET('/thing')

    const sent = fetchSpy.mock.calls.map(([request]) =>
      (request as Request).headers.get('X-Ticket')
    )
    expect(sent).toEqual(['first', 'second'])
  })

  test('sends no credential header when no hook is configured', async () => {
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation(async () => new Response('{}', { status: 200 }))

    const client = createDaemonClient<TestPaths>({
      baseUrl: 'https://example.invalid/api/v1'
    })
    await client.GET('/thing')

    expect((fetchSpy.mock.calls[0]![0] as Request).headers.get('X-Ticket')).toBeNull()
  })
})
