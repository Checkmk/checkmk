/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDate } from '@internationalized/date'

export function parseDateString(value: string | undefined): CalendarDate | undefined {
  if (!value) {
    return undefined
  }
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (!match) {
    return undefined
  }
  try {
    return new CalendarDate(parseInt(match[1]!), parseInt(match[2]!), parseInt(match[3]!))
  } catch {
    return undefined
  }
}
