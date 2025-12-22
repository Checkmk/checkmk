/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Dashboard Layout Utilities
 * PORTED from legacy dashboard layout calculation logic (not newly invented)
 *
 * Notes:
 *  - The logic is ported from legacy JavaScript absolute layout code
 *  - The legacy code had some quirks and assumptions that are preserved here for compatibility
 *  - The legacy layout size (width, height) and position (x, y) contain all the information (yes incl. anchor position
 *  as well the sizing mode) --> that's why we introduced a new layout (in the long term the relative layout should
 *  be removed)
 *
 *  - Edit Controls:
 *    - information legacy function: set_control_size
 *      - the position and dimensions of the edit box element were set manually and are therefore part of the resize &
 *      drag calculation
 *      - the width and height calculation take into calculation padding --> hence we cannot use normal padding styling
 *      as this would falsify the resize & drag calculation
 *      - the correct way would be to set a padding on the outer frame which is enabled during edit mode since the paddings
 *      are static
 *
 */
import {
  ANCHOR_POSITION,
  type AbsoluteDimensions,
  type AbsoluteLayout,
  DASHLET_PADDING,
  GRID_SIZE,
  GROW,
  MAX,
  type Position,
  type RelativeLayout
} from './types.ts'

/**
 * Vector class for layout calculations
 * Handles 2D positioning and sizing operations
 */
export class Vec {
  x: number
  y: number

  constructor(x: number | null, y: number | null) {
    this.x = x || 0
    this.y = y || 0
  }

  divide(s: number): Vec {
    return new Vec(~~(this.x / s), ~~(this.y / s))
  }

  add(v: Vec): Vec {
    return new Vec(this.x + v.x, this.y + v.y)
  }

  make_absolute(sizeVector: Vec): Vec {
    return new Vec(
      this.x < 0 ? this.x + sizeVector.x + 1 : this.x - 1,
      this.y < 0 ? this.y + sizeVector.y + 1 : this.y - 1
    )
  }

  initial_size(
    positionVector: Vec,
    gridVector: Vec,
    MAX: number,
    GROW: number,
    widgetMinSize: [number, number]
  ): Vec {
    return new Vec(
      this.x === MAX
        ? gridVector.x - Math.abs(positionVector.x) + 1
        : this.x === GROW
          ? widgetMinSize[0]
          : this.x,
      this.y === MAX
        ? gridVector.y - Math.abs(positionVector.y) + 1
        : this.y === GROW
          ? widgetMinSize[1]
          : this.y
    )
  }

  compute_grow_by(size: Vec, GROW: number): Vec {
    return new Vec(
      size.x !== GROW ? 0 : this.x < 0 ? -1 : 1,
      size.y !== GROW ? 0 : this.y < 0 ? -1 : 1
    )
  }

  toString(): string {
    return `${this.x}/${this.y}`
  }
}

/**
 * Calculate the layout positions for all dashlets
 * Handles dynamic sizing, collision detection, and growth algorithms
 * Ported from legacy dashboard.ts file (without any logic modifications)
 */
