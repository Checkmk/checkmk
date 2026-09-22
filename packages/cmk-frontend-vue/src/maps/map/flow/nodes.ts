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

import type { FlowNodeKind } from '@/maps/map/flow/nodeIds'
import type { ServiceNode, TopologyNode } from '@/maps/types/api'

/** One thing on a flow map: a host, one of its services, a stand-in for the
 *  services it does not show, or the root of a site. */
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

/** An edge between two of them. */
export interface FLink extends SimulationLinkDatum<FNode> {
  source: FNode
  target: FNode
  sourceState: string
  /** Service edges are placed geometrically, not sprung by the simulation. */
  isServiceLink: boolean
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
