/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Drawing the treemap's tiles.
 *
 * D3 owns the tiles' DOM: a site's folder tree can lay out into thousands of
 * them, and they animate between layouts, which is what a data join and a
 * transition are for. Vue owns the frame around them.
 *
 * The two passes are named transitions, deliberately. A live state tick arriving
 * mid-animation must recolour without cancelling a geometry transition that is
 * still running -- an unnamed clash froze freshly opened tiles at zero width.
 *
 * For the same reason each element gets exactly ONE transition per pass, and it
 * carries everything that pass animates. Two transitions of the same name on
 * one node interrupt each other, whichever is scheduled second winning: sizing
 * the tiles in one and tinting them in another froze every freshly opened tile
 * at zero size again, with its label already sitting where the tile should have
 * been.
 */
import { type BaseType, type Selection, select } from 'd3-selection'
// Imported for its side effect: this is what puts .transition() on a selection,
// and nothing here would otherwise pull it into the bundle.
import 'd3-transition'

import { HEADER_HEIGHT, type Tile } from './treemapLayout'
import {
  fitLabel,
  headerFillOpacity,
  isContainer,
  tileFill,
  tileFillOpacity,
  tileStroke,
  tileStrokeWidth
} from './treemapStyle'
import type { TileText } from './treemapText'

/** How long a relayout, and a recolour, take. */
const LAYOUT_MS = 450
const RECOLOR_MS = 400

const treemapClass = {
  cells: 'maps-folder-treemap__cells',
  cell: 'maps-folder-treemap__cell',
  body: 'maps-folder-treemap__body',
  header: 'maps-folder-treemap__header',
  label: 'maps-folder-treemap__label',
  mark: 'maps-folder-treemap__mark'
} as const

interface TileHandlers {
  activate: (tile: Tile) => void
  /** A right-click that asks for the folder's own menu. */
  context: (tile: Tile, x: number, y: number) => void
  hover: (event: MouseEvent, tile: Tile) => void
  hoverEnd: () => void
}

export interface PaintOptions {
  text: TileText
  /** Whether the stage is a light one, which the tints have to allow for. */
  light: boolean
}

type Cells = Selection<SVGGElement, Tile, BaseType, unknown>

const tileKey = (tile: Tile): string => `${tile.data.path}:${tile.data.kind}`

function cellsOf(svg: SVGSVGElement, tiles: readonly Tile[]): Cells {
  return select(svg)
    .select(`g.${treemapClass.cells}`)
    .selectAll<SVGGElement, Tile>(`g.${treemapClass.cell}`)
    .data(tiles as Tile[], tileKey)
}

const tileWidth = (tile: Tile): number => Math.max(0, tile.x1 - tile.x0)
const tileHeight = (tile: Tile): number => Math.max(0, tile.y1 - tile.y0)

/**
 * The tints, the labels and the markers -- everything a tile says about the
 * state it is in, which both passes have to write -- and, on a layout pass, the
 * sizes the tiles animate to. One transition per element, so the two cannot
 * interrupt each other.
 */
function paintCells(
  cells: Cells,
  options: PaintOptions,
  transition: string,
  duration: number,
  /** Whether the tiles are moving, which only a layout pass does. */
  relayout: boolean
): void {
  const body = cells
    .select(`rect.${treemapClass.body}`)
    // Fill and stroke go through `style` so the shared `var(--color-state-*)`
    // tokens resolve; an SVG presentation attribute cannot resolve them.
    .style('fill', tileFill)
    .style('stroke', tileStroke)
    .transition(transition)
    .duration(duration)
    .attr('fill-opacity', (tile) => tileFillOpacity(tile, options.light))
  if (relayout) {
    body.attr('width', tileWidth).attr('height', tileHeight)
  }

  const header = cells
    .select(`rect.${treemapClass.header}`)
    .style('fill', tileFill)
    .transition(transition)
    .duration(duration)
    .attr('fill-opacity', headerFillOpacity)
  if (relayout) {
    header
      .attr('width', tileWidth)
      .attr('height', (tile) => Math.min(HEADER_HEIGHT, tileHeight(tile)))
  }

  paintLabels(cells, options.text)
}

/** Labels and markers, on both passes: a recolour must not clobber the marker
 *  text, drop a truncated label, or leave a stale spoken label behind. */
