/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

// The legacy figures size the rings by an exponent of 0.33, not by an exact cube root.
const RING_EXPONENT = 0.33

/** The SVG path of a pointy-top hexagon centred on the origin. */
export function hexagonPath(radius: number): string {
  const corners = Array.from({ length: 6 }, (_, index) => {
    const angle = (index * Math.PI) / 3
    return `${round(Math.sin(angle) * radius)},${round(-Math.cos(angle) * radius)}`
  })
  return `M${corners.join('L')}Z`
}

/** Each part with the radius of its nested ring, from the outermost inwards; zero if empty. */
export function nestedRings<T extends { count: number }>(
  parts: readonly T[],
  radius: number
): { part: T; radius: number }[] {
  const total = parts.reduce((sum, part) => sum + part.count, 0)
  let remaining = total
  return parts.map((part) => {
    const ringRadius =
      part.count === 0
        ? 0
        : (Math.pow(remaining, RING_EXPONENT) / Math.pow(total, RING_EXPONENT)) * radius
    remaining -= part.count
    return { part, radius: ringRadius }
  })
}

function round(value: number): number {
  return Math.round(value * 1000) / 1000
}
