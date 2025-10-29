/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TimeSpan } from 'cmk-shared-typing/typescript/vue_formspec_components'

type Magnitude = TimeSpan['displayed_magnitudes'][number]

export const ALL_MAGNITUDES = new Map<Magnitude, number>([
  ['day', 24 * 60 * 60],
  ['hour', 60 * 60],
  ['minute', 60],
  ['second', 1],
  ['millisecond', 0.001]
])

export function getSelectedMagnitudes(displayedMagnitudes: Array<Magnitude>): Array<Magnitude> {
  // make sure selected magnitudes are sorted and only contain known elements
  const result: Array<Magnitude> = []
  ALL_MAGNITUDES.forEach((_, magnitude) => {
    if (displayedMagnitudes.includes(magnitude)) {
      result.push(magnitude)
    }
  })
  return result
}

function getFactor(magnitude: Magnitude): number {
  const factor = ALL_MAGNITUDES.get(magnitude)
  if (factor === undefined) {
    throw new Error(`can not find factor for magnitude ${magnitude}`)
  }
  return factor
}

export function joinToSeconds(values: Partial<Record<Magnitude, number>>): number {
  return Object.entries(values).reduce(
    (partial, [magnitude, value]) => partial + value * getFactor(magnitude as Magnitude),
    0
  )
}

export function splitToUnits(
  value: number,
  selectedMagnitudes: Array<Magnitude>
): Partial<Record<Magnitude, number>> {
  const result: Partial<Record<Magnitude, number>> = {}
  for (const [index, magnitude] of selectedMagnitudes.entries()) {
    const factor = getFactor(magnitude)
    if (factor <= value) {
      let quotient = value / factor
      if (index !== selectedMagnitudes.length - 1) {
        // dont floor the last element
        quotient = Math.floor(quotient)
      } else {
        // but round it:
        quotient = Math.round(quotient)
      }
      const remainder = value % factor
      value = remainder
      result[magnitude] = quotient
    }
  }
  return result
}
