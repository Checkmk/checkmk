/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { type Ref, nextTick, ref } from 'vue'

import type { TimeRange, ValueRange } from '@/graphing/components/TimeSeriesGraph'
import { useGlobalPin } from '@/graphing/composables/useGlobalPin'
import { useGraphInteraction } from '@/graphing/composables/useGraphInteraction'
import type { RequestedTimeRange } from '@/graphing/types'

vi.mock('@/graphing/composables/useGlobalPin', async () => {
  const { computed, ref: createRef } = await import('vue')
  const pinTimeState = createRef<number | null>(null)
  const globalPin = {
    pinTime: computed(() => pinTimeState.value),
    ensurePinLoaded: vi.fn(),
    setPin: vi.fn((time: number) => {
      pinTimeState.value = time
    }),
    clearPin: vi.fn(() => {
      pinTimeState.value = null
    })
  }
  return { useGlobalPin: () => globalPin }
})

const BASELINE: TimeRange = { start: 1000, end: 2000, step: 60 }
const ZOOMED: TimeRange = { start: 1200, end: 1500, step: 60 }
const SHIFTED: TimeRange = { start: 1100, end: 2100, step: 60 }
const PEAK: ValueRange = { min: 10, max: 20 }

const bounds = ({ start, end }: TimeRange): RequestedTimeRange => ({ start, end })

describe('useGraphInteraction', () => {
  beforeEach(() => {
    const globalPin = useGlobalPin()
    globalPin.clearPin()
    vi.mocked(globalPin.ensurePinLoaded).mockClear()
    vi.mocked(globalPin.setPin).mockClear()
    vi.mocked(globalPin.clearPin).mockClear()
  })

  test('starts on the baseline with time-zoom mode and no pin', () => {
    const graph = useGraphInteraction(() => BASELINE)

    expect(graph.viewTimeRange.value).toEqual(BASELINE)
    expect(graph.viewValueRange.value).toBeNull()
    expect(graph.inspectionActive.value).toBe(false)
    expect(graph.zoomMode.value).toBe('time')
    expect(graph.pinTime.value).toBeNull()
  })

  test('a zoom intent overlays the view and activates inspection', () => {
    const graph = useGraphInteraction(() => BASELINE)

    graph.onZoom({ timeRange: ZOOMED })

    expect(graph.viewTimeRange.value).toEqual(ZOOMED)
    expect(graph.inspectionActive.value).toBe(true)
  })

  test('a pan intent shifts the view', () => {
    const graph = useGraphInteraction(() => BASELINE)
    const shifted: TimeRange = { start: 1100, end: 2100, step: 60 }

    graph.onPan({ timeRange: shifted })

    expect(graph.viewTimeRange.value).toEqual(shifted)
    expect(graph.inspectionActive.value).toBe(true)
  })

  test('a reset intent restores the baseline', () => {
    const graph = useGraphInteraction(() => BASELINE)
    graph.onZoom({ timeRange: ZOOMED })

    graph.onReset()

    expect(graph.viewTimeRange.value).toEqual(BASELINE)
    expect(graph.inspectionActive.value).toBe(false)
  })

  test('a changed baseline updates the view but does not clear the reset target', async () => {
    const baseline = ref<TimeRange>(BASELINE)
    const graph = useGraphInteraction(() => baseline.value)
    graph.onZoom({ timeRange: ZOOMED })
    const committed: TimeRange = { start: 5000, end: 6000, step: 60 }

    baseline.value = committed
    await nextTick()

    // The local inspection overlay clears (rangeCommit) so the fresh baseline shows through...
    expect(graph.viewTimeRange.value).toEqual(committed)
    // ...but inspectionActive stays true: a baseline change alone never clears the reset
    // target (only onReset() or, when wired, an unrelated requestedTimeRange change does).
    expect(graph.inspectionActive.value).toBe(true)
  })

  test('a baseline arriving after an initial undefined becomes the view', async () => {
    const baseline = ref<TimeRange | undefined>(undefined)
    const graph = useGraphInteraction(() => baseline.value)

    baseline.value = BASELINE
    await nextTick()

    expect(graph.viewTimeRange.value).toEqual(BASELINE)
  })

  test('creating a pin delegates to the global pin', () => {
    const graph = useGraphInteraction(() => BASELINE)

    graph.onPinCreate({ time: 4242 })

    expect(useGlobalPin().setPin).toHaveBeenCalledWith(4242)
    expect(graph.pinTime.value).toBe(4242)
  })

  test('clearing a pin delegates to the global pin', () => {
    const graph = useGraphInteraction(() => BASELINE)
    graph.onPinCreate({ time: 4242 })

    graph.clearPin()

    expect(useGlobalPin().clearPin).toHaveBeenCalled()
    expect(graph.pinTime.value).toBeNull()
  })

  test('does not request the persisted pin when the pin is not shown', async () => {
    useGraphInteraction(() => BASELINE)

    await nextTick()

    expect(useGlobalPin().ensurePinLoaded).not.toHaveBeenCalled()
  })

  test('requests the persisted pin when the pin is shown', () => {
    useGraphInteraction(
      () => BASELINE,
      () => true
    )

    expect(useGlobalPin().ensurePinLoaded).toHaveBeenCalled()
  })

  test('requests the persisted pin once the pin becomes shown', async () => {
    const showPin = ref(false)
    useGraphInteraction(
      () => BASELINE,
      () => showPin.value
    )

    showPin.value = true
    await nextTick()

    expect(useGlobalPin().ensurePinLoaded).toHaveBeenCalled()
  })
})

