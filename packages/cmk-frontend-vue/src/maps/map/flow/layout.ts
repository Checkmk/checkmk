/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Where a flow map's nodes go before, and beside, the force simulation.
 *
 * Two things are laid out here rather than by forces. Hosts get a starting
 * arrangement, because a simulation started from nothing spends seconds
 * untangling itself in front of the operator, while a severity spiral or the
 * parent tree is already readable the moment it is painted. A host's services
 * get their final places, because "in a fan below its host" is a shape, not a
 * balance of forces — the simulation would only fight it.
 *
 * The nodes are described structurally (``LayoutNode``, ``PinnableNode``) so
 * this module needs neither the d3 simulation types nor a DOM.
 */
import {
  FAN_SPREAD,
  NODE_R,
  fanR,
  finiteOr,
  orbitR,
  severityRank,
  showSvcLabel,
  svcR
} from '@/maps/map/flow/geometry'
import { isFoldNodeId, serviceNameOf } from '@/maps/map/flow/nodeIds'
import type { Elbow } from '@/maps/map/flow/nodes'
import type { ServiceLayout, TopologyNode } from '@/maps/types/api'

// Structural subset of the Flow Map's FNode that the layout pre-pass needs —
// keeps this module free of a dependency on the d3 simulation types.
export interface LayoutNode {
  id: string
  topo?: TopologyNode | undefined
  x?: number | undefined
  y?: number | undefined
}

/** A node the layout pins to a place, rather than suggesting one to the forces. */
export interface PinnableNode extends LayoutNode {
  fx?: number | null | undefined
  fy?: number | null | undefined
}

// Phyllotaxis (sunflower) layout: even-density spiral with no holes. Sorting
// by severity rank (desc) means hosts with the worst state get the inner
// slots, healthy hosts the outer. The combined effect is a compact disk
// whose center is dominated by problems and whose rim is mostly green —
// readable at a glance even on 500-host maps.
const PHYLLOTAXIS_ANGLE = Math.PI * (3 - Math.sqrt(5))
// Exported: the site-umbrella offset derives its disk radius from it.
export const SPIRAL_SPACING = 55

export function rankBySeverity<T extends LayoutNode>(hosts: T[]): T[] {
  return [...hosts].sort((a, b) => {
    const sa = severityRank(a.topo)
    const sb = severityRank(b.topo)
    if (sa !== sb) {
      return sb - sa
    }
    return a.id.localeCompare(b.id)
  })
}

/** The room a host takes in the tree: its label's width, and its row's height. */
export interface Footprint {
  width: number
  height: number
}

/** Where a parent hierarchy starts its hosts, and where each group's site sits. */
export interface TreeLayout {
  at: Map<string, { x: number; y: number }>
  /** Left of each root group's first tree, which its site sits beside. */
  groupAt: { x: number; y: number }[]
  /** How far apart the columns are, a parent from its children's included. */
  column: number
  /** How far left of a host in a grid its edge comes down: the middle of the gap before it. */
  reach: Map<string, number>
}

// A host label is 12px text, about 7px a character.
const HOST_LABEL_CHAR_WIDTH = 7
const HOST_LABEL_PADDING = 12
const MAX_HOST_COLUMN = 240

/** How wide a host's column is: room for its label, the spiral's spacing at least. */
export function hostColumnWidth(name: string): number {
  return Math.min(
    MAX_HOST_COLUMN,
    Math.max(SPIRAL_SPACING, name.length * HOST_LABEL_CHAR_WIDTH + HOST_LABEL_PADDING)
  )
}

const MAX_LABEL_CHARS = Math.floor((MAX_HOST_COLUMN - HOST_LABEL_PADDING) / HOST_LABEL_CHAR_WIDTH)

/**
 * A host's name as drawn, in lines no wider than the widest column, so it never
 * runs into the next one. As everywhere in Checkmk the whole name shows: one too
 * long for a line breaks after the dot, dash or underscore nearest its middle,
 * which for a domain name is mostly after the host's own part. Only a name too
 * long for two lines is cut; it is whole in the hover card.
 */
