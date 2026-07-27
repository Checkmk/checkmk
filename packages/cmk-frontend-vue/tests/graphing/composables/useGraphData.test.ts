/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, waitFor } from '@testing-library/vue'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import { useGraphData } from '@/graphing/composables/useGraphData'
import type { RequestedTimeRange } from '@/graphing/types'

const UNIT: components['schemas']['ApiUnitFormat'] = {
  notation: 'decimal',
  symbol: '',
  precision: { type: 'auto', digits: 2 },
  convertible: true
}

const FETCHED = {
  metrics: [
    {
      metadata: { name: 'cpu', title: 'CPU', unit: UNIT, color: '#ff0000' },
      render: { stack: 'area', inverse: false, hidden: false },
      data_points: [1, 2, 3]
    }
  ],
  time_range: { start: 1_000, end: 2_000, step: 60 },
  horizontal_lines: []
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

beforeEach(() => {
  postSpy = vi.spyOn(client, 'POST')
  postSpy.mockResolvedValue({
    data: FETCHED,
    error: undefined,
    response: new Response('{}', { status: 200 })
  } as never)
})

afterEach(() => {
  vi.restoreAllMocks()
})

// The resize debounce registers onUnmounted, so this needs a mounted component.
function fetchFor(range: RequestedTimeRange, canvasWidth: number): void {
  const harness = defineComponent({
    setup() {
      useGraphData(
        () => [{ internal: '{"graphs": []}', add_type: null }],
        () => range,
        () => canvasWidth,
        () => 'max'
      )
      return () => h('div')
    }
  })
  render(harness)
}

async function requestedTimeRange(): Promise<{ start: number; end: number; step: number }> {
  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(1))
  return postSpy.mock.calls[0][1].body.requested_time_range
}

// The backend cannot serve a step finer than 60s, and asking for one only buys query load
// and holes in the series.
describe('useGraphData — requested resolution', () => {
  test('never asks for a step below a minute, however narrow the window', async () => {
    const halfMinute = { start: 1_000, end: 1_030 }

    fetchFor(halfMinute, 750)

    expect((await requestedTimeRange()).step).toBe(60)
  })
})
