/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  ANCHOR_POSITION,
  GROW,
  MAX,
  WIDGET_MIN_SIZE
} from '@/dashboard/components/RelativeGrid/types'
import {
  Vec,
  alignToGrid,
  calculateDashlets,
  convertAbsoluteToRelativePosition
} from '@/dashboard/components/RelativeGrid/utils'

import { STANDARD_DASHBOARD_DIMS } from './testHelpers'

// ─── Vec class ─────────────────────────────────────────────────────────────────

describe('Vec', () => {
  describe('constructor', () => {
    it('should create a vector with given x and y', () => {
      const v = new Vec(3, 7)

      expect(v.x).toBe(3)
      expect(v.y).toBe(7)
    })

    it('should treat null as 0', () => {
      const v = new Vec(null, null)

      expect(v.x).toBe(0)
      expect(v.y).toBe(0)
    })

    it('should treat mixed null values correctly', () => {
      const v = new Vec(5, null)

      expect(v.x).toBe(5)
      expect(v.y).toBe(0)
    })
  })

  describe('divide', () => {
    it('should perform integer division', () => {
      const v = new Vec(25, 37)

      const result = v.divide(10)

      expect(result.x).toBe(2)
      expect(result.y).toBe(3)
    })

    it('should truncate toward zero for positive values', () => {
      const v = new Vec(19, 9)

      const result = v.divide(10)

      expect(result.x).toBe(1)
      expect(result.y).toBe(0)
    })

    it('should truncate toward zero for negative values', () => {
      const v = new Vec(-25, -37)

      const result = v.divide(10)

      expect(result.x).toBe(-2)
      expect(result.y).toBe(-3)
    })
  })

  describe('add', () => {
    it('should add two vectors', () => {
      const v1 = new Vec(3, 5)
      const v2 = new Vec(7, 11)

      const result = v1.add(v2)

      expect(result.x).toBe(10)
      expect(result.y).toBe(16)
    })

    it('should handle negative values', () => {
      const v1 = new Vec(-3, 5)
      const v2 = new Vec(7, -11)

      const result = v1.add(v2)

      expect(result.x).toBe(4)
      expect(result.y).toBe(-6)
    })
  })

  describe('make_absolute', () => {
    it('should convert positive position to 0-based index', () => {
      const pos = new Vec(1, 1)
      const size = new Vec(100, 80)

      const result = pos.make_absolute(size)

      expect(result.x).toBe(0)
      expect(result.y).toBe(0)
    })

    it('should wrap negative position from the end', () => {
      const pos = new Vec(-1, -1)
      const size = new Vec(100, 80)

      const result = pos.make_absolute(size)

      expect(result.x).toBe(100)
      expect(result.y).toBe(80)
    })

    it('should handle mixed signs', () => {
      const pos = new Vec(5, -3)
      const size = new Vec(100, 80)

      const result = pos.make_absolute(size)

      expect(result.x).toBe(4)
      expect(result.y).toBe(78)
    })
  })

  describe('initial_size', () => {
    it('should return widget min size for GROW', () => {
      const size = new Vec(GROW, GROW)
      const pos = new Vec(1, 1)
      const grid = new Vec(100, 80)

      const result = size.initial_size(pos, grid, MAX, GROW, WIDGET_MIN_SIZE)

      expect(result.x).toBe(12)
      expect(result.y).toBe(12)
    })

    it('should compute remaining space for MAX', () => {
      const size = new Vec(MAX, MAX)
      const pos = new Vec(5, 10)
      const grid = new Vec(100, 80)

      const result = size.initial_size(pos, grid, MAX, GROW, WIDGET_MIN_SIZE)

      expect(result.x).toBe(96)
      expect(result.y).toBe(71)
    })

    it('should return the value as-is for MANUAL sizes', () => {
      const size = new Vec(20, 15)
      const pos = new Vec(1, 1)
      const grid = new Vec(100, 80)

      const result = size.initial_size(pos, grid, MAX, GROW, WIDGET_MIN_SIZE)

      expect(result.x).toBe(20)
      expect(result.y).toBe(15)
    })

    it('should handle MAX with negative position', () => {
      const size = new Vec(MAX, MAX)
      const pos = new Vec(-5, -10)
      const grid = new Vec(100, 80)

      const result = size.initial_size(pos, grid, MAX, GROW, WIDGET_MIN_SIZE)

      expect(result.x).toBe(96)
      expect(result.y).toBe(71)
    })
  })

  describe('compute_grow_by', () => {
    it('should return grow direction for GROW size with positive position', () => {
      const pos = new Vec(5, 10)
      const size = new Vec(GROW, GROW)

      const result = pos.compute_grow_by(size, GROW)

      expect(result.x).toBe(1)
      expect(result.y).toBe(1)
    })

    it('should return negative grow direction for GROW size with negative position', () => {
      const pos = new Vec(-5, -10)
      const size = new Vec(GROW, GROW)

      const result = pos.compute_grow_by(size, GROW)

      expect(result.x).toBe(-1)
      expect(result.y).toBe(-1)
    })

    it('should return 0 for non-GROW size', () => {
      const pos = new Vec(5, 10)
      const size = new Vec(20, 15)

      const result = pos.compute_grow_by(size, GROW)

      expect(result.x).toBe(0)
      expect(result.y).toBe(0)
    })

    it('should handle mixed GROW and non-GROW dimensions', () => {
      const pos = new Vec(5, -10)
      const size = new Vec(GROW, 15)

      const result = pos.compute_grow_by(size, GROW)

      expect(result.x).toBe(1)
      expect(result.y).toBe(0)
    })
  })
})

