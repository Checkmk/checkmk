/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Where the treemap's tiles go.
 *
 * The tree is squarified into the stage: folders become framed cards that hold
 * their contents, hosts and services become chips. Two things keep that
 * readable on a site of any size. Problems are laid out first, so the top left
 * of the map is where an operator looks. And a folder's healthy hosts are
 * bundled into one "all OK" tile, so a hundred green chips cannot bury the one
 * red one.
 */
import { type HierarchyRectangularNode, hierarchy, treemap, treemapSquarify } from 'd3-hierarchy'

import type { FolderTreeNode } from '@/maps/types/api'
import { isProblemState } from '@/maps/utils/problemState'
import { stateRank } from '@/maps/utils/stateColors'

import {
  type FolderQuery,
  isFilterActive,
  selfMatches,
  serviceVisible,
  subtreeVisible
} from './filter'

/**
 * A laid-out tile. `culled` marks an open container whose children all came out
 * too small to resolve, so it is drawn as a single aggregate tile instead.
 */
export type Tile = HierarchyRectangularNode<FolderTreeNode> & { culled?: boolean }

/** Height of an expanded container's title bar. */
export const HEADER_HEIGHT = 19

// Below this (px, either side) a tile is neither legible nor clickable, so
// neither it nor its subtree is bound into the DOM -- which caps the number of
// SVG nodes at what the stage can show, not at the host count.
const MIN_RESOLVE = 24

const OK_GROUP_SUFFIX = '::ok-group'

/**
 * The tree with everything the filter hides cut out of it. A host also survives
 * when one of its already-loaded services matches, so a service search still
 * surfaces the host to drill into -- lazily loaded leaves are not in the tree
 * the state stream sends.
 */
function pruneTree(
  node: FolderTreeNode,
  query: FolderQuery,
  servicesOf: (host: FolderTreeNode) => readonly FolderTreeNode[],
  ancestorMatched: boolean
): FolderTreeNode | null {
  const selfMatch = ancestorMatched || selfMatches(node, query.terms)
  if (node.kind !== 'folder') {
    if (subtreeVisible(node, query, ancestorMatched)) {
      return node
    }
    const bySer = (service: FolderTreeNode) => serviceVisible(node.title, service, query, selfMatch)
    if (node.kind === 'host' && servicesOf(node).some(bySer)) {
      return node
    }
    return null
  }
  const kept = node.children
    .map((child) => pruneTree(child, query, servicesOf, selfMatch))
    .filter((child): child is FolderTreeNode => child !== null)
  if (kept.length) {
    return { ...node, children: kept }
  }
  // Nothing under it survived, so the only way the folder itself still shows is
  // on its own name -- no need to walk the subtree again to be told the same.
  return selfMatch && !query.problemsOnly && node.children.length === 0
    ? { ...node, children: [] }
    : null
}

/** The root the treemap draws: the whole tree, or what the filter leaves of it. */
export function filteredRoot(
  root: FolderTreeNode,
  query: FolderQuery,
  servicesOf: (host: FolderTreeNode) => readonly FolderTreeNode[]
): FolderTreeNode {
  if (!isFilterActive(query)) {
    return root
  }
  return pruneTree(root, query, servicesOf, false) ?? { ...root, children: [] }
}

/**
 * The real folder a drawn tile stands for, looked up in the unfiltered tree.
 *
 * `filteredRoot` hands the layout copies whose children are only what survived
 * the filter, so anything that acts on a whole folder -- rather than on what is
 * drawn of it -- has to come back here for the node the list would have handed
 * it.
 */
export function folderAtPath(root: FolderTreeNode, path: string): FolderTreeNode | null {
  if (root.path === path) {
    return root
  }
  for (const child of root.children) {
    const found = child.kind === 'folder' ? folderAtPath(child, path) : null
    if (found) {
      return found
    }
  }
  return null
}

/**
 * A folder's children with its healthy hosts bundled into one collapsible tile,
 * so problems dominate the map. Skipped under problems-only (healthy hosts are
 * already hidden) and during a search, where a healthy match has to stay visible
 * under its own name rather than disappear into a bundle.
 */
