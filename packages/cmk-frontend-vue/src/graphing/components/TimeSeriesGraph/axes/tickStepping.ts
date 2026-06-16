/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Ported from cmk-frontend/number_format.ts: the "nice number" domain rounding and
// tick-step selection for value axes.

function mantissaAndExp(value: number, base: number): [number, number] {
  let exp = Math.floor(Math.log(value) / Math.log(base))
  let mantissa = value / base ** exp
  if (mantissa < 1) {
    mantissa *= base
    exp -= 1
  }
  return [mantissa, exp]
}

function tickStep(range: number, ticks: number, increments: number[]): number {
  const base = increments[increments.length - 1]!
  const [mantissa, exp] = mantissaAndExp(range / ticks, base)
  return increments.find((increment) => mantissa <= increment)! * base ** exp
}

export function stepIncrements(stepping: 'binary' | 'decimal'): number[] {
  if (stepping === 'binary') {
    return [1, 2, 4, 8, 16]
  }
  return [1, 2, 5, 10]
}

export function alignedDomain(
  domain: [number, number],
  ticks: number,
  increments: number[]
): [number, number, number] {
  let [start, end] = domain.map((value) => value || 0).sort((a, b) => a - b) as [number, number]
  if (start === end) {
    end += 1
  }
  let step = tickStep(end - start, ticks, increments)
  start = Math.floor(start / step) * step
  end = Math.ceil(end / step) * step
  step = tickStep(end - start, ticks, increments)
  return [start, end, step]
}
