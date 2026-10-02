/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SiteOverviewContent, StatsPart } from '@/dashboard/types/widget'

export interface Point {
  x: number
  y: number
}

export interface HexagonGrid {
  columns: number
  radius: number
  boxWidth: number
  boxHeight: number
  centers: Point[]
  labelHeight: number | null
}

export interface HexagonGridOptions {
  layout: 'hosts' | 'sites'
  maxBoxWidth: number
}

export interface HexagonStyle {
  color: string
  fillOpacity: number
  strokeOpacity: number
}

interface Area {
  left: number
  top: number
  width: number
  height: number
}

/** The legacy colours of the nested state hexagons of the statistics and the site overview. */
export const STATE_HEXAGON_STYLE: Record<StatsPart['category'], HexagonStyle> = {
  up: { color: 'var(--success)', fillOpacity: 0.06, strokeOpacity: 0.9 },
  ok: { color: 'var(--success)', fillOpacity: 0.06, strokeOpacity: 0.9 },
  downtime: { color: 'var(--color-light-blue-50)', fillOpacity: 0.6, strokeOpacity: 1 },
  unreachable: { color: 'var(--color-orange-50)', fillOpacity: 0.8, strokeOpacity: 1 },
  down: { color: 'var(--color-dark-red-50)', fillOpacity: 0.8, strokeOpacity: 1 },
  host_down: { color: 'var(--color-dark-blue-50)', fillOpacity: 0.5, strokeOpacity: 1 },
  warning: { color: 'var(--color-yellow-50)', fillOpacity: 0.6, strokeOpacity: 1 },
  unknown: { color: 'var(--color-orange-50)', fillOpacity: 0.8, strokeOpacity: 1 },
  critical: { color: 'var(--color-dark-red-50)', fillOpacity: 0.8, strokeOpacity: 1 }
}

/** The largest box of a hexagon grid, by the hexagon size that a widget configures. */
export const HEXAGON_MAX_BOX_WIDTH: Record<SiteOverviewContent['hexagon_size'], number> = {
  default: 96,
  large: 400
}

// The legacy figures size the rings by an exponent of 0.33, not by an exact cube root.
const RING_EXPONENT = 0.33

const AREA_H_PADDING = 4
const AREA_V_PADDING = 10

const SITE_MIN_AREA = 20
const SITE_MAX_COLUMNS = 100
const SITE_H_REL_PADDING = 0.2
const SITE_V_REL_PADDING = 0.05
const SITE_MIN_LABEL_HEIGHT = 12
const SITE_LABEL_V_PADDING = 8
const SITE_MIN_LABEL_WIDTH = 60

/** The SVG path of a pointy-top hexagon centred on the given point, the origin by default. */
export function hexagonPath(radius: number, center: Point = { x: 0, y: 0 }): string {
  const corners = Array.from({ length: 6 }, (_, index) => {
    const angle = (index * Math.PI) / 3
    return `${round(center.x + Math.sin(angle) * radius)},${round(center.y - Math.cos(angle) * radius)}`
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

/** The layout of `count` hexagons in a box; null when the box has no room. */
export function hexagonGrid(
  count: number,
  width: number,
  height: number,
  options: HexagonGridOptions
): HexagonGrid | null {
  if (!Number.isFinite(width) || !Number.isFinite(height)) {
    return null
  }
  const area = {
    left: AREA_H_PADDING,
    top: AREA_V_PADDING,
    width: Math.max(width - 2 * AREA_H_PADDING, 0),
    height: Math.max(height - 2 * AREA_V_PADDING, 0)
  }
  return options.layout === 'hosts'
    ? hostGrid(count, area, options.maxBoxWidth)
    : siteGrid(count, area, options.maxBoxWidth)
}

function hostGrid(count: number, area: Area, maxBoxWidth: number): HexagonGrid | null {
  if (area.height <= 0) {
    return null
  }
  let columns = Math.max(Math.floor(area.width / maxBoxWidth), 1)
  for (;;) {
    const boxWidth = count >= columns * 2 ? area.width / (columns + 0.5) : area.width / columns
    const rows = Math.ceil(count / columns)
    const boxHeight = (boxWidth * Math.sqrt(3)) / 2
    if (boxHeight * (rows + 1 / 3) <= area.height) {
      const hexagonHeight = (boxHeight * 4) / 3
      return {
        columns,
        radius: ((boxHeight * 2) / 3) * 0.87,
        boxWidth,
        boxHeight,
        centers: Array.from({ length: count }, (_, index) => {
          const row = Math.floor(index / columns)
          const shift = row % 2 === 1 ? boxWidth / 2 : 0
          return {
            x: ((index % columns) + 0.5) * boxWidth + shift + area.left,
            y: row * boxHeight + hexagonHeight / 2 + area.top
          }
        }),
        labelHeight: null
      }
    }
    columns += 1
  }
}

function siteGrid(count: number, area: Area, maxBoxWidth: number): HexagonGrid | null {
  if (area.width < SITE_MIN_AREA || area.height < SITE_MIN_AREA) {
    return null
  }
  const maxRadius = maxBoxWidth / 2
  for (
    let columns = Math.max(Math.floor(area.width / maxBoxWidth), 1);
    columns < SITE_MAX_COLUMNS;
    columns++
  ) {
    const rows = Math.ceil(count / columns)
    const radius = Math.min(area.width / columns / 2, maxRadius) * (1 - SITE_H_REL_PADDING)
    const labelHeight = Math.floor(Math.max(radius / 5, SITE_MIN_LABEL_HEIGHT))
    const showLabel = area.width / columns >= SITE_MIN_LABEL_WIDTH
    const neededHeight =
      radius * 2 * (1 + SITE_V_REL_PADDING) +
      (showLabel ? SITE_LABEL_V_PADDING * 2 + labelHeight : 0)
    if (neededHeight * rows > area.height) {
      continue
    }
    const boxHeight = area.height / rows
    const centerTop = radius * (1 + SITE_V_REL_PADDING) + (boxHeight - neededHeight) / 2
    const balancedColumns = Math.ceil(count / rows)
    const boxWidth = area.width / balancedColumns
    return {
      columns: balancedColumns,
      radius,
      boxWidth,
      boxHeight,
      centers: Array.from({ length: count }, (_, index) => ({
        x: (index % balancedColumns) * boxWidth + boxWidth / 2 + area.left,
        y: Math.floor(index / balancedColumns) * boxHeight + centerTop + area.top
      })),
      labelHeight: showLabel ? labelHeight : null
    }
  }
  return null
}

/** The index of the host box under a point of a host grid; null outside every box. */
export function hostIndexAt(grid: HexagonGrid, x: number, y: number): number | null {
  const origin = grid.centers[0]
  if (origin === undefined) {
    return null
  }
  const row = Math.round((y - origin.y) / grid.boxHeight)
  const shift = row % 2 === 1 ? grid.boxWidth / 2 : 0
  const column = Math.round((x - origin.x - shift) / grid.boxWidth)
  if (row < 0 || column < 0 || column >= grid.columns) {
    return null
  }
  const index = row * grid.columns + column
  return index < grid.centers.length ? index : null
}

function round(value: number): number {
  return Math.round(value * 1000) / 1000
}
