/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TimeInterval } from '../../../types'
import type { MetricAttribute } from '../../metricAttributes'

export interface HoverSample {
  metricName: string
  label: string
  color: string
  formattedValue: string
  /** Empty for a line fetched from an RRD. */
  attributes: MetricAttribute[]
  drawnPoint: { x: number; y: number } | null
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
  /** The bin the hover snapped to, if it snapped to a bar. */
  snapInterval: TimeInterval | null
  samples: HoverSample[]
}

export function metricHitDistance(
  cursorY: number,
  drawnTopPixel: number,
  drawnBottomPixel: number
): number {
  const edgeTop = Math.min(drawnTopPixel, drawnBottomPixel)
  const edgeBottom = Math.max(drawnTopPixel, drawnBottomPixel)
  const distanceAboveEdge = edgeTop - cursorY
  const distanceBelowEdge = cursorY - edgeBottom
  return Math.max(0, distanceAboveEdge, distanceBelowEdge)
}