// ─── alignToGrid ──────────────────────────────────────────────────────────────

describe('alignToGrid', () => {
  it('should round down to nearest grid unit', () => {
    const result = alignToGrid(25)

    expect(result).toBe(20)
  })

  it('should keep exact grid multiples unchanged', () => {
    const result = alignToGrid(30)

    expect(result).toBe(30)
  })

  it('should return 0 for values less than GRID_SIZE', () => {
    const result = alignToGrid(9)

    expect(result).toBe(0)
  })

  it('should return 0 for 0', () => {
    const result = alignToGrid(0)

    expect(result).toBe(0)
  })
})

// ─── calculateDashlets ────────────────────────────────────────────────────────

describe('calculateDashlets', () => {
  it('should place a single dashlet at top-left', () => {
    const layouts = [{ position: { x: 1, y: 1 }, dimensions: { width: 20, height: 10 } }]

    const result = calculateDashlets(layouts, STANDARD_DASHBOARD_DIMS, WIDGET_MIN_SIZE)

    expect(result).toHaveLength(1)
    const [left, top, width, height] = result[0]!
    expect(left).toBe(0)
    expect(top).toBe(0)
    expect(width).toBe(200)
    expect(height).toBe(100)
  })

  it('should place a dashlet anchored from bottom-right', () => {
    const layouts = [{ position: { x: -1, y: -1 }, dimensions: { width: 20, height: 10 } }]

    const result = calculateDashlets(layouts, STANDARD_DASHBOARD_DIMS, WIDGET_MIN_SIZE)

    expect(result).toHaveLength(1)
    const [left, top, width, height] = result[0]!
    // raster: 100x80, absolute position: -1+100+1=100, -1+80+1=80
    // right=100, left=100-20=80; bottom=80, top=80-10=70
    expect(left).toBe(800)
    expect(top).toBe(700)
    expect(width).toBe(200)
    expect(height).toBe(100)
  })

  it('should expand MAX-sized dashlets to fill remaining space', () => {
    const layouts = [{ position: { x: 1, y: 1 }, dimensions: { width: MAX, height: MAX } }]

    const result = calculateDashlets(layouts, STANDARD_DASHBOARD_DIMS, WIDGET_MIN_SIZE)

    expect(result).toHaveLength(1)
    const [left, top, width, height] = result[0]!
    expect(left).toBe(0)
    expect(top).toBe(0)
    // MAX from position 1 in a 100-wide raster: 100 - 1 + 1 = 100 raster units
    expect(width).toBe(1000)
    expect(height).toBe(800)
  })

  it('should expand GROW dashlets into free space', () => {
    const layouts = [
      { position: { x: 1, y: 1 }, dimensions: { width: 50, height: 40 } },
      { position: { x: 51, y: 1 }, dimensions: { width: GROW, height: GROW } }
    ]

    const result = calculateDashlets(layouts, STANDARD_DASHBOARD_DIMS, WIDGET_MIN_SIZE)

    expect(result).toHaveLength(2)
    // Second dashlet starts at x=50 (0-based) and should grow to fill remaining space
    const [left2, top2, width2, height2] = result[1]!
    expect(left2).toBe(500)
    expect(top2).toBe(0)
    // Should grow rightward to fill remaining raster columns (100 - 50 = 50)
    expect(width2).toBe(500)
    // Should grow downward to fill remaining raster rows (80 - 0 = 80)
    expect(height2).toBe(800)
  })
})

// ─── convertAbsoluteToRelativePosition ────────────────────────────────────────

describe('convertAbsoluteToRelativePosition', () => {
  const dashboardDims = STANDARD_DASHBOARD_DIMS

  it('should convert TOP_LEFT anchor position', () => {
    const result = convertAbsoluteToRelativePosition(
      { x: 0, y: 0 },
      { width: 200, height: 100 },
      ANCHOR_POSITION.TOP_LEFT,
      dashboardDims
    )

    expect(result.x).toBe(1)
    expect(result.y).toBe(1)
  })

  it('should convert TOP_RIGHT anchor position', () => {
    const result = convertAbsoluteToRelativePosition(
      { x: 800, y: 0 },
      { width: 200, height: 100 },
      ANCHOR_POSITION.TOP_RIGHT,
      dashboardDims
    )

    expect(result.x).toBe(-1)
    expect(result.y).toBe(1)
  })

  it('should convert BOTTOM_RIGHT anchor position', () => {
    const result = convertAbsoluteToRelativePosition(
      { x: 800, y: 700 },
      { width: 200, height: 100 },
      ANCHOR_POSITION.BOTTOM_RIGHT,
      dashboardDims
    )

    expect(result.x).toBe(-1)
    expect(result.y).toBe(-1)
  })

  it('should convert BOTTOM_LEFT anchor position', () => {
    const result = convertAbsoluteToRelativePosition(
      { x: 0, y: 700 },
      { width: 200, height: 100 },
      ANCHOR_POSITION.BOTTOM_LEFT,
      dashboardDims
    )

    expect(result.x).toBe(1)
    expect(result.y).toBe(-1)
  })

  it('should align position to grid before conversion', () => {
    const result = convertAbsoluteToRelativePosition(
      { x: 13, y: 27 },
      { width: 200, height: 100 },
      ANCHOR_POSITION.TOP_LEFT,
      dashboardDims
    )

    // 13 -> alignToGrid = 10, /10 = 1; 27 -> alignToGrid = 20, /10 = 2
    expect(result.x).toBe(2)
    expect(result.y).toBe(3)
  })
})
