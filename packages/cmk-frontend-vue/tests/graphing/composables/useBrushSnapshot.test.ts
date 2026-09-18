/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'
import { effectScope, nextTick, ref } from 'vue'

import { type UseBrushSnapshot, useBrushSnapshot } from '@/graphing/composables/useBrushSnapshot'
import type { BrushSnapshot, TimeInterval } from '@/graphing/types'

const HOUR = 3_600
const DAY = 86_400
const NOW = 2_000_000_000

type Payload = string

function mount(requested = ref<TimeInterval>({ start: NOW - HOUR, end: NOW })): {
  brush: UseBrushSnapshot<Payload>
  requested: typeof requested
} {
  const scope = effectScope()
  const brush = scope.run(() =>
    useBrushSnapshot<Payload>({
      getNow: () => NOW,
      getRequestedTimeRange: () => requested.value
    })
  )!
  return { brush, requested }
}

function landOverview(brush: UseBrushSnapshot<Payload>, data: Payload): void {
  const requestedDomain = brush.requestedDomain.value
  brush.onOverviewFetched({ requestedDomain, drawnDomain: requestedDomain, data })
}

describe('useBrushSnapshot — what to fetch', () => {
  test('asks for a strip around the range it was seeded with', () => {
    const { brush } = mount()

    // Ends now because the range does, and no strip may reach into the future.
    expect(brush.requestedDomain.value.end).toBe(NOW)
    expect(brush.requestedDomain.value.start).toBeLessThan(NOW - HOUR)
  })

  test('is pending until something answers the strip it is asking for', () => {
    const { brush } = mount()
    expect(brush.isPending.value).toBe(true)

    landOverview(brush, 'overview')

    expect(brush.isPending.value).toBe(false)
    expect(brush.snapshot.value?.data).toBe('overview')
  })

  test('a changed span asks for a new strip', () => {
    const { brush } = mount()
    landOverview(brush, 'overview')
    const before = brush.requestedDomain.value

    brush.onRangeCommitted({ start: NOW - 8 * DAY, end: NOW }, 'changed_timerange_span')

    expect(brush.requestedDomain.value).not.toEqual(before)
    expect(brush.isPending.value).toBe(true)
  })
})

describe('useBrushSnapshot — the pair is only ever written together', () => {
  test('a range that does not fit the strip on screen leaves the snapshot untouched', async () => {
    // The jump this composable exists to prevent.
    const requested = ref<TimeInterval>({ start: NOW - HOUR, end: NOW })
    const { brush } = mount(requested)
    landOverview(brush, 'one hour')
    const before = brush.snapshot.value!

    requested.value = { start: NOW - 400 * DAY, end: NOW }
    await nextTick()

    expect(brush.snapshot.value).toEqual(before)
    expect(brush.isPending.value).toBe(true)
  })

  test('the window and the strip change in the same assignment when the data lands', async () => {
    const requested = ref<TimeInterval>({ start: NOW - HOUR, end: NOW })
    const { brush } = mount(requested)
    landOverview(brush, 'one hour')
    const stale = brush.snapshot.value!

    requested.value = { start: NOW - 400 * DAY, end: NOW }
    await nextTick()
    landOverview(brush, 'four hundred days')

    const fresh = brush.snapshot.value!
    expect(fresh.data).toBe('four hundred days')
    expect(fresh.window).toEqual(requested.value)
    expect(fresh.drawnDomain).not.toEqual(stale.drawnDomain)
    expect(fresh.window).not.toEqual(stale.window)
  })

  test('the window still fills the same share of a strip derived for it', () => {
    // What the bar's stability rests on: a strip is a multiple of the window it was derived for.
    const { brush } = mount()
    landOverview(brush, 'overview')
    const shareOf = ({ drawnDomain, window }: BrushSnapshot<Payload>): number =>
      (window.end - window.start) / (drawnDomain.end - drawnDomain.start)
    const before = shareOf(brush.snapshot.value!)

    brush.onRangeCommitted({ start: NOW - 25 * HOUR, end: NOW }, 'changed_timerange_span')
    landOverview(brush, 'twenty five hours')

    expect(shareOf(brush.snapshot.value!)).toBeCloseTo(before, 6)
  })
})

