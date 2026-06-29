/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ZonedDateTime } from '@internationalized/date'

export function pad2(n: number): string {
  return String(n).padStart(2, '0')
}

export function isoDate(zdt: ZonedDateTime): string {
  return `${zdt.year}-${pad2(zdt.month)}-${pad2(zdt.day)}`
}

// Mirrors the backend's get_step_label()
export function stepLabel(step: number): string {
  const fmt = (n: number) => (n % 1 === 0 ? String(n) : n.toFixed(1))
  if (step < 3600) {
    return `${fmt(step / 60)} m`
  }
  if (step < 86400) {
    return `${fmt(step / 3600)} h`
  }
  return `${fmt(step / 86400)} d`
}

export function shortWeekday(unix: number, tz: string): string {
  return new Intl.DateTimeFormat(undefined, { weekday: 'short', timeZone: tz }).format(unix * 1000)
}
