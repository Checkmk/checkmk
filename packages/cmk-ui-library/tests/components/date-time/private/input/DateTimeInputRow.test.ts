/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDate } from '@internationalized/date'
import { fireEvent, render, within } from '@testing-library/vue'
import DateTimeInputRow from 'cmk-ui-library/components/date-time/private/input/DateTimeInputRow.vue'
import type { DateTimePartsDraft } from 'cmk-ui-library/components/date-time/types'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { describe, expect, test } from 'vitest'

import { DMY, MONTH_NAMES_EN } from '../../dateTimeTestFixtures'

const renderRow = (modelValue: DateTimePartsDraft) =>
  render(DateTimeInputRow, {
    props: {
      label: 'From' as TranslatedString,
      dateFormat: DMY,
      monthNames: MONTH_NAMES_EN,
      hourCycle: 24,
      timeSelectorLabel: 'Choose start time' as TranslatedString,
      modelValue
    }
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

  test('the clock button picks the time and keeps the date', async () => {
    const date = new CalendarDate(2026, 6, 10)
    const view = renderRow({ date, time: { hour: 8, minute: 5 } })

    await fireEvent.click(view.getByRole('button', { name: 'Choose start time' }))
    const hours = within(view.getByRole('listbox', { name: 'Hour' }))
    await fireEvent.click(hours.getByRole('option', { name: '17' }))
    await fireEvent.click(view.getByRole('button', { name: 'Apply' }))

    expect(view.emitted('update:modelValue')).toEqual([[{ date, time: { hour: 17, minute: 5 } }]])
    expect(view.queryByRole('listbox', { name: 'Hour' })).toBeNull()
  })
})
