/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromDate } from '@internationalized/date'
import usei18n from 'cmk-ui-library/lib/i18n'

import { formatDate, formatTime, zonedToParts } from './dateTimeUtils'
import type { ResolvedDateTimeSettings } from './types'

type RelativeDaySettings = Pick<ResolvedDateTimeSettings, 'timeZone' | 'hourCycle' | 'dateFormat'>

export function formatDateOrRelativeDay(
  date: Date,
  settings: RelativeDaySettings,
  now: Date = new Date()
): string {
  const { _t } = usei18n()
  const parts = zonedToParts(fromDate(date, settings.timeZone))
  const today = zonedToParts(fromDate(now, settings.timeZone)).date
  if (parts.date.compare(today) === 0) {
    return formatTime(parts.time, settings.hourCycle)
  }
  if (parts.date.compare(today.subtract({ days: 1 })) === 0) {
    return _t('Yesterday')
  }
  return formatDate(parts.date, settings.dateFormat)
}