export function hostLabelLines(name: string): string[] {
  if (name.length <= MAX_LABEL_CHARS) {
    return [name]
  }
  let at = MAX_LABEL_CHARS
  for (let i = 1; i < name.length; i++) {
    const fits = i <= MAX_LABEL_CHARS && name.length - i <= MAX_LABEL_CHARS
    const nearer = Math.abs(i - name.length / 2) < Math.abs(at - name.length / 2)
    if ('.-_'.includes(name[i - 1]!) && fits && (nearer || at === MAX_LABEL_CHARS)) {
      at = i
    }
  }
  const rest = name.slice(at)
  return [
    name.slice(0, at),
    rest.length > MAX_LABEL_CHARS ? `${rest.slice(0, MAX_LABEL_CHARS - 1)}…` : rest
  ]
}

/** More leaves than this under one parent wrap into a grid instead of one long column. */
const WRAP_LEAVES = 12
/** The shape a grid of leaves aims for, wider than tall like a screen. */
const TARGET_ASPECT = 3 / 2
/** Between subtrees; two single hosts one above the other only need their rows apart. */
const BLOCK_GAP = 30
const LEAF_GAP = 10
/** Between a column's widest label and the next column. */
const COLUMN_GAP = 60
/**
 * Between the labels of a grid's columns: well short of a tree's column gap,
 * so a grid does not read as levels of the tree.
 */
const GRID_COLUMN_GAP = 24
const GROUP_GAP = 120

/**
 * A laid-out piece of the tree in its own terms: ``across`` runs down the
 * column of a host's siblings, ``along`` from a parent to its children.
 */
interface Block {
  across: number
  along: number
  places: [id: string, across: number, along: number][]
  /** Where a parent beside the block goes, when not beside its first place. */
  anchor?: number
}

function shifted(block: Block, across: number, along: number): Block['places'] {
  return block.places.map(([id, a, b]) => [id, a + across, b + along])
}

/** Blocks one after the other across, as siblings are. */
function stack(blocks: Block[], gap?: number): Block {
  const places: Block['places'] = []
  let across = 0
  let along = 0
  const anchor = blocks[0]?.anchor
  blocks.forEach((block, i) => {
    if (i > 0) {
      const leaves = block.places.length === 1 && blocks[i - 1]!.places.length === 1
      across += gap ?? (leaves ? LEAF_GAP : BLOCK_GAP)
    }
    places.push(...shifted(block, across, 0))
    across += block.across
    along = Math.max(along, block.along)
  })
  return anchor === undefined ? { across, along, places } : { across, along, places, anchor }
}

/**
 * Cells in rows that read like text, left to right, then the next row down.
 * A slot that holds no cell holds a host the operator opened: it hangs below
 * its row in its column, and the rows after it move down to make room.
 */
function grid(
  slots: Block[],
  isCell: (block: Block) => boolean,
  pitch: number,
  rowGap: number
): Block {
  const cell = Math.max(...slots.filter(isCell).map((one) => one.across)) + rowGap
  // So many rows that the grid is about the target shape on screen.
  const rows = Math.min(
    slots.length,
    Math.max(WRAP_LEAVES, Math.ceil(Math.sqrt((slots.length * pitch) / (cell * TARGET_ASPECT))))
  )
  const columns = Math.ceil(slots.length / rows)
  const places: Block['places'] = []
  let across = 0
  for (let start = 0; start < slots.length; start += columns) {
    const row = slots.slice(start, start + columns)
    row.forEach((one, i) => {
      if (isCell(one)) {
        places.push(...shifted(one, across + (cell - one.across) / 2, i * pitch))
      }
    })
    across += cell
    row.forEach((one, i) => {
      if (!isCell(one)) {
        places.push(...shifted(one, across, i * pitch))
        across += one.across + rowGap
      }
    })
  }
  return {
    across,
    along: Math.max(...slots.map((one, i) => (i % columns) * pitch + one.along)),
    places
  }
}

const isLeaf = (block: Block): boolean => block.places.length === 1
/** A host with nothing drawn below it but its fold: a grid takes it as it takes a leaf. */
const isFoldPair = (block: Block): boolean =>
  block.places.length === 2 && isFoldNodeId(block.places[1]![0])

/**
 * Where a parent hierarchy starts, as a tree from left to right: a site's
 * trees one below the other, each host's children in the column right of it,
 * a parent beside its first child, so no edge crosses its neighbours and the
 * forces have nothing to untangle. A parent with many leaves wraps them into
 * a grid, so a large group stays about a screen's shape.
 *
 * Siblings keep the order they are given in, the first at the top. Each
 * group of roots (a site's) stays together, the next one below it. A
 * host with a second parent hangs under the first; one reachable from no
 * root, as on a parent cycle, starts in a group of its own at the end.
 *
 * Opening more of a host only pushes what is below it further down: the
 * hosts above, and the host itself, stay where the operator clicked.
 */