function paintLabels(cells: Cells, text: TileText): void {
  cells.attr('aria-label', (tile) => text.aria(tile))
  cells.select<SVGTextElement>(`text.${treemapClass.label}`).each(function (tile) {
    const width = tile.x1 - tile.x0
    const height = tile.y1 - tile.y0
    const label = select(this).text(fitLabel(text.label(tile), width))
    if (isContainer(tile)) {
      // In the title bar, next to the chevron.
      label
        .attr('x', 6)
        .attr('y', 13)
        .attr('text-anchor', 'start')
        .style('display', width > 30 ? 'inline' : 'none')
      return
    }
    // A chip's label is centred and clipped to the tile; the full name is in
    // the tooltip.
    label
      .attr('x', width / 2)
      .attr('y', height / 2 + 4)
      .attr('text-anchor', 'middle')
      .style('display', width > 34 && height > 18 ? 'inline' : 'none')
  })
  cells.select<SVGTextElement>(`text.${treemapClass.mark}`).each(function (tile) {
    const width = tile.x1 - tile.x0
    const height = tile.y1 - tile.y0
    const marks = text.mark(tile.data)
    select(this)
      .text(marks)
      .attr('x', width - 4)
      .attr('y', 13)
      .attr('text-anchor', 'end')
      .style('display', marks && width > 28 && height > 16 ? 'inline' : 'none')
  })
}

/** Lay the tiles out, animating from wherever they were. */
export function drawTiles(
  svg: SVGSVGElement,
  tiles: readonly Tile[],
  options: PaintOptions & {
    animate: boolean
    width: number
    height: number
    handlers: TileHandlers
  }
): void {
  const { animate, width, height, handlers } = options
  const root = select(svg).attr('viewBox', `0 0 ${width} ${height}`)
  if (root.select(`g.${treemapClass.cells}`).empty()) {
    root.append('g').attr('class', treemapClass.cells)
  }

  const duration = animate ? LAYOUT_MS : 0
  const cells = cellsOf(svg, tiles)

  cells.exit().transition('layout').duration(duration).style('opacity', 0).remove()

  const entered = cells
    .enter()
    .append('g')
    .attr('class', treemapClass.cell)
    .style('opacity', 0)
    .attr('transform', (tile) => `translate(${tile.x0},${tile.y0})`)
  entered.append('rect').attr('class', treemapClass.body)
  entered.append('rect').attr('class', treemapClass.header)
  entered.append('text').attr('class', treemapClass.label)
  entered.append('text').attr('class', treemapClass.mark)

  const merged = entered.merge(cells)
  merged
    .style('cursor', 'pointer')
    // Keyboard-operable: the map can be a folder tree's default view, so a tile
    // is a focusable button with a spoken label that Enter and Space activate.
    // The list already carries the ARIA tree roles.
    .attr('tabindex', 0)
    .attr('role', 'button')
    .on('click', (event: MouseEvent, tile) => {
      event.stopPropagation()
      handlers.activate(tile)
    })
    .on('keydown', (event: KeyboardEvent, tile) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault()
        event.stopPropagation()
        handlers.activate(tile)
      }
    })
    .on('contextmenu', (event: MouseEvent, tile) => {
      event.preventDefault()
      event.stopPropagation()
      handlers.context(tile, event.clientX, event.clientY)
    })
    .on('mousemove', handlers.hover)
    .on('mouseleave', handlers.hoverEnd)
  merged
    .transition('layout')
    .duration(duration)
    .style('opacity', 1)
    .attr('transform', (tile) => `translate(${tile.x0},${tile.y0})`)

  merged
    .select(`rect.${treemapClass.body}`)
    .attr('rx', 3)
    .attr('stroke-width', tileStrokeWidth)
    .attr('stroke-dasharray', (tile) =>
      tile.data.kind === 'folder' && tile.data.is_empty ? '4 3' : null
    )

  merged
    .select(`rect.${treemapClass.header}`)
    .attr('rx', 3)
    .style('display', (tile) => (isContainer(tile) ? null : 'none'))

  paintCells(merged, options, 'layout', duration, true)
}

/** Repaint the same tiles because only their states changed. The freshly laid
 *  tiles are rebound under the same keys, so a filtered tree -- whose root is a
 *  pruned copy -- recolours off the current data rather than the last draw's. */
export function recolorTiles(
  svg: SVGSVGElement,
  tiles: readonly Tile[],
  options: PaintOptions
): void {
  paintCells(cellsOf(svg, tiles), options, 'recolor', RECOLOR_MS, false)
}
