/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import type { FlowQueryParams, FlowsResponse } from '@/network-flow/flow-explorer/api/flows'
import { FlowService } from '@/network-flow/flow-explorer/services/FlowService'

import { makeKeyShortcutService } from '../../monitoring/shared/services/testHelpers'

function makeResponse(overrides: Partial<FlowsResponse['meta']> = {}): FlowsResponse {
  return {
    flows: [],
    meta: {
      limit: 100,
      offset: 0,
      matched: 5_000,
      total: 5_000,
      max_offset: 50_000,
      ...overrides
    }
  }
}

function makeService(response: FlowsResponse = makeResponse()) {
  const listFlows = vi.fn<(params: FlowQueryParams) => Promise<FlowsResponse>>(() =>
    Promise.resolve(response)
  )
  const service = new FlowService({ listFlows }, makeKeyShortcutService(), {
    limitTiers: [100, 500]
  })
  return { listFlows, service }
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

test('requests the smallest offered page size first', async () => {
  const { listFlows, service } = makeService()

  await vi.advanceTimersByTimeAsync(0)

  expect(listFlows).toHaveBeenCalledWith({ limit: 100, offset: 0 }, expect.anything())

  service.stopPolling()
})

test('sends the offset when paging', async () => {
  const { listFlows, service } = makeService()
  await vi.advanceTimersByTimeAsync(0)

  service.nextPage()
  await vi.advanceTimersByTimeAsync(0)

  expect(listFlows).toHaveBeenLastCalledWith({ limit: 100, offset: 100 }, expect.anything())

  service.stopPolling()
})

test('maps the response meta onto the shared paging state', async () => {
  const { service } = makeService(makeResponse({ offset: 200, matched: 1_247_302 }))

  await vi.advanceTimersByTimeAsync(0)

  expect(service.offset.value).toBe(200)
  expect(service.maxOffset.value).toBe(50_000)
  expect(service.matched.value).toBe(1_247_302)

  service.stopPolling()
})