test('a time-zoom commits the new time range', () => {
  const onTimeRangeCommit = vi.fn()
  const graph = useGraphInteraction(() => BASELINE, undefined, undefined, onTimeRangeCommit)

  graph.onZoom({ timeRange: ZOOMED })

  expect(onTimeRangeCommit).toHaveBeenCalledExactlyOnceWith(
    bounds(ZOOMED),
    'changed_timerange_span'
  )
})

test('a fractional zoom payload is rounded before it is committed', () => {
  const onTimeRangeCommit = vi.fn()
  const graph = useGraphInteraction(() => BASELINE, undefined, undefined, onTimeRangeCommit)

  graph.onZoom({ timeRange: { start: 1200.6, end: 1499.4, step: 60 } })

  expect(onTimeRangeCommit).toHaveBeenCalledExactlyOnceWith(
    { start: 1201, end: 1499 },
    'changed_timerange_span'
  )
})

test('the reset control survives the baseline settling at the rounded (not raw) committed range', async () => {
  const baseline = ref<TimeRange>(BASELINE)
  const onTimeRangeCommit = vi.fn()
  const graph = useGraphInteraction(() => baseline.value, undefined, undefined, onTimeRangeCommit)

  graph.onZoom({ timeRange: { start: 1200.6, end: 1499.4, step: 60 } })

  // Without a getRequestedTimeRange source, the session is never cleared by a baseline
  // change alone (only an explicit reset clears it) — this just confirms that still holds
  // once the baseline settles at the rounded value the zoom actually committed.
  baseline.value = { start: 1201, end: 1499, step: 60 }
  await nextTick()

  expect(graph.inspectionActive.value).toBe(true)
})

test('a value-zoom does not commit a time range', () => {
  const onTimeRangeCommit = vi.fn()
  const graph = useGraphInteraction(() => BASELINE, undefined, undefined, onTimeRangeCommit)

  graph.onZoom({ timeRange: BASELINE, valueRange: { min: 0, max: 10 } })

  expect(onTimeRangeCommit).not.toHaveBeenCalled()
})

test('a pan commits the new time range', () => {
  const onTimeRangeCommit = vi.fn()
  const graph = useGraphInteraction(() => BASELINE, undefined, undefined, onTimeRangeCommit)
  const shifted: TimeRange = { start: 1100, end: 2100, step: 60 }

  graph.onPan({ timeRange: shifted })

  expect(onTimeRangeCommit).toHaveBeenCalledExactlyOnceWith(bounds(shifted), 'translated_timerange')
})

test('a reset commits the baseline time range', () => {
  const onTimeRangeCommit = vi.fn()
  const graph = useGraphInteraction(() => BASELINE, undefined, undefined, onTimeRangeCommit)
  graph.onZoom({ timeRange: ZOOMED })
  onTimeRangeCommit.mockClear()

  graph.onReset()

  expect(onTimeRangeCommit).toHaveBeenCalledExactlyOnceWith(
    bounds(BASELINE),
    'changed_timerange_span'
  )
})

test('a reset commits the range the page requested, not the snapped one the backend served', () => {
  const requested: RequestedTimeRange = { start: 1000, end: 2000 }
  const served: TimeRange = { start: 960, end: 2040, step: 60 }
  const onTimeRangeCommit = vi.fn()
  const graph = useGraphInteraction(
    () => served,
    undefined,
    () => requested,
    onTimeRangeCommit
  )
  graph.onZoom({ timeRange: ZOOMED })
  onTimeRangeCommit.mockClear()

  graph.onReset()

  expect(onTimeRangeCommit).toHaveBeenCalledExactlyOnceWith(
    { start: 1000, end: 2000 },
    'changed_timerange_span'
  )
})

