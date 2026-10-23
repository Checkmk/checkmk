/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The graph a flow map draws, built from the topology it was pushed.
 *
 * A topology arrives as a flat list of hosts and their parents. What the map
 * draws is more than that: a service node, or a "+N more" stand-in, for each
 * service on show, and a synthetic root per site so the operator always sees
 * "these hosts are on that site". Those nodes are invented here, along with all
 * the edges between them.
 *
 * The positions live here too. A push arrives every few seconds and rebuilds
 * the graph; were that to start from nothing, the map would jump on every push
 * and a drag would be undone by the next one. So a node keeps the place it had,
 * and only a genuinely new one is given one — from the map's saved positions
 * where it has one, from the severity pre-layout otherwise.
 *
 * A rebuild also keeps the node *objects*, writing the live fields onto them.
 * That is what lets a hover card or an open slide-in hold on to a node and go
 * on seeing its current state.
 *
 * A plain factory: it holds the remembered positions and nothing reactive, so
 * it can be built and exercised outside a component.
 */
import { fanR, finiteOr, orbitR } from '@/maps/map/flow/geometry'
import {
  SPIRAL_SPACING,
  bfsLevels,
  childrenByParent,
  needsServices,
  preLayoutHosts,
  preLayoutHostsBelowSite
} from '@/maps/map/flow/layout'
import { isChildNodeId, moreNodeId, serviceNodeId, siteNodeId } from '@/maps/map/flow/nodeIds'
import type { FLink, FNode } from '@/maps/map/flow/nodes'
import type { ServiceLayout, TopologyNode } from '@/maps/types/api'

/** How far a site root sits above the disk of hosts hanging off it. */
const HOST_SITE_GAP = 140
/** Extra offset that keeps the site clear of its group's dispersion. */
const SITE_CLEARANCE = 160
/** Horizontal gap between two sites' groups. */
const SITE_SPREAD = 600
/** Widest a BFS layer gap gets, however tall the drawing area is. */
const MAX_LAYER_SPACING = 130

/** A place on the map, as the map remembers it. */
interface Position {
  x: number
  y: number
}

/** Everything one rebuild produced. */
export interface FlowGraph {
  nodes: FNode[]
  links: FLink[]
  /** The edges the simulation treats as springs — service edges are placed. */
  springLinks: FLink[]
  byId: Map<string, FNode>
  /** A host's service and "+N more" nodes, by host id. */
  servicesByHost: Map<string, FNode[]>
  /** Parent → direct children, sites included, for the unpin-on-drag walk. */
  childrenOf: Map<string, string[]>
  /** Where the pre-layout put each host — what the anchor forces pull towards. */
  anchorX: Map<string, number>
  anchorY: Map<string, number>
  /** Deepest BFS level; 0 means the topology is flat. */
  maxLvl: number
  vSpacing: number
  /** Whether a host was added, removed or renamed since the previous build. */
  structurallyChanged: boolean
}

export interface FlowGraphBuild {
  topology: TopologyNode[]
  layout: ServiceLayout
  /** Stands in for a site the topology did not tag — a single-site setup. */
  connectionId: string
  /** The positions the map remembers, so a reload keeps the arrangement. */
  savedPositions: Record<string, Position>
  /** Height of the drawing area, which the BFS layers are fitted into. */
  height: number
}

/** A node seed: the fields a rebuild writes, minus the id it is stored under. */
type NodeSeed = Omit<Partial<FNode>, 'id'> & Pick<FNode, 'nodeType'>

export interface FlowGraphOptions {
  /**
   * What the stand-in for a host's undrawn services says it stands for.
   * Injected rather than translated here, so this module needs no i18n context.
   */
  describeTruncation: (count: number) => string
}

