/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDate } from '@internationalized/date'
import { render } from '@testing-library/vue'
import { describe, expect, test } from 'vitest'

import { formatDate, formatTime, timeZoneRegionLabel } from '@/components/date-time/dateTimeUtils'
import CmkTimeRangeDisplay from '@/components/date-time/private/display/CmkTimeRangeDisplay.vue'
import type { DateTimePartsDraft, HourCycle } from '@/components/date-time/types'

import { TZ_BERLIN, YMD, makeSettings } from '../../dateTimeTestFixtures'

const buildSettings = (hourCycle: HourCycle) => makeSettings({ hourCycle, dateFormat: YMD })

const EMPTY: DateTimePartsDraft = { date: null, time: null }

describe('CmkTimeRangeDisplay', () => {
  const renderDisplay = (
    from: DateTimePartsDraft,
    to: DateTimePartsDraft,
    hourCycle: HourCycle = 24
  ) =>
    render(CmkTimeRangeDisplay, {
      props: { from, to, settings: buildSettings(hourCycle) }
    })

  test('dateText null → em dash', () => {
    const { container } = renderDisplay(EMPTY, EMPTY)
    // Both date columns render the em dash for an empty date.
    const dashes = Array.from(container.querySelectorAll('span')).filter(
      (span) => span.textContent === '—'
    )
    expect(dashes.length).toBeGreaterThanOrEqual(2)
  })

  test('empty halves announce "not set" instead of the visible em dash', () => {
    // Both endpoints fully empty → all four halves (from/to × date/time) are "not set" to AT.
    const { getAllByLabelText } = renderDisplay(EMPTY, EMPTY)
    expect(getAllByLabelText('not set')).toHaveLength(4)
  })

  test('a set half is named by its value, not "not set"', () => {
    const { getAllByLabelText } = renderDisplay(
      { date: new CalendarDate(2026, 3, 9), time: null },
      EMPTY
    )
    // The set From date drops out, leaving three empty halves.
    expect(getAllByLabelText('not set')).toHaveLength(3)
  })

  test('the timezone reads with a "Timezone:" prefix and the region name', () => {
    const settings = makeSettings({ timeZone: TZ_BERLIN })
    const { getByText } = render(CmkTimeRangeDisplay, {
      props: { from: EMPTY, to: EMPTY, settings }
    })
    // Offset is DST-dependent (no fixed instant here), so assert the stable region prefix only.
    expect(
      getByText(new RegExp(`^Timezone: ${timeZoneRegionLabel(TZ_BERLIN)},`))
    ).toBeInTheDocument()
  })

  test('dateText value → formatDate(...)', () => {
    const settings = buildSettings(24)
    const date = new CalendarDate(2026, 3, 9)
    const { container } = renderDisplay({ date, time: null }, EMPTY, 24)
    expect(container.textContent).toContain(formatDate(date, settings.dateFormat))
  })

  test('timeText null → em dash', () => {
    const { container } = renderDisplay(EMPTY, EMPTY)
    expect(container.textContent).toContain('—')
  })

  test('timeText value → formatTime(...)', () => {
    const time = { hour: 8, minute: 45 }
    const { container } = renderDisplay({ date: null, time }, EMPTY, 24)
    expect(container.textContent).toContain(formatTime(time, 24))
  })

  test('timeWidthVariants 12h', () => {
    const { container } = renderDisplay(EMPTY, EMPTY, 12)
    const ghosts = Array.from(container.querySelectorAll('.cmk-ghost-width__ghost')).map(
      (ghost) => ghost.textContent
    )
    expect(ghosts).toEqual(['00:00 AM', '00:00 PM', '00:00 AM', '00:00 PM'])
  })

  test('timeWidthVariants 24h', () => {
    const { container } = renderDisplay(EMPTY, EMPTY, 24)
    expect(container.querySelectorAll('.cmk-ghost-width__ghost')).toHaveLength(0)
  })
})