test('a reset does not commit when there is no baseline yet', () => {
  const onTimeRangeCommit = vi.fn()
  const graph = useGraphInteraction(() => undefined, undefined, undefined, onTimeRangeCommit)

  graph.onReset()

  expect(onTimeRangeCommit).not.toHaveBeenCalled()
})

test('a reset does not commit after only a value-zoom, since nothing was ever committed', () => {
  const onTimeRangeCommit = vi.fn()
  const graph = useGraphInteraction(() => BASELINE, undefined, undefined, onTimeRangeCommit)
  graph.onZoom({ timeRange: BASELINE, valueRange: { min: 0, max: 10 } })

  graph.onReset()

  expect(onTimeRangeCommit).not.toHaveBeenCalled()
})

test('inspection (and thus the reset control) stays active after the baseline catches up to a committed zoom, and a reset then commits the pre-zoom range', async () => {
  const baseline = ref<TimeRange>(BASELINE)
  const onTimeRangeCommit = vi.fn()
  const graph = useGraphInteraction(() => baseline.value, undefined, undefined, onTimeRangeCommit)

  graph.onZoom({ timeRange: ZOOMED })
  onTimeRangeCommit.mockClear()

  // Simulates the refetch that the zoom's own commit triggered actually completing:
  // the baseline itself becomes the zoomed range, which would otherwise clear the
  // inspection overlay and hide the reset control right away.
  baseline.value = ZOOMED
  await nextTick()
  expect(graph.inspectionActive.value).toBe(true)

  graph.onReset()

  expect(onTimeRangeCommit).toHaveBeenCalledExactlyOnceWith(
    bounds(BASELINE),
    'changed_timerange_span'
  )
  expect(graph.inspectionActive.value).toBe(false)
})

test('abandoning the inspection ends it without publishing a range', () => {
  const onTimeRangeCommit = vi.fn()
  const graph = useGraphInteraction(() => BASELINE, undefined, undefined, onTimeRangeCommit)
  graph.onZoom({ timeRange: ZOOMED })
  onTimeRangeCommit.mockClear()

  graph.abandonInspection()

  expect(onTimeRangeCommit).not.toHaveBeenCalled()
  expect(graph.inspectionActive.value).toBe(false)
})

test('a requested time range matching our own commit (inner) keeps the reset target', async () => {
  const baseline = ref<TimeRange>(BASELINE)
  const requestedTimeRange = ref<RequestedTimeRange>({
    start: BASELINE.start,
    end: BASELINE.end
  })
  const onTimeRangeCommit = vi.fn()
  const graph = useGraphInteraction(
    () => baseline.value,
    undefined,
    () => requestedTimeRange.value,
    onTimeRangeCommit
  )

  graph.onZoom({ timeRange: ZOOMED })
  // Let the zoom's own commit settle first, clearing the local inspection overlay — what's
  // left active afterward must come purely from the reset target (zoomSession), not the
  // transient overlay, otherwise this would pass even if zoomSession were wrongly cleared.
  baseline.value = ZOOMED
  await nextTick()
  // Echoes straight back, exactly as GraphGroup would when it applies our own emitted
  // update:requestedTimeRange — no backend round trip involved, so no rounding drift.
  requestedTimeRange.value = { start: ZOOMED.start, end: ZOOMED.end }
  await nextTick()

  expect(graph.inspectionActive.value).toBe(true)
})

describe('the brush commits like the canvas gestures do', () => {
  test.each(['translated_timerange', 'changed_timerange_span'] as const)(
    'a brush window is committed with the %s kind the brush reported',
    (kind) => {
      const onTimeRangeCommit = vi.fn()
      const graph = useGraphInteraction(() => BASELINE, undefined, undefined, onTimeRangeCommit)

      graph.onBrush({ start: 1100, end: 2100 }, kind)

      expect(onTimeRangeCommit).toHaveBeenCalledExactlyOnceWith(bounds(SHIFTED), kind)
    }
  )

  test('the echo of a brush commit is not mistaken for an outside change', async () => {
    const baseline = ref<TimeRange>(BASELINE)
    const requestedTimeRange = ref<RequestedTimeRange>({
      start: BASELINE.start,
      end: BASELINE.end
    })
    const graph = useGraphInteraction(
      () => baseline.value,
      undefined,
      () => requestedTimeRange.value,
      (timeRange) => {
        requestedTimeRange.value = { start: timeRange.start, end: timeRange.end }
      }
    )

    graph.onBrush({ start: SHIFTED.start, end: SHIFTED.end }, 'translated_timerange')
    baseline.value = SHIFTED
    await nextTick()

    expect(graph.inspectionActive.value).toBe(true)
  })
})

