/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export interface TooltipPlacementInput {
  cursorX: number
  cursorY: number
  tooltipWidth: number
  tooltipHeight: number
  viewportWidth: number
  viewportHeight: number
  cursorOffsetX: number
  cursorOffsetY: number
}

const clamp = (value: number, min: number, max: number): number =>
  Math.min(Math.max(value, min), max)

export function computeTooltipPosition(input: TooltipPlacementInput): {
  left: number
  top: number
} {
  let left = input.cursorX + input.cursorOffsetX
  if (left + input.tooltipWidth > input.viewportWidth) {
    left = input.cursorX - input.cursorOffsetX - input.tooltipWidth
  }
  left = clamp(left, 0, Math.max(0, input.viewportWidth - input.tooltipWidth))

  const top = clamp(
    input.cursorY + input.cursorOffsetY,
    0,
    Math.max(0, input.viewportHeight - input.tooltipHeight)
  )

  return { left, top }
}
