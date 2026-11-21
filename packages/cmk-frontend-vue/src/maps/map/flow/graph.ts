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
 * service on show, a synthetic root per site so the operator always sees
 * "these hosts are on that site", and a "+N hosts" fold where a large
 * hierarchy is folded (``foldHierarchy``). Those nodes are invented here,
 * along with all the edges between them.
 *
 * The positions live here too. A push arrives every few seconds and rebuilds
 * the graph; were that to start from nothing, the map would jump on every push
 * and a drag would be undone by the next one. So a node keeps the place it had,
 * and only a genuinely new one is given one — from the map's saved positions
 * where it has one, from the pre-layout otherwise: the parent tree for a
 * hierarchy, a severity spiral for a flat map.
 *
 * A rebuild also keeps the node *objects*, writing the live fields onto them.
 * That is what lets a hover card or an open slide-in hold on to a node and go
 * on seeing its current state.
 *
 * A plain factory: it holds the remembered positions and nothing reactive, so
 * it can be built and exercised outside a component.
 */
import {
  ATTENTION_STATE,
  type Attention,
  attentionOf,
  attentionRank,
  needsAttention,
  unhandledIn,
  worstIn
} from '@/maps/map/flow/attention'
import { VISIBLE_HOSTS, foldHierarchy } from '@/maps/map/flow/fold'
import {
  type DonutSegment,
  NODE_R,
  fanR,
  finiteOr,
  orbitR,
  problemScoreFromTopo,
  summarizeHosts,
  svcR,
  worstServiceState
} from '@/maps/map/flow/geometry'
import {
  type Footprint,
  SPIRAL_SPACING,
  type TreeLayout,
  bfsLevels,
  childrenByParent,
  elbowsOf,
  freeCellBeside,
  hostColumnWidth,
  hostLabelLines,
  needsServices,
  preLayoutHosts,
  preLayoutHostsBelowSite,
  rowColumnGuess,
  rowColumns,
  serviceReach,
  treeLayout
} from '@/maps/map/flow/layout'
import {
  KIND_TRAITS,
  foldNodeId,
  isChildNodeId,
  moreNodeId,
  serviceNodeId,
  siteNodeId
} from '@/maps/map/flow/nodeIds'
import type { Elbow, FLink, FNode, FoldHost, HostFrame } from '@/maps/map/flow/nodes'
import type { HostLayout, ServiceLayout, TopologyNode } from '@/maps/types/api'

/** How far a site root sits above a flat map's disk of hosts. */
const HOST_SITE_GAP = 140
/** Extra offset that keeps the site clear of its group's dispersion. */
const SITE_CLEARANCE = 160
/** Horizontal gap between two sites' groups. */
const SITE_SPREAD = 600
/** Widest a BFS layer gap gets, however tall the drawing area is. */
const MAX_LAYER_SPACING = 130
/**
 * Height of a host with its ring and its label below, the row pitch of a tree:
 * no less than collide keeps two hosts apart, or it pushes them out of line.
 */
const HOST_ROW = 2 * NODE_R + 30
/** A further line of a host's name. */
const LABEL_LINE = 15
/** Room for a folded group's "+N hosts" label. */
export const FOLD_WIDTH = 90

