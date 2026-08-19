/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'
import { effectScope, nextTick, ref } from 'vue'

import { useBrushCoordination } from '@/graphing/composables/useBrushCoordination'

const DAY = 86_400
const NOW = 2_000_000

function makeCoordination(requested = ref({ start: NOW - DAY, end: NOW })) {
  return {
    ...useBrushCoordination(
      () => NOW,
      () => requested.value
    ),
    requested
  }
}

describe('useBrushCoordination — construction', () => {
  test('the strip is seeded end-anchored from a now-anchored initial range', () => {
    const coordination = makeCoordination()

    expect(coordination.brushDomain.value).toEqual({ start: NOW - 7 * DAY, end: NOW })
  })
})

describe('useBrushCoordination — channels are independent', () => {
  test('setGraphRange moves only the graph range', () => {
    const coordination = makeCoordination()
    const windowBefore = { ...coordination.brushWindow.value }
    const domainBefore = { ...coordination.brushDomain.value }

    coordination.setGraphRange({ start: 1, end: 2 })

    expect(coordination.graphRange.value).toEqual({ start: 1, end: 2 })
    expect(coordination.brushWindow.value).toEqual(windowBefore)
    expect(coordination.brushDomain.value).toEqual(domainBefore)
  })

  test('setBrushWindow moves only the brush window', () => {
    const coordination = makeCoordination()
    const graphBefore = { ...coordination.graphRange.value }
    const domainBefore = { ...coordination.brushDomain.value }

    coordination.setBrushWindow({ start: 5, end: 6 })

    expect(coordination.brushWindow.value).toEqual({ start: 5, end: 6 })
    expect(coordination.graphRange.value).toEqual(graphBefore)
    expect(coordination.brushDomain.value).toEqual(domainBefore)
  })
})

describe('useBrushCoordination — intent handlers', () => {
  test('onGraphView never changes the committed graph range', () => {
    const coordination = makeCoordination()
    const graphBefore = { ...coordination.graphRange.value }
    const view = { start: NOW - 2 * DAY, end: NOW - DAY, step: 60 }

    coordination.onGraphView(view)

    expect(coordination.graphRange.value).toEqual(graphBefore)
    expect(coordination.brushWindow.value).toEqual({ start: view.start, end: view.end })
  })

  test('onExternalRange reseeds the strip and moves all channels', () => {
    const coordination = makeCoordination()
    const farPastRange = { start: NOW - 11 * DAY, end: NOW - 10 * DAY }

    coordination.onExternalRange(farPastRange)

    expect(coordination.graphRange.value).toEqual(farPastRange)
    expect(coordination.brushWindow.value).toEqual(farPastRange)
    expect(coordination.brushDomain.value.end).toBeLessThan(NOW)
    expect((coordination.brushDomain.value.start + coordination.brushDomain.value.end) / 2).toBe(
      (farPastRange.start + farPastRange.end) / 2
    )
  })

  test('onBrushChange updates graph + window but holds the strip away from the edge', () => {
    const coordination = makeCoordination()
    coordination.onExternalRange({ start: NOW - 11 * DAY, end: NOW - 10 * DAY })
    const domainBefore = { ...coordination.brushDomain.value }
    const windowInMiddle = { start: NOW - 11 * DAY, end: NOW - 10 * DAY }

    coordination.onBrushChange(windowInMiddle, 'translated_timerange')

    expect(coordination.graphRange.value).toEqual(windowInMiddle)
    expect(coordination.brushWindow.value).toEqual(windowInMiddle)
    expect(coordination.brushDomain.value).toEqual(domainBefore)
  })

  test('a translating commit shifts the strip when the window reaches the 10% edge', () => {
    const coordination = makeCoordination()
    coordination.onExternalRange({ start: NOW - 11 * DAY, end: NOW - 10 * DAY })
    const before = { ...coordination.brushDomain.value }
    const windowNearRightEdge = { start: NOW - 8.5 * DAY, end: NOW - 7.5 * DAY }

    coordination.onBrushChange(windowNearRightEdge, 'translated_timerange')

    expect(coordination.brushDomain.value.end).not.toBe(before.end)
    expect(coordination.brushDomain.value.end - coordination.brushDomain.value.start).toBe(
      before.end - before.start
    )
  })

  test('a span-changing commit reseeds the strip around the new range', () => {
    const coordination = makeCoordination()
    coordination.onExternalRange({ start: NOW - 11 * DAY, end: NOW - 10 * DAY })
    const widenedWindow = { start: NOW - 12 * DAY, end: NOW - 10 * DAY }

    coordination.onBrushChange(widenedWindow, 'changed_timerange_span')

    // 2d span → 5× multiplier → 10d strip centered on the widened window.
    expect(coordination.brushDomain.value).toEqual({ start: NOW - 16 * DAY, end: NOW - 6 * DAY })
  })
})

describe('useBrushCoordination — the requested range it watches', () => {
  test('a range it did not commit reseeds the strip around it', async () => {
    const scope = effectScope()
    const coordination = scope.run(() => makeCoordination())!

    coordination.requested.value = { start: NOW - 5.5 * DAY, end: NOW - 4.5 * DAY }
    await nextTick()

    expect(coordination.graphRange.value).toEqual({ start: NOW - 5.5 * DAY, end: NOW - 4.5 * DAY })
    // Centred on the new window rather than slid, i.e. it took the outside path.
    expect(coordination.brushDomain.value).toEqual({
      start: NOW - 8.5 * DAY,
      end: NOW - 1.5 * DAY
    })
    scope.stop()
  })

  test('a range it committed itself leaves the strip alone', async () => {
    const scope = effectScope()
    const coordination = scope.run(() => makeCoordination())!
    const moved = { start: NOW - DAY + 3600, end: NOW + 3600 }

    coordination.onBrushChange(moved, 'translated_timerange')
    const domainAfterCommit = { ...coordination.brushDomain.value }
    coordination.requested.value = moved
    await nextTick()

    expect(coordination.brushDomain.value).toEqual(domainAfterCommit)
    scope.stop()
  })
})
