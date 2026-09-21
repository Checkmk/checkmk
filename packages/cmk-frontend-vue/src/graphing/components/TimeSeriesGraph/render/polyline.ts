/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
export interface TimeValuePoint {
  time: number
  value: number
}

/** Reads a polyline sorted by time at `time`; flat beyond either end. */
export function valueAt(polyline: readonly TimeValuePoint[], time: number): number {
  const first = polyline[0]
  const last = polyline[polyline.length - 1]
  if (first === undefined || last === undefined) {
    return NaN
  }
  if (time <= first.time) {
    return first.value
  }
  if (time >= last.time) {
    return last.value
  }
  const nextIndex = polyline.findIndex((point) => point.time > time)
  const next = polyline[nextIndex]!
  const previous = polyline[nextIndex - 1]!
  const fraction = (time - previous.time) / (next.time - previous.time)
  return previous.value + fraction * (next.value - previous.value)
}
