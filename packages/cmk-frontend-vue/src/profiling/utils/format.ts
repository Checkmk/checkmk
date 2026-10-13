/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { renderDateAndTime } from 'cmk-ui-library/lib/renderTime'
import { userSpecificUnit } from 'cmk-ui-library/lib/unit-format/unitFormatter'

// Reuse the shared notation formatters for the two adaptive-unit cases (bytes
// and seconds) instead of hand-rolling the prefix maths. The temperature unit
// is irrelevant here — 'B'/'s' are not temperature symbols, so the value passes
// through unconverted.
const { formatter: byteFormatter } = userSpecificUnit(
  { notation: 'iec', symbol: 'B', precision: { type: 'auto', digits: 2 } },
  'celsius'
)
const { formatter: durationFormatter } = userSpecificUnit(
  { notation: 'time', symbol: 's', precision: { type: 'auto', digits: 2 } },
  'celsius'
)

export function formatTimestamp(ts: string): string {
  const d = new Date(ts)
  return isNaN(d.getTime()) ? ts : renderDateAndTime(d)
}

export function formatFileSize(bytes: number): string {
  return byteFormatter.render(bytes)
}

/** Format milliseconds with "ms" suffix and 1 decimal (used across summary bar, table, tooltips). */
export function formatMs(ms: number): string {
  return `${ms.toFixed(1)} ms`
}

/** Format a percent (0..100) with 1 decimal and "%" suffix. */
export function formatPercent(pct: number): string {
  return `${pct.toFixed(1)}%`
}

/** Format an integer count using locale-aware grouping (thousand separator). */
export function formatCount(n: number): string {
  return n.toLocaleString()
}

/**
 * Format a call count as cProfile does: a single number normally, or
 * `total/primitive` when they differ (i.e. the function recursed). The second
 * number is the non-recursive call count, so a `total/primitive` label makes
 * recursive calls easy to spot.
 */
export function formatCalls(total: number, primitive: number): string {
  if (total === primitive) {
    return formatCount(total)
  }
  return `${formatCount(total)}/${formatCount(primitive)}`
}

/** Format a duration given in seconds with an adaptive unit (s / ms / µs / min / h). */
export function formatDuration(seconds: number): string {
  return durationFormatter.render(seconds)
}