describe('useBrushSnapshot — a window that fits gets in ahead of its data', () => {
  test('a release inside the strip on screen moves the bar at once', () => {
    // Every brush interaction is clamped to the strip it is drawn in, so it always fits.
    const { brush } = mount()
    landOverview(brush, 'overview')
    const { drawnDomain } = brush.snapshot.value!
    const insideTheStrip = { start: drawnDomain.start + HOUR, end: drawnDomain.start + 2 * HOUR }

    brush.onRangeCommitted(insideTheStrip, 'translated_timerange')

    expect(brush.snapshot.value!.window).toEqual(insideTheStrip)
    expect(brush.snapshot.value!.data).toBe('overview')
  })

  test('a translation keeps the strip it was made in, and asks for nothing new', () => {
    // The surface fetches on the requested extent, so moving it would refetch a strip that
    // has not moved.
    const { brush } = mount()
    landOverview(brush, 'overview')
    const { drawnDomain } = brush.snapshot.value!
    const askedFor = brush.requestedDomain.value
    const nudge = { start: drawnDomain.start + 3 * HOUR, end: drawnDomain.start + 4 * HOUR }

    brush.onRangeCommitted(nudge, 'translated_timerange')

    expect(brush.snapshot.value!.drawnDomain).toEqual(drawnDomain)
    expect(brush.requestedDomain.value).toEqual(askedFor)
    expect(brush.isPending.value).toBe(false)
  })

  test('a translation off the end of the strip carries it along', () => {
    const { brush } = mount()
    landOverview(brush, 'overview')
    const askedFor = brush.requestedDomain.value
    const width = askedFor.end - askedFor.start
    const pastTheEdge = { start: askedFor.start - width, end: askedFor.start - width + HOUR }

    brush.onRangeCommitted(pastTheEdge, 'translated_timerange')

    expect(brush.requestedDomain.value).not.toEqual(askedFor)
    expect(brush.requestedDomain.value.end - brush.requestedDomain.value.start).toBe(width)
  })
})

describe('useBrushSnapshot — an extent that cannot be drawn in', () => {
  test('a strip collapsed by the grid its data sits on falls back to the one asked for', () => {
    // A strip snapped onto a step wider than itself; every mark would be placed by a
    // division by zero.
    const { brush } = mount()
    const requestedDomain = brush.requestedDomain.value
    const collapsed = { start: requestedDomain.start, end: requestedDomain.start }

    brush.onOverviewFetched({ requestedDomain, drawnDomain: collapsed, data: 'overview' })

    const { drawnDomain } = brush.snapshot.value!
    expect(drawnDomain.end).toBeGreaterThan(drawnDomain.start)
    expect(drawnDomain).toEqual(requestedDomain)
  })
})

describe('useBrushSnapshot — superseded answers', () => {
  test('an answer to a strip the brush has since left is dropped', async () => {
    const requested = ref<TimeInterval>({ start: NOW - HOUR, end: NOW })
    const { brush } = mount(requested)
    landOverview(brush, 'one hour')
    const inFlight = brush.requestedDomain.value

    requested.value = { start: NOW - 8 * DAY, end: NOW }
    await nextTick()
    requested.value = { start: NOW - 400 * DAY, end: NOW }
    await nextTick()
    brush.onOverviewFetched({ requestedDomain: inFlight, drawnDomain: inFlight, data: 'stale' })

    expect(brush.snapshot.value!.data).toBe('one hour')
    expect(brush.isPending.value).toBe(true)
  })

  test('a range committed while a fetch is out is not lost when that fetch lands', async () => {
    // Drag the brush during a preset switch: what lands must be drawn against the range the
    // user ended on, not the one they left.
    const requested = ref<TimeInterval>({ start: NOW - HOUR, end: NOW })
    const { brush } = mount(requested)
    landOverview(brush, 'one hour')

    requested.value = { start: NOW - 400 * DAY, end: NOW }
    await nextTick()
    const dragged = { start: NOW - 2 * HOUR, end: NOW - HOUR }
    brush.onRangeCommitted(dragged, 'changed_timerange_span')
    landOverview(brush, 'after the drag')

    expect(brush.snapshot.value!.window).toEqual(dragged)
    expect(brush.snapshot.value!.data).toBe('after the drag')
  })
})

describe('useBrushSnapshot — echoes of its own commits', () => {
  test('a committed range published back does not re-derive the strip', async () => {
    // A panel's commit is published to the page's shared range and arrives back through the
    // same watch an external change does.
    const requested = ref<TimeInterval>({ start: NOW - HOUR, end: NOW })
    const { brush } = mount(requested)
    landOverview(brush, 'overview')
    const { drawnDomain } = brush.snapshot.value!
    const nudge = { start: drawnDomain.start + 3 * HOUR, end: drawnDomain.start + 4 * HOUR }

    brush.onRangeCommitted(nudge, 'translated_timerange')
    requested.value = nudge
    await nextTick()

    expect(brush.snapshot.value!.drawnDomain).toEqual(drawnDomain)
    expect(brush.isPending.value).toBe(false)
  })
})
