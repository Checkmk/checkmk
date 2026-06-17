/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDateTime, type ZonedDateTime, toZoned } from '@internationalized/date'
import { fireEvent, render, screen } from '@testing-library/vue'
import type { CustomGraphTimeRange } from 'cmk-shared-typing/typescript/global_time_picker'
import { describe, expect, test } from 'vitest'

import type { DateTimeRange } from '@/components/date-time'

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

function renderPicker(modelValue: DateTimeRange) {
  const updates: DateTimeRange[] = []
  const view = render(GlobalTimePicker, {
    props: {
      customTimeRanges: CUSTOM_RANGES,
      serverTimeZone: 'America/Los_Angeles',
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
      modelValue: rangeOfSeconds(99)
    })
    expect(chip('Last 4 hours')).toHaveAttribute('aria-pressed', 'false')
  })
})
