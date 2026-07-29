/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDateTime, type ZonedDateTime, toZoned } from '@internationalized/date'
import { fireEvent, render, screen, within } from '@testing-library/vue'
import type { CustomGraphTimeRange } from 'cmk-shared-typing/typescript/global_time_picker'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { describe, expect, test } from 'vitest'

import GlobalTimePicker from '@/graphing/GlobalTimePicker/GlobalTimePicker.vue'
import { rollingRange } from '@/graphing/GlobalTimePicker/private/timeRange'

const TZ = 'Europe/Berlin'

// A range of exactly `totalSeconds`, anchored at a fixed instant so durations are deterministic.
const rangeOfSeconds = (totalSeconds: number): DateTimeRange => {
  const to: ZonedDateTime = toZoned(new CalendarDateTime(2026, 3, 10, 12, 0), TZ, 'compatible')
  return { from: to.subtract({ seconds: totalSeconds }), to }
}

const CUSTOM_RANGES: CustomGraphTimeRange[] = [
  { title: 'Last 4 hours', total_seconds: 4 * 3600 },
  { title: 'Last 25 hours', total_seconds: 25 * 3600 }
]

function renderPicker(
  modelValue: DateTimeRange,
  firstDayOfWeek: 'saturday' | 'sunday' | 'monday' | null = null
) {
  const updates: DateTimeRange[] = []
  const view = render(GlobalTimePicker, {
    props: {
      customTimeRanges: CUSTOM_RANGES,
      serverTimeZone: 'America/Los_Angeles',
      firstDayOfWeek,
      modelValue,
      'onUpdate:modelValue': (value: DateTimeRange) => updates.push(value)
    }
  })
  const chip = (name: string) => screen.getByRole('button', { name })
  return { ...view, updates, chip }
}

describe('GlobalTimePicker', () => {
  test('renders a chip per configured custom range', () => {
    const { chip } = renderPicker(rangeOfSeconds(99))
    expect(chip('Last 4 hours')).toBeInTheDocument()
    expect(chip('Last 25 hours')).toBeInTheDocument()
  })

  test('highlights the chip matching the seeded range on load', () => {
    const { chip } = renderPicker(rollingRange(4 * 3600))
    expect(chip('Last 4 hours')).toHaveAttribute('aria-pressed', 'true')
    expect(chip('Last 25 hours')).toHaveAttribute('aria-pressed', 'false')
  })

  test('clicking a chip applies a range of its duration and marks it pressed', async () => {
    const { chip, updates } = renderPicker(rangeOfSeconds(99))
    await fireEvent.click(chip('Last 25 hours'))

    expect(updates).toHaveLength(1)
    const applied = updates[0]!
    const spanMs = applied.to.toDate().getTime() - applied.from.toDate().getTime()
    expect(spanMs).toBe(25 * 3600 * 1000)
    expect(chip('Last 25 hours')).toHaveAttribute('aria-pressed', 'true')
  })

  test('an external range change clears the pressed chip', async () => {
    const { chip, rerender } = renderPicker(rollingRange(4 * 3600))
    expect(chip('Last 4 hours')).toHaveAttribute('aria-pressed', 'true')

    await rerender({
      customTimeRanges: CUSTOM_RANGES,
      serverTimeZone: 'America/Los_Angeles',
      firstDayOfWeek: null,
      modelValue: rangeOfSeconds(99)
    })
    expect(chip('Last 4 hours')).toHaveAttribute('aria-pressed', 'false')
  })

  // jsdom's locale is en-US, so the browser-locale default is a Sunday week start.
  test.each([
    { firstDayOfWeek: 'monday' as const, expected: 'Monday' },
    { firstDayOfWeek: 'saturday' as const, expected: 'Saturday' },
    { firstDayOfWeek: null, expected: 'Sunday' }
  ])(
    'the calendar starts the week on $expected for preference $firstDayOfWeek',
    async ({ firstDayOfWeek, expected }) => {
      renderPicker(rangeOfSeconds(99), firstDayOfWeek)
      const trigger = screen
        .getAllByRole('button')
        .find((button) => button.getAttribute('aria-haspopup') === 'dialog')!
      await fireEvent.click(trigger)

      const grid = (await screen.findAllByRole('grid'))[0]!
      const firstColumnHeader = within(grid).getAllByRole('columnheader')[0]!
      expect(firstColumnHeader).toHaveAccessibleName(expected)
    }
  )
})