export function treeLayout(options: {
  rootGroups: readonly (readonly string[])[]
  childrenOf: ReadonlyMap<string, readonly string[]>
  hosts: readonly string[]
  footprint: (id: string) => Footprint
  /** Hosts the operator opened: one opened in a grid keeps its column there. */
  opened?: ReadonlySet<string>
}): TreeLayout {
  const { rootGroups, childrenOf, hosts, opened = new Set<string>() } = options
  const footprints = new Map<string, Footprint>()
  const footprint = (id: string): Footprint => {
    let known = footprints.get(id)
    if (!known) {
      known = options.footprint(id)
      footprints.set(id, known)
    }
    return known
  }
  let widest = 0
  for (const id of [...hosts, ...rootGroups.flat(), ...[...childrenOf.values()].flat()]) {
    widest = Math.max(widest, footprint(id).width)
  }
  const column = widest + COLUMN_GAP
  const claimed = new Set<string>()
  const reach = new Map<string, number>()
  // Siblings one below the other, the leaves among them in a grid once they
  // are too many for one column: a host's children, or a site's top hosts.
  // So are the hosts that hold only a fold, in a grid of their own: a large
  // group opened is mostly those. A grid stands where its first cell would,
  // so a subtree that comes after that cell comes after the grid.
  const siblings = (blocks: Block[], gap?: number): Block => {
    let laid = blocks
    for (const isCell of [isLeaf, isFoldPair]) {
      const cells = laid.filter(isCell)
      if (cells.length <= WRAP_LEAVES) {
        continue
      }
      const along = Math.max(...cells.map((cell) => cell.along))
      const widest = Math.max(
        ...cells.flatMap((cell) => cell.places.map(([id]) => footprint(id).width))
      )
      const pitch = along + widest + GRID_COLUMN_GAP
      const first = laid.findIndex(isCell)
      // Opening a host there makes it more than a host and its fold; it stays
      // where it was rather than move after the whole grid.
      const inGrid = (block: Block, i: number): boolean =>
        isCell(block) || (isCell === isFoldPair && i > first && opened.has(block.places[0]![0]))
      const slots = laid.filter(inGrid)
      // Clear of the fold beside the host to the left, too.
      slots.forEach((slot) => reach.set(slot.places[0]![0], (pitch - along) / 2))
      // A fold's ring is wider than a host's, and would touch the name above it.
      const rowGap = isCell === isFoldPair ? LEAF_GAP : 0
      let wrapped = grid(slots, isCell, pitch, rowGap)
      if (first === 0) {
        // A row free above the grid for its parent, whose edges run along it
        // and come down to each column, rather than climb over the first row.
        const head = Math.max(...cells.map((cell) => cell.across)) + rowGap
        wrapped = {
          across: wrapped.across + head,
          along: wrapped.along,
          places: shifted(wrapped, head, 0),
          anchor: head / 2
        }
      }
      laid = [
        ...laid.slice(0, first),
        wrapped,
        ...laid.filter((block, i) => i > first && !inGrid(block, i))
      ]
    }
    return stack(laid, gap)
  }
  const subtree = (id: string): Block => {
    claimed.add(id)
    const own = footprint(id)
    const children: Block[] = []
    for (const child of childrenOf.get(id) ?? []) {
      if (!claimed.has(child)) {
        children.push(subtree(child))
      }
    }
    if (!children.length) {
      return { across: own.height, along: 0, places: [[id, own.height / 2, 0]] }
    }
    const beside = siblings(children)
    // Beside its first child rather than centred: opening more of its children
    // then grows the subtree downwards and the parent stays where it is.
    const across = Math.max(own.height / 2, beside.anchor ?? beside.places[0]![1])
    return {
      across: Math.max(across + own.height / 2, beside.across),
      along: column + beside.along,
      places: [[id, across, 0], ...shifted(beside, 0, column)]
    }
  }
  const groupOf = (roots: readonly string[]): Block =>
    siblings(roots.filter((root) => !claimed.has(root)).map(subtree), BLOCK_GAP)
  const groups = rootGroups.map(groupOf)
  const strays = groupOf(hosts.filter((id) => !claimed.has(id)))
  if (strays.places.length) {
    groups.push(strays)
  }

  // Each group is tagged by a marker beside its first tree, which is where
  // its site goes: like a parent beside its first child, it then stays put as
  // the group grows.
  const marker = (index: number): string => `\0group${index}`
  const map = stack(
    groups.map((group, index) => ({
      ...group,
      places: [[marker(index), group.anchor ?? group.places[0]?.[1] ?? 0, 0], ...group.places]
    })),
    GROUP_GAP
  )
  const at = new Map<string, { x: number; y: number }>()
  for (const [id, across, along] of map.places) {
    at.set(id, { x: along, y: across })
  }
  const groupAt = rootGroups.map((_, index) => at.get(marker(index))!)
  groups.forEach((_, index) => at.delete(marker(index)))
  return { at, groupAt, column, reach }
}

