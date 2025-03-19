/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { cmkFetch } from '@/lib/cmkFetch'

import { afterAll, afterEach, beforeAll } from 'vitest'
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'

const data = {
  some_random_playload: 123
}

export const restHandlers = [
  http.get('some_random_url', () => {
    return HttpResponse.json(data)
  }),
  http.get('some_broken_endpoint', () => {
    return HttpResponse.json(data, { status: 418 })
  }),
  http.get('some_endpoint_with_crashreport_response', () => {
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

// Start server before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))

// Close server after all tests
afterAll(() => server.close())

// Reset handlers after each test for test isolation
afterEach(() => server.resetHandlers())

test('simple fetch', async () => {
  const result = await cmkFetch('some_random_url', {})
  expect(await result.json()).toEqual(data)
})

test('raiseForStatus that should pass', async () => {
  const result = await cmkFetch('some_random_url', {})
  await result.raiseForStatus()
  expect(await result.json()).toEqual(data)
})

test('raiseForStatus that should fail', async () => {
  const result = await cmkFetch('some_broken_endpoint', {})
  await expect(async () => await result.raiseForStatus()).rejects.toThrowError(
    expect.objectContaining({
      context: "GET http://localhost:3000/some_broken_endpoint\nSTATUS 418: I'm a Teapot"
    })
  )
})

test('raiseForStatus for an known error', async () => {
  const result = await cmkFetch('some_endpoint_with_crashreport_response', {})
  await expect(async () => await result.raiseForStatus()).rejects.toThrowError(
    expect.objectContaining({
      message: 'some_title: some_detail',
      context:
        'GET http://localhost:3000/some_endpoint_with_crashreport_response\nSTATUS 500: Internal Server Error\n\nCrash report: random_href'
    })
  )
})
