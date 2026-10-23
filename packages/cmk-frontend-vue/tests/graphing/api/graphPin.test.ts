/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, describe, expect, test, vi } from 'vitest'

import { loadGraphPin, saveGraphPin } from '@/graphing/api/graphPin'

const GET_PIN_PATH = '/domain-types/graph/actions/get_pin/invoke'
const SET_PIN_PATH = '/domain-types/graph/actions/set_pin/invoke'
const CONTENT_TYPE = { params: { header: { 'Content-Type': 'application/json' } } }

describe('loadGraphPin', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let getSpy: any

  beforeEach(() => {
    getSpy = vi.spyOn(client, 'GET')
  })

  function mockPinTime(pinTime: number | null): void {
    getSpy.mockResolvedValueOnce({
      data: { pin_time: pinTime },
      error: undefined,
      response: new Response(null, { status: 200 })
    } as never)
  }

  test('returns the persisted pin time', async () => {
    mockPinTime(1700000000)

    const pinTime = await loadGraphPin()

    expect(pinTime).toBe(1700000000)
    expect(getSpy).toHaveBeenCalledWith(GET_PIN_PATH)
  })

  test('returns null when no pin is set', async () => {
    mockPinTime(null)

    const pinTime = await loadGraphPin()

    expect(pinTime).toBeNull()
  })

  test('throws when the response is not ok', async () => {
    getSpy.mockResolvedValueOnce({
      data: undefined,
      error: {},
      response: new Response('', { status: 403, statusText: 'Forbidden' })
    } as never)

    await expect(loadGraphPin()).rejects.toThrow()
  })
})

describe('saveGraphPin', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let postSpy: any

  beforeEach(() => {
    postSpy = vi.spyOn(client, 'POST')
  })

  function mockNoContent(): void {
    postSpy.mockResolvedValueOnce({
      data: undefined,
      error: undefined,
      response: new Response(null, { status: 204 })
    } as never)
  }

  test('posts the pin timestamp', async () => {
    mockNoContent()

    await saveGraphPin(1700000000)

    expect(postSpy).toHaveBeenCalledWith(SET_PIN_PATH, {
      ...CONTENT_TYPE,
      body: { pin_time: 1700000000 }
    })
  })

  test('posts null to remove the pin', async () => {
    mockNoContent()

    await saveGraphPin(null)

    expect(postSpy).toHaveBeenCalledWith(SET_PIN_PATH, {
      ...CONTENT_TYPE,
      body: { pin_time: null }
    })
  })

  test('throws when the response is not ok', async () => {
    postSpy.mockResolvedValueOnce({
      data: undefined,
      error: {},
      response: new Response('', { status: 403, statusText: 'Forbidden' })
    } as never)

    await expect(saveGraphPin(1700000000)).rejects.toThrow()
  })
})
