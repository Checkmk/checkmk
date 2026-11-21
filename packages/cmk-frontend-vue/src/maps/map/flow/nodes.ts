/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * What a flow map draws, as the rest of the map type sees it.
 *
 * The graph builds these, the forces arrange them, the painter draws them and
 * the view opens things on them — so they live in a module of their own rather
 * than in whichever of those happened to need them first.
 *
 * They extend d3's own simulation types, because the simulation writes its
 * positions and velocities straight onto them.
 */
import type { SimulationLinkDatum, SimulationNodeDatum } from 'd3-force'

import type { Attention } from '@/maps/map/flow/attention'
import type { DonutSegment } from '@/maps/map/flow/geometry'
import type { FlowNodeKind } from '@/maps/map/flow/nodeIds'
import type { ServiceNode, ServicesSummary, TopologyNode } from '@/maps/types/api'

/** A host of a folded group, by what it needs of the operator. */
export interface FoldHost {
  name: string
  needs: Attention
}

/** One thing on a flow map: a host, one of its services, a stand-in for the
 *  services it does not show, a fold for the hosts it does not draw, or the
 *  root of a site. */
export interface FNode extends SimulationNodeDatum {
  id: string
  state: string
  output: string
  bfsLevel: number
  nodeType: FlowNodeKind
  /** The host this hangs off, on a service or "+N more" node. */
  hostId?: string
  siteId?: string
  /** How many services the host has in total — what decides label visibility. */
  svcTotalCount?: number
  /** How many services a "+N more" node stands in for. */
  moreCount?: number
  /** The host or site root a folded group of hosts hangs off. */
  foldParent?: string
  /** That parent as the operator knows it: the host's name, or the site's. */
  foldParentName?: string | undefined
  /** How many hosts of each state a folded group holds, for its ring. */
  foldStates?: DonutSegment[]
  /** How many hosts a folded group holds by what they need of the operator. */
  foldAttention?: Partial<Record<Attention, number>>
  /** A folded group's hosts and their services by state, summed as for a site. */
  foldSummary?: { hosts: ServicesSummary; services: ServicesSummary }
  /** Every host a folded group holds. */
  foldMembers?: string[]
  /** The hosts of a folded group that need attention first, a few at most. */
  foldFirst?: FoldHost[]
  /**
   * The host's own topology entry, so a hover card can show the same status
   * detail as a static map. Set on host nodes; a service reaches its host's
   * through ``parentTopo``.
   */
  topo?: TopologyNode
  svc?: ServiceNode
  parentTopo?: TopologyNode
  // d3-force writes x / y / vx / vy.
}

/**
 * A framed group of hosts in a tree: a site's, or the hosts the operator opened
 * under a host. The frame shows what belongs together; a site's moves with the
 * site, and an opened one folds back.
 */
export interface HostFrame {
  /** The site or host the group belongs to, which heads the frame. */
  head: FNode
  /** The hosts and folds below it in the drawn tree. */
  members: FNode[]
  /** Whether the operator opened it, so it can be folded back. */
  opened: boolean
}

/**
 * A tree edge runs at right angles, so a parent's edges share one line rather
 * than fanning out across its children: out to ``rise`` before its children's
 * first column, ``drop`` beside the parent, along it, and across to the child,
 * ``aside`` off the child's row when it sits further along a grid.
 */
export interface Elbow {
  drop: number
  aside: number
  /** How far left of a column its edges run: in the gap, clear of the names. */
  rise: number
  /** How far left of the child its edge comes down to it. */
  reach: number
}

/** An edge between two of them. */
export interface FLink extends SimulationLinkDatum<FNode> {
  source: FNode
  target: FNode
  sourceState: string
  /** Service edges are placed geometrically, not sprung by the simulation. */
  isServiceLink: boolean
  /** How long the tree start drew this edge, which its spring rests at. */
  restLength?: number
  elbow?: Elbow
  /** In a tree: from a parent other than the one the host hangs under. */
  furtherParent?: boolean
}

/** A badge in a node's corner, saying a command is in force on it. */
export interface CmdMarker {
  key: string
  glyph: string
  fill: string
  fg: string
  title: string
  corner: 'tr' | 'tl' | 'br'
}