export function createFlowGraph({ describeTruncation }: FlowGraphOptions) {
  // The stable node store: this is what carries d3's positions, and the
  // operator's drags, across topology pushes.
  const store = new Map<string, FNode>()
  let lastHostIds: Set<string> = new Set()

  /**
   * Reuses the node this id already has, writing the live fields onto it, or
   * starts a new one — ``onCreate`` places only those.
   */
  function upsert(id: string, seed: NodeSeed, onCreate?: (node: FNode) => void): FNode {
    const known = store.get(id)
    if (known) {
      Object.assign(known, seed)
      return known
    }
    const node: FNode = { id, state: 'PENDING', output: '', bfsLevel: 0, ...seed }
    store.set(id, node)
    onCreate?.(node)
    return node
  }

  function build({
    topology,
    layout,
    connectionId,
    savedPositions,
    height
  }: FlowGraphBuild): FlowGraph {
    // Parent → children, built once: the BFS walk needs it, and so does the
    // "free the subtree" step of a drag.
    const childrenOf = childrenByParent(topology)
    const levels = bfsLevels(topology, childrenOf)
    const maxLvl = highest(levels.values())
    const vSpacing = layerSpacing(topology, layout, maxLvl, height)

    // --- Hosts. One the map has not seen before starts where the map
    // remembers it, so a reload preserves the operator's arrangement.
    const nodes: FNode[] = topology.map((topo) =>
      upsert(
        topo.name,
        {
          nodeType: 'host',
          state: topo.state,
          output: topo.output,
          bfsLevel: levels.get(topo.name) ?? 0,
          topo
        },
        (node) => pin(node, savedPositions[topo.name])
      )
    )

    // --- Services, plus one "+N more" stand-in per host whose service list the
    // backend truncated, so the operator can see there is more than is drawn.
    if (needsServices(layout)) {
      for (const topo of topology) {
        if (!topo.services) {
          continue
        }
        const bfsLevel = levels.get(topo.name) ?? 0
        const truncated = topo.services_truncated_count ?? 0
        const svcTotalCount = topo.services.length + (truncated > 0 ? 1 : 0)
        for (const svc of topo.services) {
          nodes.push(
            upsert(serviceNodeId(topo.name, svc.name), {
              nodeType: 'service',
              hostId: topo.name,
              state: svc.state,
              output: svc.output,
              bfsLevel,
              svcTotalCount,
              svc,
              parentTopo: topo
            })
          )
        }
        if (truncated > 0) {
          nodes.push(
            upsert(moreNodeId(topo.name), {
              nodeType: 'more',
              hostId: topo.name,
              state: 'PENDING',
              output: describeTruncation(truncated),
              bfsLevel,
              svcTotalCount,
              moreCount: truncated,
              parentTopo: topo
            })
          )
        }
      }
    }

    // --- Site roots. A flat topology hangs its hosts under their site in a
    // half-disk; a hierarchical one is already laid out top-down by BFS, so the
    // site just sits above the topmost layer rather than adding an empty link.
    const rootCount = topology.filter((n) => n.parents.length === 0).length
    const isMostlyFlat = topology.length > 0 && rootCount / topology.length >= 0.5
    const siteOf = (topo: TopologyNode): string => topo.site_id || connectionId
    const siteIds: string[] = []
    const hostsBySite = new Map<string, FNode[]>()
    for (const node of nodes) {
      if (node.nodeType !== 'host' || !node.topo) {
        continue
      }
      const siteId = siteOf(node.topo)
      if (!hostsBySite.has(siteId)) {
        siteIds.push(siteId)
        hostsBySite.set(siteId, [])
      }
      hostsBySite.get(siteId)!.push(node)
    }
    const spread = Math.max(0, (siteIds.length - 1) * SITE_SPREAD)
    const sitePositions = new Map<string, Position>()
    siteIds.forEach((siteId, index) => {
      // Above its own group of hosts, clear of the dispersion a large group
      // spreads over. Once the operator drags a site the position is theirs,
      // and the remembered one is kept instead of snapping back to this.
      const startsAt: Position = {
        x: siteIds.length === 1 ? 0 : -spread / 2 + (index * spread) / (siteIds.length - 1),
        y: -(
          SPIRAL_SPACING * Math.sqrt(Math.max(1, hostsBySite.get(siteId)?.length ?? 0)) +
          SITE_CLEARANCE
        )
      }
      const id = siteNodeId(siteId)
      const node = upsert(id, { nodeType: 'site', siteId, state: 'UP', output: '' }, (site) =>
        pin(site, savedPositions[id] ?? startsAt)
      )
      nodes.push(node)
      sitePositions.set(siteId, { x: node.x ?? startsAt.x, y: node.y ?? startsAt.y })
    })

    // --- A starting arrangement for hosts that have no position yet, so the
    // first paint is already readable instead of a knot the forces untangle.
    if (isMostlyFlat && siteIds.length > 0) {
      for (const siteId of siteIds) {
        const at = sitePositions.get(siteId)
        if (at) {
          const placeless = (hostsBySite.get(siteId) ?? []).filter((n) => n.x === undefined)
          preLayoutHostsBelowSite(at, placeless, HOST_SITE_GAP)
        }
      }
    } else {
      preLayoutHosts(nodes.filter((n) => n.nodeType === 'host' && n.x === undefined))
    }

    const anchorX = new Map<string, number>()
    const anchorY = new Map<string, number>()
    for (const node of nodes) {
      if (node.nodeType === 'host') {
        anchorX.set(node.id, finiteOr(node.x))
        anchorY.set(node.id, finiteOr(node.y))
      }
    }

    // Forget what the topology no longer contains, so the store does not grow
    // with every host that has ever been on the map.
    const present = new Set(nodes.map((n) => n.id))
    for (const id of store.keys()) {
      if (!present.has(id)) {
        store.delete(id)
      }
    }

    const byId = new Map(nodes.map((n) => [n.id, n] as const))

    // A drag on a host frees its whole subtree — a descendant still pinned from
    // an earlier drag would otherwise stay put and make the spring look broken.
    // The site roots are added to the same index below, so a site drag does it
    // for its hosts too.
    const addChild = (parent: string, child: string): void => {
      const children = childrenOf.get(parent) ?? []
      children.push(child)
      childrenOf.set(parent, children)
    }

    const links: FLink[] = []
    const connect = (source: FNode, target: FNode, isServiceLink: boolean): void => {
      links.push({ source, target, sourceState: source.state, isServiceLink })
    }
    for (const topo of topology) {
      const target = byId.get(topo.name)
      for (const parent of topo.parents) {
        const source = byId.get(parent)
        if (source && target) {
          connect(source, target, false)
        }
      }
    }
    // Site → host. In a hierarchy only the top-level hosts hang off the site;
    // the ones below already have a visual chain through their parents. The
    // link carries no state of its own, hence the fixed one.
    if (siteIds.length > 0) {
      const attached = isMostlyFlat ? topology : topology.filter((n) => n.parents.length === 0)
      for (const topo of attached) {
        const id = siteNodeId(siteOf(topo))
        addChild(id, topo.name)
        const source = byId.get(id)
        const target = byId.get(topo.name)
        if (source && target) {
          links.push({ source, target, sourceState: 'UP', isServiceLink: false })
        }
      }
    }

    const servicesByHost = new Map<string, FNode[]>()
    for (const node of nodes) {
      if ((node.nodeType === 'service' || node.nodeType === 'more') && node.hostId) {
        const siblings = servicesByHost.get(node.hostId) ?? []
        siblings.push(node)
        servicesByHost.set(node.hostId, siblings)
      }
    }
    for (const [hostId, services] of servicesByHost) {
      const host = byId.get(hostId)
      if (!host) {
        continue
      }
      for (const service of services) {
        connect(host, service, true)
      }
    }

    // A push arrives every few seconds and must not restart the simulation
    // unless something structural changed: a status-only update would otherwise
    // cost a full force relaxation, and the operator's layout would drift.
    const hostIds = new Set(topology.map((n) => n.name))
    const structurallyChanged =
      hostIds.size !== lastHostIds.size || [...hostIds].some((id) => !lastHostIds.has(id))
    lastHostIds = hostIds

    return {
      nodes,
      links,
      springLinks: links.filter((link) => !link.isServiceLink),
      byId,
      servicesByHost,
      childrenOf,
      anchorX,
      anchorY,
      maxLvl,
      vSpacing,
      structurallyChanged
    }
  }

  /** Where the operator has pinned hosts and sites, for the map to remember. */
  function pinnedPositions(): Record<string, Position> {
    const positions: Record<string, Position> = {}
    for (const node of store.values()) {
      if (node.nodeType !== 'host' && node.nodeType !== 'site') {
        continue
      }
      if (Number.isFinite(node.fx) && Number.isFinite(node.fy)) {
        positions[node.id] = { x: node.fx as number, y: node.fy as number }
      }
    }
    return positions
  }

  /** Frees a host's descendants, so a drag on it can pull them along. */
  function unpinDescendants(rootId: string, childrenOf: ReadonlyMap<string, string[]>): void {
    const seen = new Set<string>()
    const queue = [rootId]
    while (queue.length) {
      for (const childId of childrenOf.get(queue.shift()!) ?? []) {
        if (seen.has(childId)) {
          continue
        }
        seen.add(childId)
        queue.push(childId)
        const child = store.get(childId)
        if (child) {
          child.fx = null
          child.fy = null
        }
      }
    }
  }

  /** Start over: a different map, or a different root for this one. */
  function clear(): void {
    store.clear()
  }

  /**
   * What a switch of service layout invalidates. The service nodes go, because
   * the new layout places them from scratch. A host the operator has not
   * dragged loses its position too: the layouts need very different room around
   * a host, and carrying a donut-tight spiral into a fan makes the rings
   * overlap. A dragged host keeps its place — that one is the operator's.
   */
  function forgetLayout(from: ServiceLayout, to: ServiceLayout): void {
    // Off never left room for services, so coming off it every host moves.
    const everyHostMoves = from === 'off' && to !== 'off'
    for (const [id, node] of store) {
      if (isChildNodeId(id)) {
        store.delete(id)
        continue
      }
      const pinned = node.fx !== undefined && node.fx !== null
      if (node.nodeType === 'host' && (!pinned || everyHostMoves)) {
        node.x = node.y = node.vx = node.vy = undefined
      }
    }
  }

  return { build, pinnedPositions, unpinDescendants, clear, forgetLayout }
}

function pin(node: FNode, at: Position | undefined): void {
  if (!at) {
    return
  }
  node.x = node.fx = at.x
  node.y = node.fy = at.y
}

function highest(values: Iterable<number>): number {
  let max = 0
  for (const value of values) {
    if (value > max) {
      max = value
    }
  }
  return max
}

/**
 * How far apart the BFS layers sit: the drawing area divided by the number of
 * layers, but never so close that the service rings of two layers overlap.
 */
function layerSpacing(
  topology: TopologyNode[],
  layout: ServiceLayout,
  maxLvl: number,
  height: number
): number {
  let widest = 0
  if (needsServices(layout)) {
    for (const topo of topology) {
      widest = Math.max(widest, topo.services?.length ?? 0)
    }
  }
  // A fan only reaches downwards, so it needs about half the gap an orbit does.
  const minimum = widest > 0 ? (layout === 'fan' ? fanR(widest) + 50 : orbitR(widest) * 2 + 50) : 0
  return Math.max(minimum, Math.min(MAX_LAYER_SPACING, (height * 0.8) / Math.max(1, maxLvl + 1)))
}