/**
 * Where a host that has just come to be drawn goes among its drawn siblings,
 * without moving any of them: the first free cell of the grid they form, row
 * by row, or the next row, or the next place in their column.
 */
export function freeCellBeside(
  siblings: readonly { x: number; y: number }[],
  height: number
): { x: number; y: number } | undefined {
  if (!siblings.length) {
    return undefined
  }
  const left = Math.min(...siblings.map((sibling) => sibling.x))
  const further = siblings.filter((sibling) => sibling.x > left + NODE_R)
  if (!further.length) {
    return { x: left, y: Math.max(...siblings.map((sibling) => sibling.y)) + height + LEAF_GAP }
  }
  // Rows a hair apart, from collide or a drag, are the same row.
  const ys = further
    .map((sibling) => sibling.y)
    .sort((a, b) => a - b)
    .filter((y, i, sorted) => i === 0 || y - sorted[i - 1]! >= NODE_R)
  const gaps = ys.slice(1).map((y, i) => y - ys[i]!)
  const pitchY = gaps.length ? Math.min(...gaps) : height + LEAF_GAP
  const pitchX = Math.min(...further.map((sibling) => sibling.x)) - left
  const top = ys[0]!
  const rows = Math.round((ys.at(-1)! - top) / pitchY) + 1
  const columns = Math.round((Math.max(...further.map((sibling) => sibling.x)) - left) / pitchX) + 1
  const taken = new Set(
    siblings.map(
      (sibling) =>
        `${Math.round((sibling.x - left) / pitchX)}:${Math.round((sibling.y - top) / pitchY)}`
    )
  )
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < columns; c++) {
      if (!taken.has(`${c}:${r}`)) {
        return { x: left + c * pitchX, y: top + r * pitchY }
      }
    }
  }
  // Below every sibling: a subtree may hang below the grid in its first column.
  return { x: left, y: Math.max(...siblings.map((sibling) => sibling.y)) + pitchY }
}

/**
 * Where a parent's tree edges turn: ``drop`` right of the parent, its
 * children's first column, and for a child further right in a grid, ``aside``
 * how far above it the edge comes across, over the grid rather than through
 * the hosts before it: along the parent's own row when the grid starts below
 * it. Taken from where the children are, so it holds for a host placed later
 * too.
 */
export function elbowsOf(
  parent: { x: number; y: number },
  children: readonly { id: string; x: number; y: number }[],
  rowHeight: number,
  reach: ReadonlyMap<string, number> = new Map()
): Map<string, Elbow> {
  const elbows = new Map<string, Elbow>()
  // A child the operator moved to or behind its parent keeps a straight edge:
  // an elbow would run back through the parent.
  const column = children.filter((child) => child.x - parent.x > NODE_R)
  if (!column.length) {
    return elbows
  }
  const left = Math.min(...column.map((child) => child.x))
  const further = column.filter((child) => child.x > left + NODE_R)
  const top = Math.min(...further.map((child) => child.y))
  const clear = !column.some((child) => child.x <= left + NODE_R && child.y < top - NODE_R)
  const stem = further.length
    ? Math.min(top - rowHeight / 2 - LEAF_GAP / 2, clear ? parent.y : Infinity)
    : 0
  // Halfway into the gap before a column: the names hang centred under the
  // hosts, so that is as far from them as the edge can keep.
  const drop = left - parent.x
  // Hosts of one column sit at about the same x, not quite: the simulation
  // nudges them.
  const xs = column.map((child) => child.x).sort((a, b) => a - b)
  const gaps = xs
    .slice(1)
    .map((x, i) => x - xs[i]!)
    .filter((gap) => gap > 2 * NODE_R)
  const pitch = Math.min(drop, ...gaps)
  for (const child of column) {
    const along = child.x > left + NODE_R
    elbows.set(child.id, {
      drop,
      aside: along ? stem - child.y : 0,
      rise: pitch / 2,
      reach: along ? (reach.get(child.id) ?? pitch / 2) : pitch / 2
    })
  }
  return elbows
}

