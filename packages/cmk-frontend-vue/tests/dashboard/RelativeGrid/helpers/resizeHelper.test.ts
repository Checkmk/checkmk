/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { clampResizeDeltas } from '@/dashboard/components/RelativeGrid/helpers/resizeHelper'
import { WIDGET_MIN_SIZE } from '@/dashboard/components/RelativeGrid/types'

describe('clampResizeDeltas', () => {
  // Standard setup: dashlet at (100, 100) with size 200x200 in a 1000x800 dashboard
  const initialLeft = 100
  const initialTop = 100
  const initialWidth = 200
  const initialHeight = 200
  const dashboardWidth = 1000
  const dashboardHeight = 800

  describe('horizontal (left / right)', () => {
    it('should pass through deltas within bounds', () => {
      const right = clampResizeDeltas(
        'right',
        50,
        0,
        initialLeft,
        initialTop,
        initialWidth,
        initialHeight,
        dashboardWidth,
        dashboardHeight,
        WIDGET_MIN_SIZE
      )

      expect(right.dx).toBe(50)

      const left = clampResizeDeltas(
        'left',
        50,
        0,
        initialLeft,
        initialTop,
        initialWidth,
        initialHeight,
        dashboardWidth,
        dashboardHeight,
        WIDGET_MIN_SIZE
      )

      expect(left.dx).toBe(50)
    })

    it('should clamp right expansion to dashboard boundary', () => {
      const result = clampResizeDeltas(
        'right',
        800,
        0,
        initialLeft,
        initialTop,
        initialWidth,
        initialHeight,
        dashboardWidth,
        dashboardHeight,
        WIDGET_MIN_SIZE
      )

      // maxWidth = 1000 - 100 = 900; proposed = 200 + 800 = 1000 → 900 → dx = 700
      expect(result.dx).toBe(700)
    })

    it('should clamp left edge to 0', () => {
      const result = clampResizeDeltas(
        'left',
        -200,
        0,
        initialLeft,
        initialTop,
        initialWidth,
        initialHeight,
        dashboardWidth,
        dashboardHeight,
        WIDGET_MIN_SIZE
      )

      // proposed left = 100 + (-200) = -100 → clamped to 0 → dx = -100
      expect(result.dx).toBe(-100)
    })

    it('should enforce minimum width from right', () => {
      const result = clampResizeDeltas(
        'right',
        -150,
        0,
        initialLeft,
        initialTop,
        initialWidth,
        initialHeight,
        dashboardWidth,
        dashboardHeight,
        WIDGET_MIN_SIZE
      )

      // proposed = 200 + (-150) = 50 → clamped to minW=120 → dx = 120-200 = -80
      expect(result.dx).toBe(-80)
    })

    it('should enforce minimum width from left', () => {
      const result = clampResizeDeltas(
        'left',
        200,
        0,
        initialLeft,
        initialTop,
        initialWidth,
        initialHeight,
        dashboardWidth,
        dashboardHeight,
        WIDGET_MIN_SIZE
      )

      // maxLeft = R - minW = 300-120 = 180 → dx = 180 - 100 = 80
      expect(result.dx).toBe(80)
    })
  })

  describe('vertical (top / bottom)', () => {
    it('should pass through deltas within bounds', () => {
      const bottom = clampResizeDeltas(
        'bottom',
        0,
        50,
        initialLeft,
        initialTop,
        initialWidth,
        initialHeight,
        dashboardWidth,
        dashboardHeight,
        WIDGET_MIN_SIZE
      )

      expect(bottom.dy).toBe(50)

      const top = clampResizeDeltas(
        'top',
        0,
        50,
        initialLeft,
        initialTop,
        initialWidth,
        initialHeight,
        dashboardWidth,
        dashboardHeight,
        WIDGET_MIN_SIZE
      )

      expect(top.dy).toBe(50)
    })

    it('should clamp bottom expansion to dashboard boundary', () => {
      const result = clampResizeDeltas(
        'bottom',
        0,
        600,
        initialLeft,
        initialTop,
        initialWidth,
        initialHeight,
        dashboardWidth,
        dashboardHeight,
        WIDGET_MIN_SIZE
      )

      // maxHeight = 800 - 100 = 700; proposed = 200 + 600 = 800 → 700 → dy = 500
      expect(result.dy).toBe(500)
    })

    it('should clamp top edge to 0', () => {
      const result = clampResizeDeltas(
        'top',
        0,
        -200,
        initialLeft,
        initialTop,
        initialWidth,
        initialHeight,
        dashboardWidth,
        dashboardHeight,
        WIDGET_MIN_SIZE
      )

      expect(result.dy).toBe(-100)
    })

    it('should enforce minimum height from bottom', () => {
      const result = clampResizeDeltas(
        'bottom',
        0,
        -150,
        initialLeft,
        initialTop,
        initialWidth,
        initialHeight,
        dashboardWidth,
        dashboardHeight,
        WIDGET_MIN_SIZE
      )

      expect(result.dy).toBe(-80)
    })

    it('should enforce minimum height from top', () => {
      const result = clampResizeDeltas(
        'top',
        0,
        200,
        initialLeft,
        initialTop,
        initialWidth,
        initialHeight,
        dashboardWidth,
        dashboardHeight,
        WIDGET_MIN_SIZE
      )

      // maxTop = B - minH = 300-120 = 180 → dy = 180 - 100 = 80
      expect(result.dy).toBe(80)
    })
  })

  describe('compound directions', () => {
    it('should clamp both axes for all four corners', () => {
      const topLeft = clampResizeDeltas(
        'top-left',
        -200,
        -200,
        initialLeft,
        initialTop,
        initialWidth,
        initialHeight,
        dashboardWidth,
        dashboardHeight,
        WIDGET_MIN_SIZE
      )

      expect(topLeft).toEqual({ dx: -100, dy: -100 })

      const topRight = clampResizeDeltas(
        'top-right',
        800,
        -200,
        initialLeft,
        initialTop,
        initialWidth,
        initialHeight,
        dashboardWidth,
        dashboardHeight,
        WIDGET_MIN_SIZE
      )

      expect(topRight).toEqual({ dx: 700, dy: -100 })

      const bottomLeft = clampResizeDeltas(
        'bottom-left',
        -200,
        700,
        initialLeft,
        initialTop,
        initialWidth,
        initialHeight,
        dashboardWidth,
        dashboardHeight,
        WIDGET_MIN_SIZE
      )

      expect(bottomLeft).toEqual({ dx: -100, dy: 500 })

      const bottomRight = clampResizeDeltas(
        'bottom-right',
        800,
        700,
        initialLeft,
        initialTop,
        initialWidth,
        initialHeight,
        dashboardWidth,
        dashboardHeight,
        WIDGET_MIN_SIZE
      )

      expect(bottomRight).toEqual({ dx: 700, dy: 500 })
    })

    it('should enforce minimum size for compound directions', () => {
      const result = clampResizeDeltas(
        'top-left',
        200,
        200,
        initialLeft,
        initialTop,
        initialWidth,
        initialHeight,
        dashboardWidth,
        dashboardHeight,
        WIDGET_MIN_SIZE
      )

      expect(result).toEqual({ dx: 80, dy: 80 })
    })
  })

  describe('edge cases', () => {
    it('should handle zero deltas', () => {
      const result = clampResizeDeltas(
        'right',
        0,
        0,
        initialLeft,
        initialTop,
        initialWidth,
        initialHeight,
        dashboardWidth,
        dashboardHeight,
        WIDGET_MIN_SIZE
      )

      expect(result).toEqual({ dx: 0, dy: 0 })
    })

    it('should handle dashlet at origin', () => {
      const result = clampResizeDeltas(
        'top-left',
        -50,
        -50,
        0,
        0,
        200,
        200,
        dashboardWidth,
        dashboardHeight,
        WIDGET_MIN_SIZE
      )

      expect(result).toEqual({ dx: 0, dy: 0 })
    })

    it('should handle dashlet already at maximum boundary', () => {
      const result = clampResizeDeltas(
        'right',
        100,
        0,
        800,
        600,
        200,
        200,
        dashboardWidth,
        dashboardHeight,
        WIDGET_MIN_SIZE
      )

      expect(result.dx).toBe(0)
    })
  })
})
