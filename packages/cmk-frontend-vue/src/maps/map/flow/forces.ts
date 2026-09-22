/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The forces that arrange a flow map's hosts.
 *
 * Only hosts and site roots take part. A host's services already have their
 * places from ``placeServiceNodes``, so charge and collide skip them — with a
 * few hundred hosts carrying twenty services each, letting them into the
 * simulation costs most of the tick budget and buys nothing.
 *
 * Every strength here is a compromise between two readings of the same map.
 * Without services on show, the severity spiral is what makes the map legible,
 * so the anchor that holds it wins. With services on show, the rings around the
 * worst hosts are wide, so the anchor gives way and lets collide push
 * neighbours aside. Hence the ``needsServices`` branch in nearly all of them.
 */
import {
  type Simulation,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY
} from 'd3-force'

import { NODE_R, svcR } from '@/maps/map/flow/geometry'
import { layoutR, needsServices, rowColumns, showsDonut } from '@/maps/map/flow/layout'
import type { FLink, FNode } from '@/maps/map/flow/nodes'
import type { ServiceLayout } from '@/maps/types/api'

export interface FlowForcesOptions {
  nodes: FNode[]
  /** Host↔host and site→host edges. Service edges are laid out, not sprung. */
  springLinks: FLink[]
  /** A host's service and "+N more" nodes, by host id. */
  servicesByHost: ReadonlyMap<string, unknown[]>
  layout: ServiceLayout
  /** Deepest BFS level in the topology; 0 means it is flat. */
  maxLvl: number
  /** Vertical gap between BFS layers. */
  vSpacing: number
  /** Where the pre-layout put each host — what the anchor pulls back towards. */
  anchorX: ReadonlyMap<string, number>
  anchorY: ReadonlyMap<string, number>
  /** Measured row-grid column widths, by host id. */
  rowSpacings: ReadonlyMap<string, number>
}

/** Site links pull softly, so the pre-layout still wins at rest. */
const SITE_LINK_STRENGTH = 0.08
const HOST_LINK_STRENGTH = 0.4
/** How hard a BFS hierarchy holds its hosts on their own layer. */
const LAYER_STRENGTH = 0.4
/** Full grip on the severity spiral; a fraction of it once rings are on show. */
const ANCHOR_STRENGTH = 0.18
const ANCHOR_STRENGTH_WITH_SERVICES = 0.06

/**
 * Builds the simulation, stopped. The caller decides how much energy to give
 * it: a first paint needs a full relaxation, a status-only update needs none.
 */
export function createFlowSimulation(options: FlowForcesOptions): Simulation<FNode, undefined> {
  const {
    nodes,
    springLinks,
    servicesByHost,
    layout,
    maxLvl,
    vSpacing,
    anchorX,
    anchorY,
    rowSpacings
  } = options
  const withServices = needsServices(layout)
  const serviceCount = (id: string): number => servicesByHost.get(id)?.length ?? 0

  /** How hard a host is held at its pre-layout slot. */
  const anchorStrength = (node: FNode): number => {
    if (node.nodeType !== 'host') {
      return 0
    }
    if (!withServices) {
      return ANCHOR_STRENGTH
    }
    // A host that actually draws a service ring is left free, so charge and
    // collide can disperse it instead of the anchor yanking it back.
    return serviceCount(node.id) > 0 ? 0 : ANCHOR_STRENGTH_WITH_SERVICES
  }

  return (
    forceSimulation<FNode>(nodes)
      .force(
        'link',
        forceLink<FNode, FLink>(springLinks)
          .id((d) => d.id)
          .distance((link) => linkDistance(link, layout, serviceCount))
          .strength((link) => (isSiteLink(link) ? SITE_LINK_STRENGTH : HOST_LINK_STRENGTH))
      )
      .force(
        'charge',
        forceManyBody<FNode>().strength((node) => {
          if (node.nodeType !== 'host') {
            return 0
          }
          // On a flat map without service rings the severity spiral already
          // spreads the hosts evenly; all-to-all repulsion would only beat the
          // anchor and flatten the rings into a wide ellipse.
          if (maxLvl === 0 && !withServices) {
            return 0
          }
          const N = serviceCount(node.id)
          return N > 0 ? -Math.max(700, layoutR(layout, N) * 9) : -600
        })
      )
      .force(
        'center',
        forceX<FNode>((node) =>
          node.nodeType === 'host' ? (anchorX.get(node.id) ?? 0) : 0
        ).strength(anchorStrength)
      )
      .force(
        'collide',
        forceCollide<FNode>((node) =>
          collideRadius(node, layout, serviceCount, rowSpacings)
        ).iterations(withServices ? 5 : maxLvl > 0 ? 3 : 1)
      )
      .force(
        'y',
        // A real hierarchy keeps the layered look; a flat topology holds each
        // host at its severity slot instead, so the pre-layout survives.
        maxLvl > 0
          ? forceY<FNode>((node) => (node.bfsLevel - maxLvl / 2) * vSpacing).strength((node) =>
              node.nodeType === 'service' ? 0 : LAYER_STRENGTH
            )
          : forceY<FNode>((node) =>
              node.nodeType === 'host' ? (anchorY.get(node.id) ?? 0) : 0
            ).strength(anchorStrength)
      )
      // A flat map starts close to its steady state, so it can cool fast. A real
      // hierarchy needs time to settle its layers, and service-aware layouts need
      // it too, because collide has to push the wide rings apart from a
      // donut-tight start.
      .alphaDecay(maxLvl > 0 || withServices ? 0.05 : 0.1)
      .stop()
  )
}

function isSiteLink(link: FLink): boolean {
  return link.source.nodeType === 'site' || link.target.nodeType === 'site'
}

function linkDistance(
  link: FLink,
  layout: ServiceLayout,
  serviceCount: (id: string) => number
): number {
  const { source, target } = link
  // Site → host: scale with the host's service ring, so a dense top-K host
  // does not end up sitting on the site box.
  if (isSiteLink(link)) {
    const host = source.nodeType === 'site' ? target : source
    const N = serviceCount(host.id)
    return N > 0 ? Math.max(220, layoutR(layout, N) + 80) : 220
  }
  const sourceN = serviceCount(source.id)
  const targetN = serviceCount(target.id)
  if (sourceN === 0 && targetN === 0) {
    return 160
  }
  return Math.max(200, layoutR(layout, sourceN) + layoutR(layout, targetN) + 60)
}

function collideRadius(
  node: FNode,
  layout: ServiceLayout,
  serviceCount: (id: string) => number,
  rowSpacings: ReadonlyMap<string, number>
): number {
  if (node.nodeType === 'service') {
    return 0
  }
  if (node.nodeType === 'site') {
    return 70
  }
  const N = serviceCount(node.id)
  if (N === 0 || !needsServices(layout)) {
    // The ring sits on the host itself, so its width has to be reserved — by
    // the same rule that decides whether it is drawn at all.
    return showsDonut(layout, node.topo?.services_omitted) ? NODE_R + 14 : NODE_R + 10
  }
  if (layout === 'fan' || layout === 'orbit') {
    return layoutR(layout, N) + svcR(N) + 35
  }
  return (rowColumns(N) / 2) * (rowSpacings.get(node.id) ?? 60) + svcR(N) + 20
}
