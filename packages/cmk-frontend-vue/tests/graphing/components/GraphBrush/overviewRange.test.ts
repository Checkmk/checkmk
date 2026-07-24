/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import {
  overviewDomain,
  overviewMultiplier,
  overviewStep,
  overviewTimeRange,
  recenterOverviewDomain
} from '@/graphing/components/GraphBrush/overviewRange'

const HOUR = 3600
const DAY = 86_400

describe('overviewMultiplier', () => {
  test('spans up to 25h widen sevenfold', () => {
    expect(overviewMultiplier(4 * HOUR)).toBe(7)
    expect(overviewMultiplier(25 * HOUR)).toBe(7)
  })

  test('spans over 25h and up to 8d widen fivefold', () => {
    expect(overviewMultiplier(25 * HOUR + 1)).toBe(5)
    expect(overviewMultiplier(8 * DAY)).toBe(5)
  })

  test('spans over 8d widen threefold', () => {
    expect(overviewMultiplier(8 * DAY + 1)).toBe(3)
    expect(overviewMultiplier(365 * DAY)).toBe(3)
  })
})

describe('overviewDomain (center-then-clamp-at-now)', () => {
  const now = 2_000_000

  test('width is the committed span times the multiplier (24h → ×7)', () => {
    const committed = { start: now - DAY, end: now }

    const strip = overviewDomain(committed, now)

    expect(strip.end - strip.start).toBe(DAY * 7)
  })

  test('a committed range ending at now is end-anchored', () => {
    const committed = { start: now - DAY, end: now }

    const strip = overviewDomain(committed, now)

    expect(strip.end).toBe(now)
    expect(strip.start).toBe(now - DAY * 7)
  })

  test('a far-past committed range is centered on the window', () => {
    const farPastCommitted = { start: now - 11 * DAY, end: now - 10 * DAY }

    const strip = overviewDomain(farPastCommitted, now)

    const committedCenter = (farPastCommitted.start + farPastCommitted.end) / 2
    expect((strip.start + strip.end) / 2).toBe(committedCenter)
    expect(strip.end - strip.start).toBe(DAY * 7)
    expect(strip.end).toBeLessThan(now)
  })

  test('a near-now committed range lands right-of-center with its end clamped to now', () => {
    const nearNowCommitted = { start: now - 2 * DAY, end: now - DAY }

    const strip = overviewDomain(nearNowCommitted, now)

    expect(strip.end).toBe(now)
    expect(strip.end - strip.start).toBe(DAY * 7)
    expect(nearNowCommitted.end).toBeLessThan(strip.end)
  })

  test('an odd committed span still yields integer bounds (the fetch API rejects fractions)', () => {
    const strip = overviewDomain({ start: now - DAY - 1, end: now - DAY }, now)

    expect(Number.isInteger(strip.start)).toBe(true)
    expect(Number.isInteger(strip.end)).toBe(true)
    expect(strip.end - strip.start).toBe(7)
  })

  test('multiplier thresholds drive the width', () => {
    const at25h = overviewDomain({ start: now - 25 * HOUR, end: now }, now)
    const at8d = overviewDomain({ start: now - 8 * DAY, end: now }, now)
    const over8d = overviewDomain({ start: now - 9 * DAY, end: now }, now)

    expect(at25h.end - at25h.start).toBe(25 * HOUR * 7)
    expect(at8d.end - at8d.start).toBe(8 * DAY * 5)
    expect(over8d.end - over8d.start).toBe(9 * DAY * 3)
  })
})

describe('recenterOverviewDomain (10% edge hold/shift, fixed width)', () => {
  const farFutureNow = 1e12
  const domain = { start: 0, end: 1000 }

  test('a window inside the middle 80% leaves the domain unchanged', () => {
    const windowInMiddle = { start: 400, end: 600 }

    const result = recenterOverviewDomain(domain, windowInMiddle, farFutureNow)

    expect(result).toEqual(domain)
  })

  test('a window within 10% of the right edge shifts the domain, width preserved', () => {
    const windowNearRightEdge = { start: 850, end: 950 }

    const result = recenterOverviewDomain(domain, windowNearRightEdge, farFutureNow)

    expect(result.end - result.start).toBe(1000)
    expect((result.start + result.end) / 2).toBe(900)
  })

  test('a window within 10% of the left edge shifts the domain, width preserved', () => {
    const windowNearLeftEdge = { start: 50, end: 150 }

    const result = recenterOverviewDomain(domain, windowNearLeftEdge, farFutureNow)

    expect(result.end - result.start).toBe(1000)
    expect((result.start + result.end) / 2).toBe(100)
  })

  test('a window with an odd coordinate sum still shifts to integer bounds', () => {
    const windowWithOddSum = { start: 851, end: 950 }

    const result = recenterOverviewDomain(domain, windowWithOddSum, farFutureNow)

    expect(Number.isInteger(result.start)).toBe(true)
    expect(Number.isInteger(result.end)).toBe(true)
    expect(result.end - result.start).toBe(1000)
  })

  test('a shift that would pass now is clamped so the end sits at now', () => {
    const windowNearRightEdge = { start: 850, end: 950 }
    const nowJustPastDomain = 1200

    const result = recenterOverviewDomain(domain, windowNearRightEdge, nowJustPastDomain)

    expect(result.end).toBe(1200)
    expect(result.end - result.start).toBe(1000)
  })
})

describe('overviewStep', () => {
  test('is about one point per pixel', () => {
    const spanSeconds = 800 * 100
    const canvasWidth = 800

    const step = overviewStep(0, spanSeconds, canvasWidth)

    expect(step).toBe(100)
  })

  test('is floored at 60s for tiny spans', () => {
    const spanSeconds = 600
    const canvasWidth = 800

    const step = overviewStep(0, spanSeconds, canvasWidth)

    expect(step).toBe(60)
  })
})

describe('overviewTimeRange', () => {
  const now = 1_000_000

  test('matches overviewDomain and carries a coarse step', () => {
    const committed = { start: now - DAY, end: now, step: 60 }

    const timeRange = overviewTimeRange(committed, now, 800)

    const domain = overviewDomain(committed, now)
    expect(timeRange.start).toBe(domain.start)
    expect(timeRange.end).toBe(domain.end)
    expect(timeRange.step).toBe(overviewStep(domain.start, domain.end, 800))
  })
})
