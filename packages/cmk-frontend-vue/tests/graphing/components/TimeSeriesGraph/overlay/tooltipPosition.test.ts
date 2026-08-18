/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import {
  type TooltipPlacementInput,
  computeTooltipPosition
} from '@/graphing/components/TimeSeriesGraph/overlay/tooltipPosition'

function placementInput(overrides: Partial<TooltipPlacementInput>): TooltipPlacementInput {
  return {
    cursorX: 400,
    cursorY: 300,
    tooltipWidth: 300,
    tooltipHeight: 100,
    viewportWidth: 1000,
    viewportHeight: 600,
    cursorOffset: 16,
    ...overrides
  }
}

describe('computeTooltipPosition', () => {
  test('places the tooltip right of the cursor, top aligned with it', () => {
    expect(computeTooltipPosition(placementInput({}))).toEqual({ left: 416, top: 300 })
  })

  test('flips to the left of the cursor when it would cross the right viewport edge', () => {
    expect(computeTooltipPosition(placementInput({ cursorX: 800 }))).toEqual({
      left: 800 - 16 - 300,
      top: 300
    })
  })

  test('clamps to the left viewport edge when the flipped position is negative', () => {
    const position = computeTooltipPosition(
      placementInput({ cursorX: 200, viewportWidth: 400, tooltipWidth: 300 })
    )
    expect(position.left).toBe(0)
  })

  test('clamps to the top viewport edge', () => {
    expect(computeTooltipPosition(placementInput({ cursorY: -20 })).top).toBe(0)
  })

  test('clamps to the bottom viewport edge', () => {
    expect(computeTooltipPosition(placementInput({ cursorY: 590 })).top).toBe(600 - 100)
  })

  test('pins a tooltip taller than the viewport to the top', () => {
    expect(computeTooltipPosition(placementInput({ tooltipHeight: 700 })).top).toBe(0)
  })

  test('degrades to cursor plus offset for a zero-size tooltip', () => {
    expect(computeTooltipPosition(placementInput({ tooltipWidth: 0, tooltipHeight: 0 }))).toEqual({
      left: 416,
      top: 300
    })
  })
})