export function aggregatedChildren(
  folder: FolderTreeNode,
  query: FolderQuery,
  describeOkGroup: (count: number) => string
): FolderTreeNode[] {
  if (folder.ok_group || query.problemsOnly || query.terms.length > 0) {
    return folder.children
  }
  const isHealthyHost = (child: FolderTreeNode) =>
    child.kind === 'host' && !isProblemState(child.state)
  const healthy = folder.children.filter(isHealthyHost)
  if (healthy.length < 2) {
    return folder.children
  }
  const group: FolderTreeNode = {
    path: folder.path + OK_GROUP_SUFFIX,
    title: describeOkGroup(healthy.length),
    kind: 'folder',
    state: 'OK',
    is_empty: false,
    folder_id: '',
    host_count: healthy.length,
    problem_count: 0,
    severity_counts: {},
    output: '',
    acknowledged: false,
    in_downtime: false,
    is_flapping: false,
    stale: false,
    site_id: null,
    children: healthy,
    ok_group: true
  }
  return [...folder.children.filter((child) => !isHealthyHost(child)), group]
}

interface LayoutOptions {
  root: FolderTreeNode
  width: number
  height: number
  /** Whether the node is drawn with its contents inside it. */
  isOpen: (node: FolderTreeNode) => boolean
  /** What an open node holds -- a folder's children, a host's services. */
  childrenOf: (node: FolderTreeNode) => FolderTreeNode[]
}

export function layoutTreemap(options: LayoutOptions): Tile | null {
  const { root, width, height, childrenOf } = options
  if (!width || !height) {
    return null
  }
  // D3 asks whether a node is open twice -- once building the hierarchy, once
  // weighing it -- and the answer involves filtering the node's service leaves.
  // The nodes are stable for the length of one layout, so it is answered once.
  const answered = new Map<FolderTreeNode, boolean>()
  const isOpen = (node: FolderTreeNode): boolean => {
    const known = answered.get(node)
    if (known !== undefined) {
      return known
    }
    const answer = options.isOpen(node)
    answered.set(node, answer)
    return answer
  }
  const laid = hierarchy<FolderTreeNode>(root, (node) =>
    isOpen(node) ? childrenOf(node) : undefined
  )
    // Tile weights: a folder reads as a slightly larger card than a single host
    // (a container against a leaf) without the host count dwarfing the map;
    // empty folders are smallest, services size like hosts, and the "all OK"
    // bundle stays host-sized so it cannot dominate. An open node contributes
    // nothing of its own -- it grows to hold what is inside it.
    .sum((node) => {
      if (node.kind === 'service') {
        return 1
      }
      if (node.kind === 'host' || node.ok_group) {
        return isOpen(node) ? 0 : 1
      }
      return isOpen(node) ? 0 : node.is_empty ? 0.5 : 2
    })
    // Mirror the list's order: a folder's own hosts before its subfolders, then
    // worst severity first (so problems cluster top left), then bigger first.
    // The "all OK" bundle counts as a host, and being healthy sinks below them.
    .sort(
      (a, b) =>
        (a.data.kind === 'folder' && !a.data.ok_group ? 1 : 0) -
          (b.data.kind === 'folder' && !b.data.ok_group ? 1 : 0) ||
        stateRank(b.data.state) - stateRank(a.data.state) ||
        (b.value ?? 0) - (a.value ?? 0)
    )
  return treemap<FolderTreeNode>()
    .tile(treemapSquarify.ratio(1))
    .size([width, height])
    .paddingOuter(3)
    .paddingTop((node) => (node.children ? HEADER_HEIGHT : 0))
    .paddingInner(3)
    .round(true)(laid)
}

/** The tiles worth drawing: child tiles too small to resolve are dropped, and a
 *  container whose children all fail folds into one aggregate tile. */
export function visibleTiles(laid: Tile): Tile[] {
  const tiles: Tile[] = []
  const walk = (tile: Tile): void => {
    tiles.push(tile)
    const children = tile.children
    if (!children?.length) {
      return
    }
    const resolvable = children.filter(
      (child) => child.x1 - child.x0 >= MIN_RESOLVE && child.y1 - child.y0 >= MIN_RESOLVE
    )
    tile.culled = resolvable.length === 0
    if (!tile.culled) {
      resolvable.forEach(walk)
    }
  }
  walk(laid)
  return tiles
}

/**
 * What is on screen and where, so an unchanged picture can be recoloured
 * instead of relaid.
 *
 * The geometry is part of it, not just which tiles are there: a tile too small
 * to resolve is left out of this list but still weighs on the layout, so the
 * same set of drawn tiles can come back at different sizes -- and a recolour
 * would then move their labels while their rectangles stayed put. Rounded
 * layout coordinates make the comparison exact.
 */
export function tileSignature(tiles: readonly Tile[]): string {
  return tiles
    .map((tile) => `${tile.data.path}@${tile.x0},${tile.y0},${tile.x1},${tile.y1}`)
    .join('|')
}
