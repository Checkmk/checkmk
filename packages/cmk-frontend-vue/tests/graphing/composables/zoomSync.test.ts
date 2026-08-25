/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  CalendarDateTime,
  type ZonedDateTime,
  getLocalTimeZone,
  toZoned
} from '@internationalized/date'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { nextTick, ref, watch } from 'vue'

import { useGlobalTimeRange } from '@/graphing/GlobalTimePicker/globalTimeState'
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
const PEAK = { min: 10, max: 20 }

const pickedRange = (fromHour: number, toHour: number): DateTimeRange => ({
  from: toZoned(new CalendarDateTime(2026, 3, 1, fromHour, 0), getLocalTimeZone(), 'compatible'),
  to: toZoned(new CalendarDateTime(2026, 3, 1, toHour, 0), getLocalTimeZone(), 'compatible')
})
const epochSeconds = (value: ZonedDateTime): number => Math.floor(value.toDate().getTime() / 1000)

// A commit travels graph -> requested range -> global picker -> sibling graph.
async function settlePropagation(): Promise<void> {
  await nextTick()
  await nextTick()
  await nextTick()
}

function twoGraphsOnOnePage() {
  const zoomed = useRequestedTimeRange(INITIAL)
  const sibling = useRequestedTimeRange(INITIAL)

  const zoomedGraph = useGraphInteraction(
    () => BASELINE,
    () => false,
    () => zoomed.requestedTimeRange.value,
    zoomed.setRequestedTimeRange
  )

  const siblingBaseline = ref<TimeRange>(BASELINE)
  watch(sibling.requestedTimeRange, (range) => {
    siblingBaseline.value = { ...range, step: BASELINE.step }
  })
  const siblingGraph = useGraphInteraction(
    () => siblingBaseline.value,
    () => false,
    () => sibling.requestedTimeRange.value,
    sibling.setRequestedTimeRange
  )

  return {
    zoomedGraph,
    siblingGraph,
    zoomedRange: zoomed.requestedTimeRange,
    siblingRange: sibling.requestedTimeRange,
    siblingTimePickerRequests: sibling.timePickerRequests
  }
}

describe('zoom sync across the graphs on a page', () => {
  // The global picker store is a module-level singleton shared across the whole bundle;
  // reset it so each test starts from a known state.
  beforeEach(() => {
    useGlobalTimeRange().setActiveTimeRange(null, 'time_picker')
  })

  test('an X-zoom propagates the new range to a sibling graph', async () => {
    const { zoomedGraph, siblingRange } = twoGraphsOnOnePage()

    zoomedGraph.onZoom({ timeRange: { start: 1_200, end: 1_500, step: 60 } })
    await settlePropagation()

    expect(siblingRange.value).toEqual({ start: 1_200, end: 1_500 })
  })

  test('a Y-zoom stays local and never reaches a sibling graph', async () => {
    const { zoomedGraph, siblingRange } = twoGraphsOnOnePage()

    zoomedGraph.onZoom({ timeRange: BASELINE, valueRange: PEAK })
    await settlePropagation()

    expect(zoomedGraph.viewValueRange.value).toEqual(PEAK)
    expect(siblingRange.value).toEqual(INITIAL)
  })

  test('a Y-zoom leaves the global picker unpublished', () => {
    const { zoomedGraph } = twoGraphsOnOnePage()

    zoomedGraph.onZoom({ timeRange: BASELINE, valueRange: PEAK })

    expect(useGlobalTimeRange().activeTimeRange.value).toBeNull()
  })

  test('a pan propagates to a sibling graph the same way an X-zoom does', async () => {
    const { zoomedGraph, siblingRange } = twoGraphsOnOnePage()

    zoomedGraph.onPan({ timeRange: { start: 1_100, end: 2_100, step: 60 } })
    await settlePropagation()

    expect(siblingRange.value).toEqual({ start: 1_100, end: 2_100 })
  })

  test("a peer's commit reaches the sibling without counting as a new window", async () => {
    const { zoomedGraph, siblingTimePickerRequests } = twoGraphsOnOnePage()

    zoomedGraph.onPan({ timeRange: { start: 1_100, end: 2_100, step: 60 } })
    await settlePropagation()

    expect(siblingTimePickerRequests.value).toBe(0)
  })

  test("a peer's pan leaves a sibling's own peak zoom standing", async () => {
    const { zoomedGraph, siblingGraph } = twoGraphsOnOnePage()
    siblingGraph.onZoom({ timeRange: BASELINE, valueRange: PEAK })

    zoomedGraph.onPan({ timeRange: { start: 1_100, end: 2_100, step: 60 } })
    await settlePropagation()

    expect(siblingGraph.viewTimeRange.value).toEqual({ start: 1_100, end: 2_100, step: 60 })
    expect(siblingGraph.viewValueRange.value).toEqual(PEAK)
  })

  test("a peer's X-zoom leaves a sibling's own peak zoom standing", async () => {
    const { zoomedGraph, siblingGraph } = twoGraphsOnOnePage()
    siblingGraph.onZoom({ timeRange: BASELINE, valueRange: PEAK })

    zoomedGraph.onZoom({ timeRange: { start: 1_200, end: 1_500, step: 60 } })
    await settlePropagation()

    expect(siblingGraph.viewValueRange.value).toEqual(PEAK)
  })

  test('the user picking a range reaches a graph counted as a new window', async () => {
    const { siblingRange, siblingTimePickerRequests } = twoGraphsOnOnePage()
    const picked = pickedRange(9, 10)

    useGlobalTimeRange().setActiveTimeRange(picked, 'time_picker')
    await settlePropagation()

    expect(siblingRange.value).toEqual({
      start: epochSeconds(picked.from as ZonedDateTime),
      end: epochSeconds(picked.to as ZonedDateTime)
    })
    expect(siblingTimePickerRequests.value).toBe(1)
  })
})