export function preLayoutHosts(hosts: LayoutNode[]): void {
  rankBySeverity(hosts).forEach((d, i) => {
    const angle = i * PHYLLOTAXIS_ANGLE
    const r = SPIRAL_SPACING * Math.sqrt(i + 1)
    d.x = r * Math.cos(angle)
    d.y = r * Math.sin(angle)
  })
}

// Half-disk phyllotaxis below the site: mirror the negative-y points so the
// entire spiral lands in the lower half-plane. Hosts visually hang under
// their site root instead of orbiting around (0,0).
export function preLayoutHostsBelowSite(
  sitePos: { x: number; y: number },
  hosts: LayoutNode[],
  gap: number
): void {
  if (!hosts.length) {
    return
  }
  rankBySeverity(hosts).forEach((d, i) => {
    const angle = i * PHYLLOTAXIS_ANGLE
    const r = SPIRAL_SPACING * Math.sqrt(i + 1)
    d.x = sitePos.x + r * Math.cos(angle)
    d.y = sitePos.y + gap + Math.abs(r * Math.sin(angle))
  })
}

export function layoutR(layout: ServiceLayout | null | undefined, N: number): number {
  return layout === 'fan' ? fanR(N) : orbitR(N)
}

// Layouts that need the full per-host service list. Donut renders only
// services_summary aggregates and therefore skips the bulk query entirely —
// that's the main scaling win for large installations.
export function needsServices(layout: ServiceLayout | null | undefined): boolean {
  return layout === 'fan' || layout === 'orbit' || layout === 'row'
}

/** How many columns the row grid wraps a host's ``N`` services into. */
export function rowColumns(N: number): number {
  return Math.min(N, Math.max(4, Math.ceil(Math.sqrt(N * 1.5))))
}

/**
 * Column width for the row grid from the service names alone, for the first
 * paint — before the labels are in the DOM there is nothing to measure, and
 * guessing from the name lengths beats letting them overlap.
 */
export function rowSpacingFallback(services: readonly LayoutNode[]): number {
  return rowColumnGuess(services.map((service) => serviceNameOf(service.id)))
}

/** A row grid's column width from its service names, before any is drawn. */
export function rowColumnGuess(names: readonly string[]): number {
  return names.reduce(
    (widest, name) => Math.max(widest, name.length * 5.5 + 8),
    svcR(names.length) * 2 + 14
  )
}

/**
 * How far a host's ``N`` services reach out from it. Collide keeps neighbours
 * this far apart and the tree start leaves them this much room, so the two
 * agree and the forces have nothing to push apart.
 */
export function serviceReach(layout: ServiceLayout, N: number, rowColumnWidth: number): number {
  if (layout === 'fan' || layout === 'orbit') {
    return layoutR(layout, N) + svcR(N) + 35
  }
  return (rowColumns(N) / 2) * rowColumnWidth + svcR(N) + 20
}

/**
 * Pins every host's services into the shape the chosen layout asks for: a fan
 * below the host, a full orbit around it, or a wrapping grid under it.
 *
 * ``rowSpacings`` carries the column widths measured off the rendered labels,
 * where they have been rendered — the grid is the one layout whose spacing
 * depends on how long the service names actually draw.
 */
