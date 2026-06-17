/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CalendarDate } from '@internationalized/date'

/** Whether the calendar selects a single date or a date range. */
export type CalendarMode = 'single' | 'range'

/** Selection state shared by single- and range-calendars. `end === null` means single-date mode. */
export interface CalendarSelection {
  start: CalendarDate | null
  end: CalendarDate | null
}
