/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import type { Weekday } from 'cmk-ui-library/components/date-time'

const WEEKDAY_BY_PREFERENCE: Record<
  NonNullable<GlobalTimePickerProps['first_day_of_week']>,
  Weekday
> = {
  saturday: 6,
  sunday: 0,
  monday: 1
}

/** `undefined` leaves the start of the week to the browser locale.
 */
export function firstDayOfWeekAsWeekday(
  preference: GlobalTimePickerProps['first_day_of_week']
): Weekday | undefined {
  return preference === null ? undefined : WEEKDAY_BY_PREFERENCE[preference]
}

const DAY_TOKENS = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'] as const

/** The token `@internationalized/date` takes as week-start override. Declared locally because
 * the library does not export its `DayOfWeek` type.
 */
export function weekdayAsDayToken(
  weekday: Weekday | undefined
): (typeof DAY_TOKENS)[number] | undefined {
  return weekday === undefined ? undefined : DAY_TOKENS[weekday]
}