export function calculateDashlets(
  dashletsLayout: RelativeLayout[],
  dashboardDimensions: AbsoluteDimensions,
  minDashletSize: [number, number]
): number[][] {
  const screenSize = new Vec(dashboardDimensions.width, dashboardDimensions.height)
  const rasterSize = screenSize.divide(GRID_SIZE)
  const usedMatrix: Record<string, boolean> = {}
  let positions: [number, number, number, number, Vec][] = []

  // First place all dashlets at their absolute positions
  let nr: number, top: number, left: number, right: number, bottom: number, growBy: Vec

  for (nr = 0; nr < dashletsLayout.length; nr++) {
    const layout = dashletsLayout[nr]!

    // Relative position is as noted in the declaration. 1,1 => top left origin,
    // -1,-1 => bottom right origin, 0 is not allowed here
    // starting from 1, negative means: from right/bottom
    const relativePosition = new Vec(layout.position.x, layout.position.y)

    // Compute the absolute position, this time from 0 to rasterSize - 1
    const absolutePosition = relativePosition.make_absolute(rasterSize)

    // The size in raster-elements. A 0 for a dimension means growth. No negative values here.
    const size = new Vec(layout.dimensions.width, layout.dimensions.height)

    // Compute the minimum used size for the dashlet. For growth-dimensions we start with 1
    const usedSize = size.initial_size(relativePosition, rasterSize, MAX, GROW, minDashletSize)

    // Now compute the rectangle that is currently occupied. The coords
    // of bottomright are *not* included.
    if (relativePosition.x > 0) {
      left = absolutePosition.x
      right = left + usedSize.x
    } else {
      right = absolutePosition.x
      left = right - usedSize.x
    }

    if (relativePosition.y > 0) {
      top = absolutePosition.y
      bottom = top + usedSize.y
    } else {
      bottom = absolutePosition.y
      top = bottom - usedSize.y
    }

    // Allocate used squares in matrix. If not all squares we need are free,
    // then the dashboard is too small for all dashlets (as it seems).
    for (let x = left; x < right; x++) {
      for (let y = top; y < bottom; y++) {
        usedMatrix[`${x} ${y}`] = true
      }
    }

    // Helper variable for how to grow, both x and y in [-1, 0, 1]
    growBy = relativePosition.compute_grow_by(size, GROW)
    positions.push([left, top, right, bottom, growBy])
  }

  const tryAllocate = function (left: number, top: number, right: number, bottom: number): boolean {
    let x, y
    // Try if all needed squares are free
    for (x = left; x < right; x++) {
      for (y = top; y < bottom; y++) {
        const key = `${x} ${y}`
        if (key in usedMatrix) {
          return false
        }
      }
    }

    // Allocate all needed squares
    for (x = left; x < right; x++) {
      for (y = top; y < bottom; y++) {
        usedMatrix[`${x} ${y}`] = true
      }
    }
    return true
  }

  // Now try to expand all elastic rectangles as far as possible
  let atLeastOneExpanded = true
  while (atLeastOneExpanded) {
    atLeastOneExpanded = false
    const newPositions: [number, number, number, number, Vec][] = []

    for (nr = 0; nr < positions.length; nr++) {
      // legacy...
      left = positions[nr]![0]!
      top = positions[nr]![1]!
      right = positions[nr]![2]!
      bottom = positions[nr]![3]!
      growBy = positions[nr]![4]!

      // try to grow in X direction by one
      if (growBy.x > 0 && right < rasterSize.x && tryAllocate(right, top, right + 1, bottom)) {
        atLeastOneExpanded = true
        right += 1
      } else if (growBy.x < 0 && left > 0 && tryAllocate(left - 1, top, left, bottom)) {
        atLeastOneExpanded = true
        left -= 1
      }

      // try to grow in Y direction by one
      if (growBy.y > 0 && bottom < rasterSize.y && tryAllocate(left, bottom, right, bottom + 1)) {
        atLeastOneExpanded = true
        bottom += 1
      } else if (growBy.y < 0 && top > 0 && tryAllocate(left, top - 1, right, top)) {
        atLeastOneExpanded = true
        top -= 1
      }
      newPositions.push([left, top, right, bottom, growBy])
    }
    positions = newPositions
  }

  const sizeInfo: number[][] = []
  for (nr = 0; nr < positions.length; nr++) {
    // legacy...
    left = positions[nr]![0]
    top = positions[nr]![1]
    right = positions[nr]![2]
    bottom = positions[nr]![3]
    sizeInfo.push([
      left * GRID_SIZE,
      top * GRID_SIZE,
      (right - left) * GRID_SIZE,
      (bottom - top) * GRID_SIZE
    ])
  }
  return sizeInfo
}

export function calculateAbsoluteLayouts(
  dashletsLayouts: RelativeLayout[],
  dashboardDimensions: { width: number; height: number },
  layoutMinSize: [number, number],
  dashlets: Array<{ hasTitle: boolean }>
): AbsoluteLayout[] {
  const sizeInfo = calculateDashlets(dashletsLayouts, dashboardDimensions, layoutMinSize)

  const layouts: AbsoluteLayout[] = []

  for (let i = 0; i < sizeInfo.length; i++) {
    const dashlet = dashlets[i]!
    const dashletSize: number[] = sizeInfo[i]!
    const dashletLeft = dashletSize[0]!
    const dashletTop = dashletSize[1]!
    const dashletWidth = dashletSize[2]!
    const dashletHeight = dashletSize[3]!

    const calculated = calculateSingleDashletDimensions(
      dashletWidth,
      dashletHeight,
      DASHLET_PADDING,
      dashlet.hasTitle
    )

    layouts.push({
      frame: {
        position: {
          left: dashletLeft,
          top: dashletTop
        },
        dimensions: {
          width: calculated.adjustedOuterWidth,
          height: dashletHeight
        }
      },
      content: {
        position: {
          left: calculated.inner.left,
          top: calculated.inner.top
        },
        dimensions: {
          width: calculated.inner.width,
          height: calculated.inner.height
        }
      }
    })
  }

  return layouts
}

