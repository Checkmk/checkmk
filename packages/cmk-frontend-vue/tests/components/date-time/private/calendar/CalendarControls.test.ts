/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { describe, expect, test } from 'vitest'

import CalendarControls from '@/components/date-time/private/calendar/CalendarControls.vue'

import { MONTH_NAMES_EN } from '../../dateTimeTestFixtures'
import { openDropdown, selectDropdownOption } from '../../pickerTestHarness'

function renderControls(props: Record<string, unknown> = {}) {
  return render(CalendarControls, {
    props: {
      month: 6,
      year: 2026,
      monthNamesDisplay: MONTH_NAMES_EN,
      yearRange: [2006, 2028] as [number, number],
      ...props
    }
  })
}

/** Visible labels of the options in the currently open dropdown, in render order. */
async function openOptionTexts(user: ReturnType<typeof userEvent.setup>, label: string) {
  await openDropdown(user, label)
  const options = await screen.findAllByRole('option')
  return options.map((option) => option.textContent?.trim() ?? '')
}

describe('CalendarControls', () => {
  test('month dropdown lists all twelve months in order', async () => {
    const user = userEvent.setup()
    renderControls()
    expect(await openOptionTexts(user, 'Month')).toEqual(MONTH_NAMES_EN)
  })

  test('year dropdown lists the range newest-first', async () => {
    const user = userEvent.setup()
    renderControls({ year: 2020 })
    const years = await openOptionTexts(user, 'Year')
    expect(years[0]).toBe('2028')
    expect(years[years.length - 1]).toBe('2006')
    expect(years).toHaveLength(2028 - 2006 + 1)
  })

  test('year dropdown includes a displayed year above the range', async () => {
    const user = userEvent.setup()
    renderControls({ year: 2030 })
    const years = await openOptionTexts(user, 'Year')
    expect(years[0]).toBe('2030')
    expect(years[years.length - 1]).toBe('2006')
  })

  test('year dropdown includes a displayed year below the range', async () => {
    const user = userEvent.setup()
    renderControls({ year: 2000 })
    const years = await openOptionTexts(user, 'Year')
    expect(years[0]).toBe('2028')
    expect(years[years.length - 1]).toBe('2000')
  })

  test('selecting a month emits its number', async () => {
    const user = userEvent.setup()
    const { emitted } = renderControls()
    await selectDropdownOption(user, 'Month', 'March')
    expect(emitted('update:month')).toEqual([[3]])
  })

  test('selecting a year emits its number', async () => {
    const user = userEvent.setup()
    const { emitted } = renderControls()
    await selectDropdownOption(user, 'Year', '2020')
    expect(emitted('update:year')).toEqual([[2020]])
  })
})
