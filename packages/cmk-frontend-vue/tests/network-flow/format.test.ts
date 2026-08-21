/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { expect, test } from 'vitest'

import { formatDelta, formatTimeOfDay } from '@/network-flow/format'

function atLocalTime(hour: number, minute: number, second: number): number {
  // Built from local parts, since the formatter renders in the site's zone.
  const date = new Date(2026, 6, 30, hour, minute, second)
  return Math.floor(date.getTime() / 1000)
}

test('renders a clock time as 24-hour HH:MM:SS', () => {
  expect(formatTimeOfDay(atLocalTime(9, 5, 3))).toBe('09:05:03')
})

test('renders an afternoon time in 24-hour form, never AM/PM', () => {
  const rendered = formatTimeOfDay(atLocalTime(22, 13, 20))

  expect(rendered).toBe('22:13:20')
  expect(rendered).not.toMatch(/[AP]M/)
})

test('renders midnight as 00, not 12', () => {
  expect(formatTimeOfDay(atLocalTime(0, 0, 0))).toBe('00:00:00')
})

test('carries no date, since a listing covers one range', () => {
  expect(formatTimeOfDay(atLocalTime(13, 45, 9))).toBe('13:45:09')
})

test('signs a change and calls growth out of nothing new', () => {
  expect(formatDelta(90, 60)).toBe('+50.0%')
  expect(formatDelta(60, 90)).toBe('-33.3%')
  expect(formatDelta(90, 0)).toBe('new')
  expect(formatDelta(0, 0)).toBe('–')
})