export function placeServiceNodes(options: {
  layout: ServiceLayout
  hosts: ReadonlyMap<string, LayoutNode>
  servicesByHost: ReadonlyMap<string, PinnableNode[]>
  rowSpacings: ReadonlyMap<string, number>
}): void {
  const { layout, hosts, servicesByHost, rowSpacings } = options
  for (const [hostId, services] of servicesByHost) {
    const host = hosts.get(hostId)
    if (!host) {
      continue
    }
    const hx = finiteOr(host.x)
    const hy = finiteOr(host.y)
    const N = services.length
    if (layout === 'fan') {
      // Semicircle below the host — the radius scales with N so the points
      // stay clear of each other.
      const R = fanR(N)
      const spread = N > 1 ? FAN_SPREAD : 0
      services.forEach((service, i) => {
        const angle = Math.PI / 2 + (N > 1 ? -spread / 2 + (i * spread) / (N - 1) : 0)
        service.fx = hx + R * Math.cos(angle)
        service.fy = hy + R * Math.sin(angle)
      })
      continue
    }
    if (layout === 'orbit') {
      const R = orbitR(N)
      services.forEach((service, i) => {
        const angle = (2 * Math.PI * i) / N - Math.PI / 2
        service.fx = hx + R * Math.cos(angle)
        service.fy = hy + R * Math.sin(angle)
      })
      continue
    }
    const r = svcR(N)
    const cols = rowColumns(N)
    const spacingX = rowSpacings.get(hostId) ?? rowSpacingFallback(services)
    const spacingY = r * 2 + (showSvcLabel(N) ? 26 : 6)
    const yOffset = NODE_R + r + 22
    services.forEach((service, i) => {
      const col = i % cols
      const row = Math.floor(i / cols)
      service.fx = hx + (col - (cols - 1) / 2) * spacingX
      service.fy = hy + yOffset + row * spacingY
    })
  }
}

// Site root box scales up at low zoom so the label stays legible. At fit-zoom
// (k≈0.25) the 110-px-wide rect would render as ~28px without this — too
// small to read. At full zoom the scale stays 1 (no inflation).
export function siteScaleForZoom(zoomK: number): number {
  const inv = 1 / Math.max(finiteOr(zoomK, 1), 0.0001)
  return Math.min(3.5, Math.max(1, inv))
}

/**
 * Parent → children over the hosts the map actually draws. A parent the
 * topology does not contain is dropped, so a partial view has roots rather than
 * edges into nothing.
 */
export function childrenByParent(topoNodes: TopologyNode[]): Map<string, string[]> {
  const present = new Set(topoNodes.map((n) => n.name))
  const childrenOf = new Map<string, string[]>()
  for (const n of topoNodes) {
    for (const parent of n.parents) {
      if (!present.has(parent)) {
        continue
      }
      const children = childrenOf.get(parent) ?? []
      children.push(n.name)
      childrenOf.set(parent, children)
    }
  }
  return childrenOf
}

/**
 * Whether a host shows the aggregated ring instead of its services. Off is the
 * operator's explicit choice and is left alone; a detail layout falls back to
 * the ring only where the backend dropped the per-service rows for a host it
 * did not count among the worst.
 *
 * Both the painter and the collide force need this — the ring takes room.
 */
export function showsDonut(layout: ServiceLayout, servicesOmitted: boolean | undefined): boolean {
  if (layout === 'donut') {
    return true
  }
  return layout !== 'off' && (servicesOmitted ?? false)
}

// Loose BFS levels over the parent topology — feeds d3's forceY so layers
// roughly stack top-down. Hosts whose parents are all outside the visible
// set count as roots; unreachable leftovers sink to the bottom.
//
// The caller usually needs the child index too, so it can be passed in rather
// than built a second time.
export function bfsLevels(
  topoNodes: TopologyNode[],
  childrenOf: ReadonlyMap<string, string[]> = childrenByParent(topoNodes)
): Map<string, number> {
  const nameSet = new Set(topoNodes.map((n) => n.name))
  const levels = new Map<string, number>()
  const roots = topoNodes.filter(
    (n) => !n.parents.length || n.parents.every((p) => !nameSet.has(p))
  )
  const queue: string[] = roots.map((r) => r.name)
  roots.forEach((r) => levels.set(r.name, 0))
  while (queue.length) {
    const name = queue.shift()!
    const lvl = levels.get(name)!
    for (const child of childrenOf.get(name) ?? []) {
      if (!levels.has(child)) {
        levels.set(child, lvl + 1)
        queue.push(child)
      }
    }
  }
  // What the BFS never reached — a parent cycle, say. They all sink to one
  // level below the deepest real one; giving each its own would drive the
  // maximum up with the size of the topology, and the layer spacing derived
  // from it towards zero, flattening the whole map's stratification.
  let deepest = 0
  for (const level of levels.values()) {
    deepest = Math.max(deepest, level)
  }
  topoNodes.filter((n) => !levels.has(n.name)).forEach((n) => levels.set(n.name, deepest + 1))
  return levels
}
