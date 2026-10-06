/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { SIFormatter, TimeFormatter } from 'cmk-ui-library/lib/unit-format/notationFormatter'

// Canonical SI formatters (base 1000), matching the backend and the network flow
// widgets: 90_400_000_000 B -> "90.40 GB", 1_360_000 -> "1.4 M".
const BYTES = new SIFormatter('B', { type: 'strict', digits: 2 })
const COUNT = new SIFormatter('', { type: 'strict', digits: 1 })
// Windows are whole seconds, so the digits never come into it.
const DURATION = new TimeFormatter('s', { type: 'auto', digits: 0 })

const { _t } = usei18n()

export function formatBytes(value: number): string {
  return BYTES.render(value)
}

export function formatCount(value: number): string {
  return COUNT.render(value)
}

/** A window length as Checkmk writes one: 14_400 -> "4 h", 5_400 -> "1 h 30 min". */
export function formatDuration(seconds: number): string {
  return DURATION.render(seconds)
}

/** Heads a comparison column: "Prev 4 h" for a four-hour window. */
export function previousWindowLabel(window: { start: number; end: number }): string {
  const { _t } = usei18n()
  return _t('Prev %{duration}', { duration: formatDuration(window.end - window.start) })
}

export const DASH = '–'

/** A change against a previous period, split so the direction can be drawn. */
export interface Delta {
  /**
   * The signed ratio an arrow points along. Null where there is no direction to
   * point in: nothing to compare against, or growth out of nothing, which has
   * no ratio. Zero is no change, which is also no arrow.
   */
  ratio: number | null
  /** The change in words. Unsigned: the arrow beside it carries the sign. */
  text: string
}

/**
 * A change against a previous period.
 *
 * Growth out of nothing has no ratio, so it says "new" rather than falling back
 * to the dash that means "nothing to compare".
 */
export function formatDelta(value: number, previous: number): Delta {
  if (previous <= 0) {
    return value > 0 ? { ratio: null, text: _t('new') } : { ratio: null, text: DASH }
  }
  const ratio = (value - previous) / previous
  return { ratio, text: `${Math.abs(ratio * 100).toFixed(1)}%` }
}

/** The dash that stands in for a comparison this row cannot make. */
export function noDelta(): Delta {
  return { ratio: null, text: DASH }
}
