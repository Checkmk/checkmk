/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
export interface TimeValuePoint {
  time: number
  value: number
}

export function clampedValueAt(
  polylineSortedByTime: readonly TimeValuePoint[],
  time: number
): number {
  const first = polylineSortedByTime[0]
  const last = polylineSortedByTime[polylineSortedByTime.length - 1]
  if (first === undefined || last === undefined) {
    return NaN
  }
  if (time <= first.time) {
    return first.value
  }
  if (time >= last.time) {
    return last.value
  }
  const nextIndex = polylineSortedByTime.findIndex((point) => point.time > time)
  const next = polylineSortedByTime[nextIndex]!
  const previous = polylineSortedByTime[nextIndex - 1]!
  const fraction = (time - previous.time) / (next.time - previous.time)
  return previous.value + fraction * (next.value - previous.value)
}