export function calculateSingleDashletDimensions(
  outerWidth: number,
  outerHeight: number,
  widgetPadding: [number, number, number, number, number],
  hasTitle: boolean = false
): {
  inner: {
    left: number
    top: number
    width: number
    height: number
  }
  titleWidth: number
  adjustedOuterWidth: number
} {
  let adjustedWidth = outerWidth
  let titleWidth = 0

  if (hasTitle) {
    // If browser window too small prevent js error
    if (adjustedWidth <= 20) {
      adjustedWidth = 21
    }
    titleWidth = adjustedWidth - 17 // 9 title padding + empty space on right of dashlet
  }

  let topPadding = widgetPadding[0]
  if (!hasTitle) {
    topPadding = widgetPadding[4]
  }

  const nettoHeight = outerHeight - topPadding - widgetPadding[2]
  const nettoWidth = adjustedWidth - widgetPadding[1] - widgetPadding[3]

  return {
    inner: {
      left: widgetPadding[3],
      top: topPadding,
      width: Math.max(0, nettoWidth),
      height: Math.max(0, nettoHeight)
    },
    titleWidth: titleWidth,
    adjustedOuterWidth: adjustedWidth
  }
}

/**
 * Utility to get page dimensions
 */
export function getPageDimensions() {
  return {
    width: window.innerWidth || document.documentElement.clientWidth || document.body.clientWidth,
    height:
      window.innerHeight || document.documentElement.clientHeight || document.body.clientHeight
  }
}

/**
 * Calculate dashboard container dimensions based on element positioning
 */
export function calculateDashboardDimensions(dashboardElement: HTMLElement): AbsoluteDimensions {
  const dashboardRect = dashboardElement.getBoundingClientRect()
  const oContainer = dashboardElement.parentElement
  const containerPaddingRight = oContainer
    ? parseInt(window.getComputedStyle(oContainer).paddingRight, 10)
    : 0

  const pageDims = getPageDimensions()

  return {
    width: pageDims.width - dashboardRect.left - containerPaddingRight,
    // For some reason a cache removing reload on Firefox breaks this height calculation by 1px.
    // Thus the '- 1' hack here, so the dashboard does not overflow and no scrollbar is needed.
    height: pageDims.height - dashboardRect.top - 1
  }
}

export const alignToGrid = (pixels: number): number => {
  return ~~(pixels / GRID_SIZE) * GRID_SIZE
}

/**
 * Converts pixel position and dimensions to normalized position
 * taking into account the anchor position.
 * @param position
 * @param dimensions
 * @param anchorPosition
 * @param dashboardDimensions
 */
export const convertAbsoluteToRelativePosition = (
  position: Position,
  dimensions: AbsoluteDimensions,
  anchorPosition: ANCHOR_POSITION,
  dashboardDimensions: AbsoluteDimensions
): Position => {
  let x = alignToGrid(position.x) / GRID_SIZE
  let y = alignToGrid(position.y) / GRID_SIZE
  const width = alignToGrid(dimensions.width) / GRID_SIZE
  const height = alignToGrid(dimensions.height) / GRID_SIZE

  const screenSize = new Vec(dashboardDimensions.width, dashboardDimensions.height)
  const rasterSize = screenSize.divide(GRID_SIZE)

  if (anchorPosition === ANCHOR_POSITION.TOP_RIGHT) {
    x = x + width - (rasterSize.x + 2)
  } else if (anchorPosition === ANCHOR_POSITION.BOTTOM_RIGHT) {
    x = x + width - (rasterSize.x + 2)
    y = y + height - (rasterSize.y + 2)
  } else if (anchorPosition === ANCHOR_POSITION.BOTTOM_LEFT) {
    y = y + height - (rasterSize.y + 2)
  }

  return {
    x: x + 1,
    y: y + 1
  }
}
