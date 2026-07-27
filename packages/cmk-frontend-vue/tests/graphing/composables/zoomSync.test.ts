/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { nextTick } from 'vue'

import { useGlobalTimeRange } from '@/graphing/GlobalTimePicker/useGlobalTimeRange'
import type { TimeRange } from '@/graphing/components/TimeSeriesGraph'
import { useGraphInteraction } from '@/graphing/composables/useGraphInteraction'
import { useRequestedTimeRange } from '@/graphing/composables/useRequestedTimeRange'
import type { RequestedTimeRange } from '@/graphing/types'

vi.mock('@/graphing/composables/useGlobalPin', async () => {
  const { computed } = await import('vue')
  return {
    useGlobalPin: () => ({
      pinTime: computed(() => null),
      ensurePinLoaded: vi.fn(),
      setPin: vi.fn(),
      clearPin: vi.fn()
    })
  }
})

const BASELINE: TimeRange = { start: 1_000, end: 2_000, step: 60 }
const INITIAL: RequestedTimeRange = { start: 1_000, end: 2_000 }

// A commit travels graph -> requested range -> global picker -> sibling graph.
async function settlePropagation(): Promise<void> {
  await nextTick()
  await nextTick()
}

function twoGraphsOnOnePage() {
  const zoomedGraphRange = useRequestedTimeRange(INITIAL)
  const siblingGraphRange = useRequestedTimeRange(INITIAL)
  const zoomedGraph = useGraphInteraction(
    () => BASELINE,
    () => false,
    () => zoomedGraphRange.value,
    (timeRange) => {
      zoomedGraphRange.value = { start: timeRange.start, end: timeRange.end }
    }
  )
  return { zoomedGraph, zoomedGraphRange, siblingGraphRange }
}

describe('zoom sync across the graphs on a page', () => {
  // The global picker store is a module-level singleton shared across the whole bundle;
  // reset it so each test starts from a known state.
  beforeEach(() => {
    useGlobalTimeRange().setActiveTimeRange(null)
  })

  test('an X-zoom propagates the new range to a sibling graph', async () => {
    const { zoomedGraph, siblingGraphRange } = twoGraphsOnOnePage()

    zoomedGraph.onZoom({ timeRange: { start: 1_200, end: 1_500, step: 60 } })
    await settlePropagation()

    expect(siblingGraphRange.value).toEqual({ start: 1_200, end: 1_500 })
  })

  test('a Y-zoom stays local and never reaches a sibling graph', async () => {
    const { zoomedGraph, siblingGraphRange } = twoGraphsOnOnePage()

    zoomedGraph.onZoom({ timeRange: BASELINE, valueRange: { min: 10, max: 20 } })
    await settlePropagation()

    expect(zoomedGraph.viewValueRange.value).toEqual({ min: 10, max: 20 })
    expect(siblingGraphRange.value).toEqual(INITIAL)
  })

  test('a Y-zoom leaves the global picker unpublished', () => {
    const { zoomedGraph } = twoGraphsOnOnePage()

    zoomedGraph.onZoom({ timeRange: BASELINE, valueRange: { min: 10, max: 20 } })

    expect(useGlobalTimeRange().activeTimeRange.value).toBeNull()
  })

  test('a pan propagates to a sibling graph the same way an X-zoom does', async () => {
    const { zoomedGraph, siblingGraphRange } = twoGraphsOnOnePage()

    zoomedGraph.onPan({ timeRange: { start: 1_100, end: 2_100, step: 60 } })
    await settlePropagation()

    expect(siblingGraphRange.value).toEqual({ start: 1_100, end: 2_100 })
  })
})
