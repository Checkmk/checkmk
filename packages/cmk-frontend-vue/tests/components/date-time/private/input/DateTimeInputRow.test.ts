/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDate } from '@internationalized/date'
import { fireEvent, render, screen } from '@testing-library/vue'
import { afterEach, describe, expect, test, vi } from 'vitest'

import type { TranslatedString } from '@/lib/i18nString'

import DateTimeInputRow from '@/components/date-time/private/input/DateTimeInputRow.vue'
import type { DateTimePartsDraft } from '@/components/date-time/types'

import { DMY, MONTH_NAMES_EN, WEEKDAY_NAMES_SHORT_EN } from '../../dateTimeTestFixtures'

const renderRow = (modelValue: DateTimePartsDraft) =>
  render(DateTimeInputRow, {
    props: {
      label: 'From' as TranslatedString,
      dateFormat: DMY,
      monthNames: MONTH_NAMES_EN,
      hourCycle: 24,
      weekdayNames: WEEKDAY_NAMES_SHORT_EN,
      modelValue
    }
  })

afterEach(() => {
  vi.restoreAllMocks()
})

describe('DateTimeInputRow', () => {
  test('re-emits commit from the inner date-time input', async () => {
    const date = new CalendarDate(2026, 6, 10)
    const time = { hour: 8, minute: 5 }
    const { container, emitted } = renderRow({ date, time })

    await fireEvent.keyDown(container.querySelector('input')!, { key: 'Enter' })

    expect(emitted('commit')).toEqual([[]])
  })

  test('the visual From/To label is hidden from assistive tech', () => {
    const { container } = renderRow({
      date: new CalendarDate(2026, 6, 10),
      time: { hour: 8, minute: 5 }
    })
    const label = Array.from(container.querySelectorAll('label')).find(
      (element) => element.textContent?.trim() === 'From'
    )!
    // The date/time fields are already named "Date"/"Time" (or "From date" etc. from the parent),
    // so the loose "From" text would be redundant for assistive tech.
    expect(label).toHaveAttribute('aria-hidden', 'true')
  })

  test('weekday is shown to sighted users only', () => {
    // 2026-06-10 is a Wednesday.
    renderRow({
      date: new CalendarDate(2026, 6, 10),
      time: null
    })
    // The abbreviation is shown visually (aria-hidden), distinct from the equally aria-hidden width
    // ghosts that hold every short name — the ghost class is the only way to single it out.
    expect(screen.getByText('Wed', { ignore: '.cmk-ghost-width__ghost' })).toBeInTheDocument()
    // The weekday is a sighted convenience: nothing weekday-related is exposed to assistive tech
    // (the date field's spinbutton segments already speak the full date).
    expect(screen.queryByText('Wednesday')).not.toBeInTheDocument()
  })

  test('no weekday with null date', () => {
    renderRow({ date: null, time: { hour: 8, minute: 5 } })
    expect(screen.queryByText('Wed', { ignore: '.cmk-ghost-width__ghost' })).not.toBeInTheDocument()
    expect(screen.queryByText('Wednesday')).not.toBeInTheDocument()
  })
})
