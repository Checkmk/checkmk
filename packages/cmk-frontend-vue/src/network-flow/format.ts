/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { SIFormatter } from 'cmk-ui-library/lib/unit-format/notationFormatter'

// Canonical SI formatters (base 1000), matching the backend and the network flow
// widgets: 90_400_000_000 B -> "90.40 GB", 1_360_000 -> "1.4 M".
const BYTES = new SIFormatter('B', { type: 'strict', digits: 2 })
const COUNT = new SIFormatter('', { type: 'strict', digits: 1 })

const { _t } = usei18n()

export function formatBytes(value: number): string {
  return BYTES.render(value)
}

export function formatCount(value: number): string {
  return COUNT.render(value)
}

export const DASH = '–'

/**
 * A signed change against a previous period.
 *
 * Growth out of nothing has no ratio, so it says "new" rather than falling back
 * to the dash that means "nothing to compare".
 */
export function formatDelta(value: number, previous: number): string {
  if (previous <= 0) {
    return value > 0 ? _t('new') : DASH
  }
  const ratio = (value - previous) / previous
  return `${ratio >= 0 ? '+' : '-'}${Math.abs(ratio * 100).toFixed(1)}%`
}

function pad(value: number): string {
  return String(value).padStart(2, '0')
}

/**
 * A clock time as Checkmk renders one: 24-hour HH:MM:SS.
 *
 * Deliberately not left to Intl's locale default, which renders 12-hour AM/PM
 * for en-US and would make the column both wider and inconsistent with the rest
 * of Checkmk. No date: a listing covers a single time range, so repeating it on
 * every row tells the reader nothing.
 *
 * The zone is the browser's, matching the other Vue date-time components (they
 * resolve to getLocalTimeZone() unless handed a zone). Where a user's browser
 * sits in a different zone from the site, these times will not line up with the
 * timestamps Python renders server-side for the same flows; carrying the site
 * zone into the page would be needed to close that gap.
 */
export function formatTimeOfDay(unixSeconds: number): string {
  const date = new Date(unixSeconds * 1000)
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}