function placed(node: FNode | undefined): node is FNode & Position {
  return !!node && Number.isFinite(node.x) && Number.isFinite(node.y)
}

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
  /** Whether the hosts start along their parent tree, which then holds them. */
  startsAsTree: boolean
  /** In a tree, each site's frame, then each opened host's; empty otherwise. */
  frames: HostFrame[]
  vSpacing: number
  /** Whether a host or a group was added or removed since the previous build. */
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
  /** Hosts and site roots whose folded children the operator opened, with how often. */
  opened: ReadonlyMap<string, number>
  /** Hosts the operator searched for, which are drawn wherever they hang. */
  found: ReadonlySet<string>
  /** Whether the map shows only what has a problem, which is then drawn wherever it hangs. */
  problemsOnly: boolean
  /** The host the operator picked by its name, which is drawn wherever it hangs. */
  picked: string | null
  /** How a parent hierarchy is laid out; a flat map ignores it. */
  hostLayout: HostLayout
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
  // What a tree is laid out afresh for: the hosts, and what the operator opened,
  // searched or filtered. A change of state leaves the drawn hosts where they are.
  let lastNames: ReadonlySet<string> = new Set()
  let lastOpened: ReadonlyMap<string, number> = new Map()
  let lastDrawn: ReadonlySet<string> = new Set()
  let lastAsked: ReadonlySet<string> = new Set()
  let lastProblemsOnly = false
  /** Where each site of a tree was put by the layout, rather than by the operator. */
  let siteLaidOutAt = new Map<string, Position>()
  /**
   * Where the operator put the hosts that are folded away, which keep that
   * place for when they are drawn again: from the map, or from the store when
   * they were folded before the map saved it.
   */
  let keptAway = new Map<string, Position>()
  /** Hosts freed by a drag on an ancestor while folded away, whose saved place no longer counts. */
  let freedAway = new Set<string>()
  let lastTopology: readonly TopologyNode[] = []

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
    height,
    opened,
    found,
    problemsOnly,
    picked,
    hostLayout
  }: FlowGraphBuild): FlowGraph {
    // Parent → children, built once: the BFS walk needs it, and so does the
    // "free the subtree" step of a drag.
    const childrenOf = childrenByParent(topology)
    const levels = bfsLevels(topology, childrenOf)
    const maxLvl = highest(levels.values())
    const vSpacing = layerSpacing(topology, layout, maxLvl, height)
    // A host whose parents are not on the map is a root here too.
    const rootCount = topology.filter((n) => levels.get(n.name) === 0).length
    const isMostlyFlat = topology.length > 0 && rootCount / topology.length >= 0.5
    const siteOf = (topo: TopologyNode): string => topo.site_id || connectionId

    // --- What a large hierarchy folds away. A flat map has nothing to fold
    // under, and keeps its severity spiral; a hierarchy drawn as a network
    // shows every host.
    const rootsBySite = new Map<string, string[]>()
    for (const topo of topology) {
      if (levels.get(topo.name) === 0) {
        const roots = rootsBySite.get(siteOf(topo)) ?? []
        roots.push(topo.name)
        rootsBySite.set(siteOf(topo), roots)
      }
    }
    // What the search or the problems filter names is drawn wherever it hangs.
    // A search that names a large part of the map is shown by dimming alone:
    // drawing every hit would defeat the folding.
    const asked = new Set([
      ...(found.size <= VISIBLE_HOSTS / 2 ? found : []),
      ...(picked ? [picked] : [])
    ])
    // The problems follow the states, unlike what the operator asked for.
    const drawnAnyway: ReadonlySet<string> = problemsOnly
      ? new Set([...asked, ...withProblems(topology)])
      : asked
    const folded =
      isMostlyFlat || hostLayout === 'network'
        ? undefined
        : foldHierarchy({
            sites: [...rootsBySite].map(([siteId, roots]) => ({
              siteRoot: siteNodeId(siteId),
              roots
            })),
            childrenOf,
            hosts: topology.map((n) => n.name),
            opened,
            // Unreachable is the consequence of a host down above it, which is
            // what is shown; it opens nothing by itself.
            troubled: new Set(
              topology.filter((topo) => attentionOf(topo) === 'down').map((topo) => topo.name)
            ),
            causes: new Set(
              topology.filter((topo) => topo.state === 'DOWN').map((topo) => topo.name)
            ),
            shownAnyway: drawnAnyway
          })
    const shown = folded ? topology.filter((n) => folded.visible.has(n.name)) : topology
    const wasDrawn = lastDrawn
    lastDrawn = folded?.visible ?? new Set()

    // --- Hosts. One the map has not seen before starts where the map
    // remembers it, so a reload preserves the operator's arrangement.
    const nodes: FNode[] = shown.map((topo) =>
      upsert(
        topo.name,
        {
          nodeType: 'host',
          state: topo.state,
          output: topo.output,
          bfsLevel: levels.get(topo.name) ?? 0,
          topo
        },
        (node) =>
          pin(
            node,
            freedAway.has(topo.name)
              ? undefined
              : (keptAway.get(topo.name) ?? savedPositions[topo.name])
          )
      )
    )

    // --- Services, plus one "+N more" stand-in per host whose service list the
    // backend truncated, so the operator can see there is more than is drawn.
    if (needsServices(layout)) {
      for (const topo of shown) {
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

    const topoByName = new Map(topology.map((n) => [n.name, n] as const))
    const siteOfRoot = new Map([...rootsBySite.keys()].map((id) => [siteNodeId(id), id]))
    const folds: FNode[] = (folded?.folds ?? []).map((fold) => {
      const parentTopo = topoByName.get(fold.parentId)
      const siteId = parentTopo
        ? siteOf(parentTopo)
        : (siteOfRoot.get(fold.parentId) ?? connectionId)
      const states = new Map<DonutSegment['state'], number>()
      const attention: Partial<Record<Attention, number>> = {}
      const pressing: FoldHost[] = []
      for (const member of fold.members) {
        const topo = topoByName.get(member)
        const needs = topo ? attentionOf(topo) : 'pending'
        const ring = RING_STATE[needs]
        states.set(ring, (states.get(ring) ?? 0) + 1)
        attention[needs] = (attention[needs] ?? 0) + 1
        if (needsAttention(needs)) {
          pressing.push({ name: member, needs })
        }
      }
      pressing.sort(
        (a, b) => attentionRank(b.needs) - attentionRank(a.needs) || byName(a.name, b.name)
      )
      return upsert(foldNodeId(fold.parentId), {
        nodeType: 'fold',
        state: ATTENTION_STATE[pressing[0]?.needs ?? 'none'],
        output: '',
        bfsLevel: parentTopo ? (levels.get(fold.parentId) ?? 0) + 1 : 0,
        siteId,
        moreCount: fold.members.length,
        foldParent: fold.parentId,
        foldParentName: parentTopo ? fold.parentId : siteId,
        foldStates: [...states].map(([state, value]) => ({ state, value })),
        foldAttention: attention,
        foldSummary: summarizeHosts(fold.members.flatMap((member) => topoByName.get(member) ?? [])),
        foldMembers: fold.members,
        foldFirst: pressing.slice(0, FOLD_FIRST)
      })
    })
    nodes.push(...folds)

    // A push arrives every few seconds and must not restart the simulation
    // unless something structural changed: a status-only update would otherwise
    // cost a full force relaxation, and the operator's layout would drift.
    const hostIds = new Set([...shown.map((n) => n.name), ...folds.map((n) => n.id)])
    const structurallyChanged =
      hostIds.size !== lastHostIds.size || [...hostIds].some((id) => !lastHostIds.has(id))
    lastHostIds = hostIds
    const names = new Set(topology.map((n) => n.name))
    const reshaped =
      !sameSet(names, lastNames) ||
      !sameMap(opened, lastOpened) ||
      // A search or filter that draws nothing new leaves the hosts where they are.
      ((problemsOnly !== lastProblemsOnly || !sameSet(asked, lastAsked)) &&
        !sameSet(lastDrawn, wasDrawn))
    lastNames = names
    lastTopology = topology
    lastOpened = opened
    lastAsked = asked
    lastProblemsOnly = problemsOnly

    // --- Site roots. A flat topology hangs its hosts under their site in a
    // half-disk; a tree starts beside its site.
    const siteIds: string[] = []
    const hostsBySite = new Map<string, FNode[]>()
    for (const node of nodes) {
      const siteId = node.topo ? siteOf(node.topo) : node.nodeType === 'fold' ? node.siteId : null
      if (!KIND_TRAITS[node.nodeType].hostShaped || !siteId) {
        continue
      }
      if (!hostsBySite.has(siteId)) {
        siteIds.push(siteId)
        hostsBySite.set(siteId, [])
      }
      hostsBySite.get(siteId)!.push(node)
    }
    // A hierarchy starts along its drawn tree, each site's roots under that
    // site, and each fold where the hosts it holds would have been.
    let tree: TreeLayout | undefined
    const drawnParent = new Map<string, string>()
    const drawnChildren = new Map<string, string[]>()
    if (folded) {
      // What needs attention first among siblings, in the order of
      // ``ATTENTIONS``; among equals, the one with the most urgent need
      // anywhere below it, drawn or folded, then the one with more below it
      // that needs attention; and the fold of the rest last.
      const needOf = new Map<string, Attention>()
      for (const id of folded.visible) {
        const topo = topoByName.get(id)
        needOf.set(id, topo ? attentionOf(topo) : 'none')
      }
      const urgency = (id: string): number => attentionRank(needOf.get(id) ?? 'none')
      const foldUnder = new Map(folds.map((fold) => [fold.foldParent!, fold] as const))
      const below = new Map<string, { rank: number; count: number }>()
      const belowOf = (id: string): { rank: number; count: number } => {
        const known = below.get(id)
        if (known) {
          return known
        }
        const fold = foldUnder.get(id)?.foldAttention
        const sum = { rank: attentionRank(worstIn(fold)), count: unhandledIn(fold) }
        for (const child of folded.children.get(id) ?? []) {
          const pressing = needsAttention(needOf.get(child) ?? 'none')
          const deeper = belowOf(child)
          sum.rank = Math.max(sum.rank, pressing ? urgency(child) : 0, deeper.rank)
          sum.count += (pressing ? 1 : 0) + deeper.count
        }
        below.set(id, sum)
        return sum
      }
      const byUrgency = (a: string, b: string): number =>
        urgency(b) - urgency(a) ||
        belowOf(b).rank - belowOf(a).rank ||
        belowOf(b).count - belowOf(a).count ||
        byName(a, b)
      for (const [parent, children] of folded.children) {
        drawnChildren.set(parent, [...children].sort(byUrgency))
      }
      for (const fold of folds) {
        drawnChildren.get(fold.foldParent!)?.push(fold.id)
      }
      for (const [parent, children] of drawnChildren) {
        for (const child of children) {
          drawnParent.set(child, parent)
        }
      }
      tree = treeLayout({
        rootGroups: siteIds.map((siteId) => drawnChildren.get(siteNodeId(siteId)) ?? []),
        childrenOf: drawnChildren,
        hosts: [...hostIds],
        opened: new Set(opened.keys()),
        footprint: (id) => {
          const topo = topoByName.get(id)
          return topo ? hostFootprint(topo, layout) : { width: FOLD_WIDTH, height: HOST_ROW }
        }
      })
    }
    const spread = Math.max(0, (siteIds.length - 1) * SITE_SPREAD)
    const flatSiteStart = (siteId: string, index: number): Position => ({
      // Clear of the dispersion a large group spreads over.
      x: siteIds.length === 1 ? 0 : -spread / 2 + (index * spread) / (siteIds.length - 1),
      y: -(
        SPIRAL_SPACING * Math.sqrt(Math.max(1, hostsBySite.get(siteId)?.length ?? 0)) +
        SITE_CLEARANCE
      )
    })
    const frames: HostFrame[] = []
    siteIds.forEach((siteId, index) => {
      // Above its own group of hosts. Once the operator drags a site the
      // position is theirs, and the remembered one is kept instead of
      // snapping back to this.
      const startsAt: Position = tree
        ? { x: tree.groupAt[index]!.x - tree.column, y: tree.groupAt[index]!.y }
        : flatSiteStart(siteId, index)
      const id = siteNodeId(siteId)
      const node = upsert(id, { nodeType: 'site', siteId, state: 'UP', output: '' }, (site) => {
        pin(site, savedPositions[id] ?? startsAt)
        if (tree && !savedPositions[id]) {
          siteLaidOutAt.set(id, startsAt)
        }
      })
      nodes.push(node)
      // --- A starting arrangement for the site's hosts that have no position
      // yet, so the first paint is already readable instead of a knot.
      // A tree the operator reshaped is laid out afresh, or an opened group
      // would land among hosts that kept their old places. What the operator
      // dragged stays where they put it.
      const siteHosts = hostsBySite.get(siteId) ?? []
      const placeless = siteHosts.filter(
        (n) => n.x === undefined || (tree && reshaped && !Number.isFinite(n.fx))
      )
      const afresh = reshaped || placeless.length === siteHosts.length
      // The site follows its trees whenever they are laid out afresh, unless the
      // operator put it somewhere.
      const laidOutAt = siteLaidOutAt.get(id)
      const putByOperator = laidOutAt
        ? node.fx !== laidOutAt.x || node.fy !== laidOutAt.y
        : savedPositions[id] !== undefined
      if (tree && afresh && !putByOperator) {
        pin(node, startsAt)
        siteLaidOutAt.set(id, startsAt)
      }
      if (tree) {
        frames.push({ head: node, members: siteHosts, opened: opened.has(id) })
        // Each host hangs right of its drawn parent as the tree has it, from
        // wherever that parent actually is: a site or host the operator put
        // somewhere, or one that kept its place through a change of state, so
        // an operator watching the map does not see every host move whenever
        // one goes down. Parents come first, being further left in the tree.
        const slotOf = (hostId: string): Position | undefined =>
          hostId === id ? startsAt : tree.at.get(hostId)
        for (const host of placeless.sort((a, b) => slotOf(a.id)!.x - slotOf(b.id)!.x)) {
          const slot = slotOf(host.id)!
          const parent = store.get(drawnParent.get(host.id) ?? '')
          const parentSlot = parent && slotOf(parent.id)
          const follows = parentSlot && Number.isFinite(parent.x) && Number.isFinite(parent.y)
          host.x = follows ? parent.x! + slot.x - parentSlot.x : slot.x
          host.y = follows ? parent.y! + slot.y - parentSlot.y : slot.y
          // One that a change of state shows joins its siblings where they
          // are, in a free place, rather than where a fresh layout would put
          // it, among them.
          const placedOthers = (ids: readonly string[]): Position[] =>
            ids.flatMap((other) => {
              const at = store.get(other)
              return at && at !== host && placed(at) ? [{ x: at.x, y: at.y }] : []
            })
          let free: Position | undefined
          if (!afresh && parent?.nodeType === 'host') {
            free = freeCellBeside(placedOthers(drawnChildren.get(parent.id) ?? []), HOST_ROW)
          } else if (!afresh && parent) {
            // A top-level host goes below the site's trees, in the column of
            // their roots.
            const roots = placedOthers(drawnChildren.get(parent.id) ?? [])
            const all = placedOthers(siteHosts.map((other) => other.id))
            free = roots.length
              ? {
                  x: Math.min(...roots.map((at) => at.x)),
                  y: Math.max(...all.map((at) => at.y)) + HOST_ROW
                }
              : undefined
          }
          if (free) {
            host.x = free.x
            host.y = free.y
          }
        }
      } else if (isMostlyFlat) {
        preLayoutHostsBelowSite(
          { x: node.x ?? startsAt.x, y: node.y ?? startsAt.y },
          placeless,
          HOST_SITE_GAP
        )
      }
    })
    // A hierarchy drawn as a network starts as one spiral, which the forces
    // pull into its layers.
    if (!tree && !isMostlyFlat) {
      preLayoutHosts(nodes.filter((n) => n.nodeType === 'host' && n.x === undefined))
    }

    const anchorX = new Map<string, number>()
    const anchorY = new Map<string, number>()
    for (const node of nodes) {
      if (KIND_TRAITS[node.nodeType].hostShaped) {
        anchorX.set(node.id, finiteOr(node.x))
        anchorY.set(node.id, finiteOr(node.y))
      }
    }

    // Forget what the topology no longer contains, so the store does not grow
    // with every host that has ever been on the map.
    const present = new Set(nodes.map((n) => n.id))
    for (const [id, node] of store) {
      if (present.has(id)) {
        continue
      }
      if (node.nodeType === 'host' && Number.isFinite(node.fx) && Number.isFinite(node.fy)) {
        keptAway.set(id, { x: node.fx as number, y: node.fy as number })
      }
      store.delete(id)
    }
    for (const id of freedAway) {
      if (present.has(id) || !(id in savedPositions)) {
        freedAway.delete(id)
      }
    }
    for (const id of keptAway.keys()) {
      if (present.has(id) || !names.has(id)) {
        keptAway.delete(id)
      }
    }
    for (const [id, at] of Object.entries(savedPositions)) {
      if (names.has(id) && !present.has(id) && !freedAway.has(id) && !keptAway.has(id)) {
        keptAway.set(id, at)
      }
    }

    const byId = new Map(nodes.map((n) => [n.id, n] as const))
    if (tree) {
      for (const id of opened.keys()) {
        const head = byId.get(id)
        if (head?.nodeType === 'host') {
          frames.push({ head, members: descendants(id, drawnChildren, byId), opened: true })
        }
      }
    }

    // A drag on a host frees its whole subtree — a descendant still pinned from
    // an earlier drag would otherwise stay put and make the spring look broken.
    // The site roots are added to the same index below, so a site drag does it
    // for its hosts too.
    const addChild = (parent: string, child: string): void => {
      const children = childrenOf.get(parent) ?? []
      children.push(child)
      childrenOf.set(parent, children)
    }

    const elbows = new Map<string, Elbow>()
    if (tree) {
      for (const [parentId, childIds] of drawnChildren) {
        const parent = byId.get(parentId)
        const children = childIds.map((id) => byId.get(id)).filter(placed)
        if (placed(parent)) {
          for (const [id, elbow] of elbowsOf(parent, children, HOST_ROW, tree.reach)) {
            elbows.set(id, elbow)
          }
        }
      }
    }
    const links: FLink[] = []
    // In a tree a spring rests at the length it has, so the forces keep the
    // layout instead of pulling parents and children together.
    const connect = (
      source: FNode,
      target: FNode,
      isServiceLink: boolean,
      furtherParent = false
    ): void => {
      const tied = tree && !isServiceLink && placed(source) && placed(target)
      const elbow = drawnParent.get(target.id) === source.id ? elbows.get(target.id) : undefined
      links.push({
        source,
        target,
        sourceState: source.state,
        isServiceLink,
        ...(tied ? { restLength: Math.hypot(target.x! - source.x!, target.y! - source.y!) } : {}),
        ...(elbow ? { elbow } : {}),
        ...(furtherParent ? { furtherParent } : {})
      })
    }
    for (const topo of shown) {
      const target = byId.get(topo.name)
      for (const parent of topo.parents) {
        const source = byId.get(parent)
        if (source && target) {
          connect(source, target, false, tree && drawnParent.get(target.id) !== source.id)
        }
      }
    }
    // Site → host. Only the top-level hosts hang off the site; the ones below
    // already have a visual chain through their parents. In a tree the site's
    // edges run like a host's to its children, its fold included; otherwise
    // the link carries no state of its own, hence the fixed one.
    if (siteIds.length > 0) {
      const attached = isMostlyFlat ? shown : shown.filter((n) => n.parents.length === 0)
      for (const topo of attached) {
        const id = siteNodeId(siteOf(topo))
        addChild(id, topo.name)
        const source = byId.get(id)
        const target = byId.get(topo.name)
        if (source && target && !tree) {
          links.push({ source, target, sourceState: 'UP', isServiceLink: false })
        }
      }
    }
    if (tree) {
      for (const siteId of siteIds) {
        const site = byId.get(siteNodeId(siteId))
        for (const child of drawnChildren.get(siteNodeId(siteId)) ?? []) {
          const target = byId.get(child)
          if (site && target) {
            connect(site, target, false)
          }
        }
      }
    }
    for (const fold of folds) {
      const source = byId.get(fold.foldParent ?? '')
      if (source && source.nodeType !== 'site') {
        connect(source, fold, false)
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
      startsAsTree: tree !== undefined,
      frames,
      vSpacing,
      structurallyChanged
    }
  }

  /** Where the operator has pinned hosts and sites, for the map to remember. */
  function pinnedPositions(): Record<string, Position> {
    const positions: Record<string, Position> = {}
    for (const [id, at] of keptAway) {
      positions[id] = at
    }
    for (const node of store.values()) {
      if (node.nodeType !== 'host' && node.nodeType !== 'site') {
        continue
      }
      if (!Number.isFinite(node.fx) || !Number.isFinite(node.fy)) {
        continue
      }
      // A site where the tree layout put it follows its trees; only one the
      // operator moved is remembered.
      const laidOutAt = siteLaidOutAt.get(node.id)
      if (laidOutAt && node.fx === laidOutAt.x && node.fy === laidOutAt.y) {
        continue
      }
      positions[node.id] = { x: node.fx as number, y: node.fy as number }
    }
    return positions
  }

  /**
   * Frees a host's descendants, so a drag on it can pull them along — those
   * folded away too, which would otherwise come back where they were.
   */
  function unpinDescendants(rootId: string, childrenOf: ReadonlyMap<string, string[]>): void {
    // Built per drag, not per update: only a drag needs the hosts it does not draw.
    const below = new Map([...childrenOf].map(([id, children]) => [id, [...children]]))
    for (const topo of lastTopology) {
      for (const parent of topo.parents) {
        const children = below.get(parent) ?? []
        children.push(topo.name)
        below.set(parent, children)
      }
    }
    const seen = new Set<string>()
    const queue = [rootId]
    for (let i = 0; i < queue.length; i++) {
      for (const childId of below.get(queue[i]!) ?? []) {
        if (seen.has(childId)) {
          continue
        }
        seen.add(childId)
        queue.push(childId)
        const child = store.get(childId)
        if (child) {
          child.fx = null
          child.fy = null
        } else if (keptAway.delete(childId)) {
          freedAway.add(childId)
        }
      }
    }
  }

  /** Start over: a different map, or a different root for this one. */
  function clear(): void {
    store.clear()
    lastDrawn = new Set()
    siteLaidOutAt = new Map()
    keptAway = new Map()
    freedAway = new Set()
    lastTopology = []
  }

  /**
   * What a switch of service layout invalidates. The service nodes go, because
   * the new layout places them from scratch. A host the operator has not
   * dragged loses its position too: the layouts need very different room around
   * a host, and carrying a donut-tight spiral into a fan makes the rings
   * overlap. A dragged host keeps its place — that one is the operator's —
   * and a tree is laid out afresh around it, as the hosts that kept a place
   * would otherwise hold the moved ones to the old one.
   */
  function forgetLayout(from: ServiceLayout, to: ServiceLayout): void {
    lastNames = new Set()
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

/** The nodes below ``id`` in the drawn tree. */
function descendants(
  id: string,
  children: ReadonlyMap<string, readonly string[]>,
  byId: ReadonlyMap<string, FNode>
): FNode[] {
  const found: FNode[] = []
  const queue = [...(children.get(id) ?? [])]
  for (let i = 0; i < queue.length; i++) {
    const node = byId.get(queue[i]!)
    if (node) {
      found.push(node)
    }
    queue.push(...(children.get(queue[i]!) ?? []))
  }
  return found
}

/** Whether two maps hold the same entries. */
function sameMap<V>(a: ReadonlyMap<string, V>, b: ReadonlyMap<string, V>): boolean {
  if (a.size !== b.size) {
    return false
  }
  for (const [key, value] of a) {
    if (b.get(key) !== value) {
      return false
    }
  }
  return true
}

/** Whether two sets hold the same members. */
export function sameSet(a: ReadonlySet<string>, b: ReadonlySet<string>): boolean {
  if (a.size !== b.size) {
    return false
  }
  for (const id of a) {
    if (!b.has(id)) {
      return false
    }
  }
  return true
}

/**
 * The hosts a map showing only problems draws wherever they hang: those not up,
 * or with a service in trouble. No more than half the budget, the worst first;
 * the folds' rings still count the rest.
 */
function withProblems(topology: readonly TopologyNode[]): string[] {
  return topology
    .filter((topo) => topo.state !== 'UP' || worstServiceState(topo.services_summary) !== null)
    .sort((a, b) => problemScoreFromTopo(b) - problemScoreFromTopo(a))
    .slice(0, VISIBLE_HOSTS / 2)
    .map((topo) => topo.name)
}

/** The hosts a fold's hover card names, the ones that need attention first. */
const FOLD_FIRST = 3

function byName(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0
}

/** A fold's ring: its hosts by what they need, a handled problem quieter than one that is not. */
const RING_STATE: Record<Attention, DonutSegment['state']> = {
  down: 'CRITICAL',
  critical: 'CRITICAL',
  unreachable: 'UNKNOWN',
  unknown: 'UNKNOWN',
  warning: 'WARNING',
  handled: 'PENDING',
  pending: 'PENDING',
  none: 'OK'
}

/** The room a host takes in the tree start: its label, and the ring of services it draws. */
function hostFootprint(topo: TopologyNode, layout: ServiceLayout): Footprint {
  const label = hostColumnWidth(topo.name)
  const N = needsServices(layout)
    ? (topo.services?.length ?? 0) + ((topo.services_truncated_count ?? 0) > 0 ? 1 : 0)
    : 0
  if (N === 0) {
    return { width: label, height: HOST_ROW + (hostLabelLines(topo.name).length - 1) * LABEL_LINE }
  }
  const reach = serviceReach(
    layout,
    N,
    rowColumnGuess((topo.services ?? []).map((service) => service.name))
  )
  const width = Math.max(label, reach * 2)
  if (layout === 'fan') {
    return { width, height: NODE_R + reach + 30 }
  }
  if (layout === 'orbit') {
    return { width, height: reach * 2 }
  }
  const columns = rowColumns(N)
  return { width, height: NODE_R + 40 + Math.ceil(N / columns) * (svcR(N) * 2 + 26) }
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
