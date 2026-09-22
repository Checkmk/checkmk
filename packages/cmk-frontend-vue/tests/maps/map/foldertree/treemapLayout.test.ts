/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { layoutTreemap, tileSignature, visibleTiles } from '@/maps/map/foldertree/treemapLayout'
import type { FolderTreeNode } from '@/maps/types/api'

import { aFolderNode } from '../../support/fixtures'

/** A root folder holding two hosts and a subfolder of two more. */
function aTree(): FolderTreeNode {
  return aFolderNode({
    path: '/main',
    title: 'Main',
    kind: 'folder',
    children: [
      aFolderNode({ path: '/main/web-01', title: 'web-01', kind: 'host', state: 'UP' }),
      aFolderNode({ path: '/main/db-01', title: 'db-01', kind: 'host', state: 'DOWN' }),
      aFolderNode({
        path: '/main/os',
        title: 'Os hosts',
        kind: 'folder',
        children: [
          aFolderNode({ path: '/main/os/a', title: 'a', kind: 'host', state: 'UP' }),
          aFolderNode({ path: '/main/os/b', title: 'b', kind: 'host', state: 'UP' })
        ]
      })
    ]
  })
}

function tilesOn(width: number, height: number) {
  const laid = layoutTreemap({
    root: aTree(),
    width,
    height,
    isOpen: (node) => node.kind === 'folder',
    childrenOf: (node) => node.children
  })
  return visibleTiles(laid!)
}

const paths = (tiles: ReturnType<typeof tilesOn>) => tiles.map((tile) => tile.data.path)

describe('tileSignature', () => {
  it('is the same for a layout that came out identical, so it can be recoloured', () => {
    expect(tileSignature(tilesOn(800, 600))).toBe(tileSignature(tilesOn(800, 600)))
  })

  it('changes when the same tiles come back at different sizes', () => {
    const narrow = tilesOn(800, 600)
    const wide = tilesOn(900, 600)
    // The same tiles are on screen either way -- only their geometry moved,
    // which a recolour pass would not follow.
    expect(paths(wide)).toEqual(paths(narrow))

    expect(tileSignature(wide)).not.toBe(tileSignature(narrow))
  })
})
