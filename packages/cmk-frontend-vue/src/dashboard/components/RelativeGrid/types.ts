/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
export const MAX = -1
export const GROW = 0
export const GRID_SIZE = 10 // Raster the dashlet coords are measured in (px)
export const WIDGET_MIN_SIZE: [number, number] = [12, 12] // TODO: potentially make this load from backend
export const DASHLET_PADDING: [number, number, number, number, number] = [26, 4, 4, 4, 4] // Margin (N, E, S, W, N w/o title) between outer border of dashlet and its content

export const SIZING_MODE = {
  MAX: 'max',
  GROW: 'grow',
  MANUAL: 'manual'
} as const

// eslint-disable-next-line @typescript-eslint/naming-convention
export type SIZING_MODE = (typeof SIZING_MODE)[keyof typeof SIZING_MODE]

export const ANCHOR_POSITION = {
  TOP_LEFT: 'top-left',
  TOP_RIGHT: 'top-right',
  BOTTOM_LEFT: 'bottom-left',
  BOTTOM_RIGHT: 'bottom-right',

  determine: (position: Position) => {
    if (position.x > 0 && position.y > 0) {
      return ANCHOR_POSITION.TOP_LEFT
    }
    if (position.x <= 0 && position.y > 0) {
      return ANCHOR_POSITION.TOP_RIGHT
    }
    if (position.x <= 0 && position.y <= 0) {
      return ANCHOR_POSITION.BOTTOM_RIGHT
    }

    return ANCHOR_POSITION.BOTTOM_LEFT
  }
} as const

// eslint-disable-next-line @typescript-eslint/naming-convention
export type ANCHOR_POSITION = (typeof ANCHOR_POSITION)[keyof typeof ANCHOR_POSITION]

export interface Position {
  x: number
  y: number
}

export interface AbsolutePosition {
  left: number
  top: number
}

export interface AbsoluteDimensions {
  width: number
  height: number
}

export interface Dimensions {
  width: number
  height: number
}

export interface AbsoluteLayout {
  frame: {
    position: AbsolutePosition
    dimensions: AbsoluteDimensions
  }
  content: {
    position: AbsolutePosition
    dimensions: AbsoluteDimensions
  }
}

export interface RelativeLayout {
  position: Position
  dimensions: Dimensions
}

export interface DimensionModes {
  width: SIZING_MODE
  height: SIZING_MODE
}

export interface AbsoluteWidgetLayout {
  anchorPosition: ANCHOR_POSITION
  layout: AbsoluteLayout
  dimensionModes: DimensionModes
}
