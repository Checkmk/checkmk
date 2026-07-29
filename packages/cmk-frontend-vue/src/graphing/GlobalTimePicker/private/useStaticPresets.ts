/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  type ZonedDateTime,
  endOfMonth,
  endOfWeek,
  endOfYear,
  getLocalTimeZone,
  now,
  startOfMonth,
  startOfWeek,
  startOfYear
} from '@internationalized/date'
import type { RangePreset, Weekday } from 'cmk-ui-library/components/date-time'
import usei18n from 'cmk-ui-library/lib/i18n'
import { type MaybeRefOrGetter, toValue } from 'vue'

import { weekdayAsDayToken } from './firstDayOfWeek.ts'

function startOfDay(at: ZonedDateTime): ZonedDateTime {
  return at.set({ hour: 0, minute: 0, second: 0, millisecond: 0 })
}
function endOfDay(at: ZonedDateTime): ZonedDateTime {
  return at.set({ hour: 23, minute: 59, second: 59, millisecond: 999 })
}

/** The built-in quick ranges (Today, Yesterday, …). Call within `setup()`: it resolves `usei18n`.
 * `firstDayOfWeek` overrides the browser locale's start of week for "This week".
 */
export function useStaticPresets(
  firstDayOfWeek?: MaybeRefOrGetter<Weekday | undefined>
): RangePreset[] {
  const browserLocale = new Intl.DateTimeFormat().resolvedOptions().locale
  const { _t } = usei18n()

  return [
    {
      id: 'today',
      label: _t('Today'),
      getRange: () => {
        const at = now(getLocalTimeZone())
        return { from: startOfDay(at), to: endOfDay(at) }
      }
    },
    {
      id: 'yesterday',
      label: _t('Yesterday'),
      getRange: () => {
        const yesterday = now(getLocalTimeZone()).subtract({ days: 1 })
        return { from: startOfDay(yesterday), to: endOfDay(yesterday) }
      }
    },
    {
      id: 'this-week',
      label: _t('This week'),
      getRange: () => {
        const at = now(getLocalTimeZone())
        const dayToken = weekdayAsDayToken(toValue(firstDayOfWeek))
        return {
          from: startOfDay(startOfWeek(at, browserLocale, dayToken)),
          to: endOfDay(endOfWeek(at, browserLocale, dayToken))
        }
      }
    },
    {
      id: 'this-month',
      label: _t('This month'),
      getRange: () => {
        const at = now(getLocalTimeZone())
        return { from: startOfDay(startOfMonth(at)), to: endOfDay(endOfMonth(at)) }
      }
    },
    {
      id: 'this-year',
      label: _t('This year'),
      getRange: () => {
        const at = now(getLocalTimeZone())
        return { from: startOfDay(startOfYear(at)), to: endOfDay(endOfYear(at)) }
      }
    }
  ]
}
