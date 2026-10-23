/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cmkFetch } from 'cmk-ui-library/lib/cmkFetch'
import { CmkNetworkError } from 'cmk-ui-library/lib/error'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'

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
  }),
  http.get('some_unreachable_endpoint', () => {
    return HttpResponse.error()
  })
]

useMswServer(...restHandlers)

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

test('a request without response rejects with CmkNetworkError', async () => {
  await expect(cmkFetch('some_unreachable_endpoint', {})).rejects.toBeInstanceOf(CmkNetworkError)
})

test('a request aborted through its signal rejects with the abort reason', async () => {
  const controller = new AbortController()
  const reason = new Error('unmounted')
  controller.abort(reason)

  await expect(cmkFetch('some_random_url', { signal: controller.signal })).rejects.toBe(reason)
})