describe('a peak zoom outlives every change of the requested time range', () => {
  function peakZoomedGraph() {
    const baseline = ref<TimeRange>(BASELINE)
    const requestedTimeRange = ref<RequestedTimeRange>({
      start: BASELINE.start,
      end: BASELINE.end
    })
    function request(range: RequestedTimeRange): void {
      requestedTimeRange.value = range
    }
    const graph = useGraphInteraction(
      () => baseline.value,
      undefined,
      () => requestedTimeRange.value,
      (timeRange) => {
        request({ start: timeRange.start, end: timeRange.end })
      }
    )
    graph.onZoom({ timeRange: BASELINE, valueRange: PEAK })
    return { graph, baseline, request }
  }

  async function refetchServes(baseline: Ref<TimeRange>, served: TimeRange): Promise<void> {
    baseline.value = served
    await nextTick()
  }

  test('a pan keeps it', async () => {
    const { graph, baseline } = peakZoomedGraph()

    graph.onPan({ timeRange: SHIFTED })
    await refetchServes(baseline, SHIFTED)

    expect(graph.viewTimeRange.value).toEqual(SHIFTED)
    expect(graph.viewValueRange.value).toEqual(PEAK)
  })

  test('a time zoom keeps it', async () => {
    const { graph, baseline } = peakZoomedGraph()

    graph.onZoom({ timeRange: ZOOMED })
    await refetchServes(baseline, ZOOMED)

    expect(graph.viewTimeRange.value).toEqual(ZOOMED)
    expect(graph.viewValueRange.value).toEqual(PEAK)
  })

  test('a brush move keeps it', async () => {
    const { graph, baseline } = peakZoomedGraph()

    graph.onBrush({ start: SHIFTED.start, end: SHIFTED.end }, 'translated_timerange')
    await refetchServes(baseline, SHIFTED)

    expect(graph.viewTimeRange.value).toEqual(SHIFTED)
    expect(graph.viewValueRange.value).toEqual(PEAK)
  })

  test('an outside range change keeps it, since only the host can judge that one', async () => {
    const { graph, baseline, request } = peakZoomedGraph()

    request({ start: 5000, end: 6000 })
    await refetchServes(baseline, { start: 5000, end: 6000, step: 60 })

    expect(graph.viewValueRange.value).toEqual(PEAK)
  })

  test('a refetch re-serving the same window at another step keeps it', async () => {
    const { graph, baseline } = peakZoomedGraph()

    await refetchServes(baseline, { ...BASELINE, step: 120 })

    expect(graph.viewValueRange.value).toEqual(PEAK)
  })

  test('a requested range republished unchanged keeps it', async () => {
    const { graph, request } = peakZoomedGraph()

    request({ start: BASELINE.start, end: BASELINE.end })
    await nextTick()

    expect(graph.viewValueRange.value).toEqual(PEAK)
  })

  test('the host abandoning the inspection ends it', () => {
    const { graph } = peakZoomedGraph()

    graph.abandonInspection()

    expect(graph.viewValueRange.value).toBeNull()
    expect(graph.inspectionActive.value).toBe(false)
  })

  test('a reset ends it', () => {
    const { graph } = peakZoomedGraph()

    graph.onReset()

    expect(graph.viewValueRange.value).toBeNull()
    expect(graph.inspectionActive.value).toBe(false)
  })

  test('it keeps the reset control reachable once the panned range has settled', async () => {
    const { graph, baseline } = peakZoomedGraph()

    graph.onPan({ timeRange: SHIFTED })
    await refetchServes(baseline, SHIFTED)

    expect(graph.inspectionActive.value).toBe(true)
  })
})

test('an unrelated requested time range (e.g. the global picker) drops the reset target', async () => {
  const baseline = ref<TimeRange>(BASELINE)
  const requestedTimeRange = ref<RequestedTimeRange>({
    start: BASELINE.start,
    end: BASELINE.end
  })
  const onTimeRangeCommit = vi.fn()
  const graph = useGraphInteraction(
    () => baseline.value,
    undefined,
    () => requestedTimeRange.value,
    onTimeRangeCommit
  )

  graph.onZoom({ timeRange: ZOOMED })
  // Let the zoom's own commit settle first, clearing the local inspection overlay — same
  // reasoning as above, isolating what's being tested to zoomSession's own clearing logic.
  baseline.value = ZOOMED
  await nextTick()
  expect(graph.inspectionActive.value).toBe(true)

  requestedTimeRange.value = { start: 5000, end: 6000 }
  await nextTick()

  expect(graph.inspectionActive.value).toBe(false)
})
