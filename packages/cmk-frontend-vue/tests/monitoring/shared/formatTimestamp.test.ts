/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { expect, test } from 'vitest'

import { formatTimestamp } from '@/monitoring/shared/formatTimestamp'

// Built from local components and round-tripped through toISOString(), so the
// expectation holds regardless of the machine's timezone.
function isoAt(
  year: number,
  month: number,
  day: number,
  hours: number,
  minutes: number,
  seconds: number
): string {
  return new Date(year, month, day, hours, minutes, seconds).toISOString()
}

test('formats a timestamp as YYYY-MM-DD HH:MM:SS in the local timezone', () => {
  expect(formatTimestamp(isoAt(2026, 0, 5, 9, 3, 7))).toBe('2026-01-05 09:03:07')
})

test('pads single-digit date and time components', () => {
  expect(formatTimestamp(isoAt(2026, 8, 1, 0, 0, 5))).toBe('2026-09-01 00:00:05')
})
