/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { MetricAttribute } from '../../metricAttributes'

export interface HoverSample {
  metricName: string
  label: string
  color: string
  formattedValue: string
  /** Empty for a line fetched from an RRD. */
  attributes: MetricAttribute[]
  pixelY: number | null
  snapTime: number | null
  isClosest: boolean
}

export interface HoverState {
  cursorX: number
  cursorY: number
  clientX: number
  clientY: number
  snapX: number
  snapTime: number
  samples: HoverSample[]
}

/** Zero inside the drawn edge, else the distance to its nearer side; a line's edge has no height. */
export function metricHitDistance(
  cursorY: number,
  drawnTopPixel: number,
  drawnBottomPixel: number
): number {
  const edgeTop = Math.min(drawnTopPixel, drawnBottomPixel)
  const edgeBottom = Math.max(drawnTopPixel, drawnBottomPixel)
  if (cursorY < edgeTop) {
    return edgeTop - cursorY
  }
  if (cursorY > edgeBottom) {
    return cursorY - edgeBottom
  }
  return 0
}
