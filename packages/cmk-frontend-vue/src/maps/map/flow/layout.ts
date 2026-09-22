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
 * untangling itself in front of the operator, and a severity spiral is already
 * readable the moment it is painted. A host's services get their final places,
 * because "in a fan below its host" is a shape, not a balance of forces — the
 * simulation would only fight it.
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
import { serviceNameOf } from '@/maps/map/flow/nodeIds'
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

export function preLayoutHosts(hosts: LayoutNode[]): void {
  if (!hosts.length) {
    return
  }
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
  const r = svcR(services.length)
  return services.reduce(
    (widest, service) => Math.max(widest, serviceNameOf(service.id).length * 5.5 + 8),
    r * 2 + 14
  )
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
