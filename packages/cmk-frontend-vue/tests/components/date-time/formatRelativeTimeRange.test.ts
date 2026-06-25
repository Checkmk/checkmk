/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { untranslated } from '@/lib/i18n'

import { formatRelativeTimeRange } from '@/components/date-time/formatRelativeTimeRange'
import type { ResolvedDateTimeSettings } from '@/components/date-time/types'

const settings: Pick<ResolvedDateTimeSettings, 'timeZone' | 'hourCycle' | 'formatLongDate'> = {
  timeZone: 'UTC',
  hourCycle: 24,
  formatLongDate: (date) =>
    untranslated(
      `${date.year}-${String(date.month).padStart(2, '0')}-${String(date.day).padStart(2, '0')}`
    )
}

test('same-day range shows times only', () => {
  expect(formatRelativeTimeRange(new Date('2026-06-26T18:30:00Z'), 4 * 3600, settings)).toBe(
    '14:30 – 18:30'
  )
})

test('range spanning days includes the date', () => {
  expect(formatRelativeTimeRange(new Date('2026-06-26T14:30:00Z'), 7 * 24 * 3600, settings)).toBe(
    '2026-06-19, 14:30 – 2026-06-26, 14:30'
  )
})

test('12-hour cycle formats with meridiem', () => {
  expect(
    formatRelativeTimeRange(new Date('2026-06-26T18:30:00Z'), 4 * 3600, {
      ...settings,
      hourCycle: 12
    })
  ).toBe('02:30 PM – 06:30 PM')
})
