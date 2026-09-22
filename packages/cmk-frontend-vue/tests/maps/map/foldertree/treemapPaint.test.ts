/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { select } from 'd3-selection'
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

import { type Tile, layoutTreemap, visibleTiles } from '@/maps/map/foldertree/treemapLayout'
import { drawTiles } from '@/maps/map/foldertree/treemapPaint'
import type { TileText } from '@/maps/map/foldertree/treemapText'
import type { FolderTreeNode } from '@/maps/types/api'

const STAGE = { width: 800, height: 600 }

/** Long enough for the layout transition to have finished. */
const AFTER_THE_ANIMATION_MS = 700

/** Long enough for an unanimated draw to have landed. */
const AFTER_THE_DRAW_MS = 100

function aNode(node: Partial<FolderTreeNode> & { path: string; kind: string }): FolderTreeNode {
  return {
    title: node.path,
    state: 'CRIT',
    is_empty: false,
    folder_id: '',
    host_count: 1,
    problem_count: 1,
    severity_counts: {},
    output: '',
    acknowledged: false,
    in_downtime: false,
    is_flapping: false,
    stale: false,
    site_id: null,
    children: [],
    ...node
  } as FolderTreeNode
}

/** A root folder holding two hosts and a subfolder of three more. */
function aTree(): FolderTreeNode {
  return aNode({
    path: '/main',
    title: 'Main',
    kind: 'folder',
    children: [
      aNode({ path: '/main/web-01', title: 'web-01', kind: 'host' }),
      aNode({ path: '/main/db-01', title: 'db-01', kind: 'host' }),
      aNode({
        path: '/main/os',
        title: 'Os hosts',
        kind: 'folder',
        children: [
          aNode({ path: '/main/os/a', title: 'a', kind: 'host' }),
          aNode({ path: '/main/os/b', title: 'b', kind: 'host' }),
          aNode({ path: '/main/os/c', title: 'c', kind: 'host' })
        ]
      })
    ]
  })
}

const text: TileText = {
  label: (tile) => tile.data.title,
  mark: () => '',
  aria: (tile) => tile.data.title,
  tooltip: (tile) => ({ title: tile.data.title, meta: '', color: 'red' })
}

const handlers = {
  activate: vi.fn(),
  context: vi.fn(),
  hover: vi.fn(),
  hoverEnd: vi.fn()
}

function tilesOf(openPaths: readonly string[]): Tile[] {
  const laid = layoutTreemap({
    root: aTree(),
    ...STAGE,
    isOpen: (node) => openPaths.includes(node.path),
    childrenOf: (node) => node.children
  })
  if (laid === null) {
    throw new Error('the fixture has to lay out')
  }
  return visibleTiles(laid)
}

function paint(svg: SVGSVGElement, tiles: readonly Tile[], animate: boolean): void {
  drawTiles(svg, tiles, { text, light: false, animate, ...STAGE, handlers })
}

/** Every drawn tile's body rect, by the path of the tile it belongs to. */
function drawnBodies(svg: SVGSVGElement): Record<string, { width: number; height: number }> {
  const drawn: Record<string, { width: number; height: number }> = {}
  svg.querySelectorAll('g.maps-folder-treemap__cell').forEach((cell, index) => {
    const body = cell.querySelector('rect.maps-folder-treemap__body')
    drawn[cell.getAttribute('aria-label') ?? `#${index}`] = {
      width: Number(body?.getAttribute('width') ?? -1),
      height: Number(body?.getAttribute('height') ?? -1)
    }
  })
  return drawn
}

function expectedBodies(tiles: readonly Tile[]): Record<string, { width: number; height: number }> {
  return Object.fromEntries(
    tiles.map((tile) => [tile.data.title, { width: tile.x1 - tile.x0, height: tile.y1 - tile.y0 }])
  )
}

describe('drawTiles — opening a folder', () => {
  let svg: SVGSVGElement

  beforeAll(() => {
    // jsdom implements no SVG geometry, so d3 throws where it parses a
    // transform through a probe element. Answering "no transform" is enough:
    // d3 falls back to interpolating straight to the target, and this case
    // reads the tiles' sizes rather than where they travelled.
    Object.defineProperty(SVGElement.prototype, 'transform', {
      configurable: true,
      get: () => ({ baseVal: { consolidate: () => null } })
    })
  })

  afterAll(() => {
    Reflect.deleteProperty(SVGElement.prototype, 'transform')
  })

  afterEach(() => {
    // Nothing of this case's animation may still be running when the next test
    // file takes over the timer.
    select(svg).selectAll('*').interrupt()
    svg.remove()
  })

  it('sizes every tile to its layout once the animation is over', async () => {
    svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
    document.body.appendChild(svg)

    // The stage draws once without animating, the way a first resize does it.
    // Even that goes through a zero-length transition, so it has to have
    // landed before the next pass -- otherwise the case is about two passes
    // racing rather than about the one under test.
    paint(svg, tilesOf(['/main']), false)
    await new Promise((resolve) => setTimeout(resolve, AFTER_THE_DRAW_MS))

    // Then the operator opens the subfolder, which animates.
    const opened = tilesOf(['/main', '/main/os'])
    paint(svg, opened, true)
    await new Promise((resolve) => setTimeout(resolve, AFTER_THE_ANIMATION_MS))

    // The freshly opened folder's hosts must be drawn at their animated size,
    // not just labelled.
    expect(drawnBodies(svg)).toEqual(expectedBodies(opened))
  })
})
