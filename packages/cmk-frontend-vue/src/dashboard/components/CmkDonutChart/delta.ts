/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

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
