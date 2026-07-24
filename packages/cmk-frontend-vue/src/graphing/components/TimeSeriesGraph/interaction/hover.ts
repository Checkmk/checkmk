/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export interface HoverSample {
  metricName: string
  label: string
  color: string
  formattedValue: string
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

export function metricHitDistance(
  cursorY: number,
  drawnTopPixel: number,
  drawnBottomPixel: number,
  filled: boolean
): number {
  if (!filled) {
    return Math.abs(cursorY - drawnTopPixel)
  }
  const bandTop = Math.min(drawnTopPixel, drawnBottomPixel)
  const bandBottom = Math.max(drawnTopPixel, drawnBottomPixel)
  if (cursorY < bandTop) {
    return bandTop - cursorY
  }
  if (cursorY > bandBottom) {
    return cursorY - bandBottom
  }
  return 0
}
