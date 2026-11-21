/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * How big the things a flow map draws are, and where the parts of a host sit.
 *
 * A flow map is drawn from a live topology, so nothing on it has a place the
 * operator gave it: every radius, ring width and label offset is derived from
 * how much there is to show. Two of them also depend on the zoom, because they
 * have to stay readable when a few hundred hosts are fitted into one screen.
 *
 * Kept apart from the drawing so the sizes can be reasoned about — and tested —
 * without a DOM.
 */
import { arc as d3arc, pie as d3pie } from 'd3-shape'

import type { FNode } from '@/maps/map/flow/nodes'
import type { ServicesSummary, TopologyNode } from '@/maps/types/api'

export const NODE_R = 18
export const SVC_R_MAX = 11 // service node radius at low service count
export const ORBIT_R_MIN = 80 // minimum orbit/fan radius

// A NaN position reaching a geometry attr makes d3 abort the render; a NaN in
// the zoom transform corrupts d3-zoom and floods every later frame. `?? 0`
// doesn't catch NaN, so coordinates are funnelled through these guards.
export const finiteOr = (v: unknown, fallback = 0): number =>
  typeof v === 'number' && Number.isFinite(v) ? v : fallback
export const firstFinite = (a: unknown, b: unknown): number => finiteOr(a, finiteOr(b, NaN))

export function svcR(N: number): number {
  if (N <= 6) {
    return SVC_R_MAX
  }
  if (N <= 12) {
    return 9
  }
  if (N <= 20) {
    return 7
  }
  return 6
}

/** How big a host or service node is drawn. */
export function nodeRadius(node: FNode): number {
  return node.nodeType === 'service' ? svcR(node.svcTotalCount ?? 1) : NODE_R
}

// Scale orbit radius up so service circles don't overlap.
// Full circle circumference = 2π·R must fit N circles of diameter 2r+gap.
export function orbitR(N: number): number {
  const r = svcR(N)
  return Math.max(ORBIT_R_MIN, Math.ceil((N * (r * 2 + 3)) / (2 * Math.PI)))
}

// Fan = semicircle below host. Arc length = FAN_SPREAD·R must fit N service
// circles spaced 2r+gap apart, so the radius scales like ~2× orbitR for large N.
export const FAN_SPREAD = Math.PI * 0.9
export function fanR(N: number): number {
  const r = svcR(N)
  if (N <= 1) {
    return ORBIT_R_MIN
  }
  return Math.max(ORBIT_R_MIN, Math.ceil(((N - 1) * (r * 2 + 3)) / FAN_SPREAD))
}

export function showSvcLabel(N: number): boolean {
  return N <= 10
}

// Donut ring around a host: aggregated services_summary as proportional arcs.
// Width grows inversely with zoom so the ring stays ≥ DONUT_MIN_SCREEN_PX on
// fit-to-view of dense maps — otherwise an 8 model-px ring collapses to <2 px
// screen at scale ~0.2 and the entire status aggregate becomes invisible.
const DONUT_INNER = NODE_R + 3
const DONUT_BASE_WIDTH = 8
const DONUT_MIN_SCREEN_PX = 4
export const DONUT_MAX_WIDTH = 24
export function donutOuterRadius(zoomK: number): number {
  const widthForMinScreen = DONUT_MIN_SCREEN_PX / Math.max(finiteOr(zoomK, 1), 0.0001)
  const width = Math.min(DONUT_MAX_WIDTH, Math.max(DONUT_BASE_WIDTH, widthForMinScreen))
  return DONUT_INNER + width
}
export type DonutSegment = {
  state: 'OK' | 'WARNING' | 'CRITICAL' | 'UNKNOWN' | 'PENDING'
  value: number
}
export type DonutArc = { startAngle: number; endAngle: number }
export function buildDonutArc(zoomK: number) {
  return d3arc<DonutArc>().innerRadius(DONUT_INNER).outerRadius(donutOuterRadius(zoomK))
}
/**
 * A folded group's ring: a thin line of the states it holds, so the group reads
 * as several hosts without its share of warnings outshouting a host that is down.
 */
export const foldArc = d3arc<DonutArc>()
  .innerRadius(NODE_R + 2)
  .outerRadius(NODE_R + 5)
export const donutPie = d3pie<DonutSegment>()
  .sort(null)
  .value((d) => d.value)

export const HEALTHY_HOST_STATES = new Set(['UP', 'OK', 'PENDING'])

export function problemScoreFromTopo(n: TopologyNode): number {
  const hostPenalty = HEALTHY_HOST_STATES.has(n.state) ? 0 : 100
  const s = n.services_summary
  if (!s) {
    return hostPenalty
  }
  return hostPenalty + s.critical * 4 + s.warning * 2 + s.unknown * 2
}

/**
 * For each host down, how many hosts are unreachable because of it: through
 * any of their parents that are not up, and the unreachable ones above those.
 * Each host's hosts down are worked out once, so a long chain stays linear.
 */
export function cutOffBy(topology: readonly TopologyNode[]): Map<string, number> {
  const hosts = new Map(topology.map((topo) => [topo.name, topo] as const))
  const downAbove = new Map<string, ReadonlySet<string>>()
  const parentsOutOf = (topo: TopologyNode): TopologyNode[] =>
    topo.parents.flatMap((name) => {
      const parent = hosts.get(name)
      return parent && (parent.state === 'DOWN' || parent.state === 'UNREACHABLE') ? [parent] : []
    })
  // Depth first without recursion, so a long chain cannot overflow the stack;
  // a parent cycle is cut where it closes.
  const resolve = (start: TopologyNode): ReadonlySet<string> => {
    const entered = new Set<string>()
    const stack = [start]
    while (stack.length) {
      const topo = stack[stack.length - 1]!
      if (downAbove.has(topo.name)) {
        stack.pop()
      } else if (!entered.has(topo.name)) {
        entered.add(topo.name)
        for (const parent of parentsOutOf(topo)) {
          if (parent.state === 'UNREACHABLE' && !entered.has(parent.name)) {
            stack.push(parent)
          }
        }
      } else {
        const down = new Set<string>()
        for (const parent of parentsOutOf(topo)) {
          if (parent.state === 'DOWN') {
            down.add(parent.name)
          } else {
            downAbove.get(parent.name)?.forEach((host) => down.add(host))
          }
        }
        downAbove.set(topo.name, down)
        stack.pop()
      }
    }
    return downAbove.get(start.name)!
  }
  const cutOff = new Map<string, number>()
  for (const topo of topology) {
    if (topo.state === 'UNREACHABLE') {
      for (const host of resolve(topo)) {
        cutOff.set(host, (cutOff.get(host) ?? 0) + 1)
      }
    }
  }
  return cutOff
}

/**
 * The host down nearest above ``name``, through parents that are unreachable:
 * ``name`` itself if it is down. Null where nothing down cuts it off.
 */
export function hostDownAbove(name: string, topology: readonly TopologyNode[]): string | null {
  const hosts = new Map(topology.map((topo) => [topo.name, topo] as const))
  const seen = new Set([name])
  for (let level = [name]; level.length; ) {
    const next: string[] = []
    for (const id of [...level].sort()) {
      const topo = hosts.get(id)
      if (topo?.state === 'DOWN') {
        return id
      }
      if (topo?.state !== 'UNREACHABLE') {
        continue
      }
      for (const parent of topo.parents) {
        if (!seen.has(parent)) {
          seen.add(parent)
          next.push(parent)
        }
      }
    }
    level = next
  }
  return null
}

/**
 * The ``count`` hosts worst affected: a host down weighs as much again for each
 * host unreachable because of it, and an unreachable host, the consequence,
 * not at all. Among equals, the first by name, so the choice does not flicker.
 */
export function worstAffected(
  topology: readonly TopologyNode[],
  count: number,
  cutOff: ReadonlyMap<string, number> = cutOffBy(topology)
): Set<string> {
  const score = (topo: TopologyNode): number =>
    topo.state === 'UNREACHABLE'
      ? 0
      : problemScoreFromTopo(topo) * (1 + (cutOff.get(topo.name) ?? 0))
  return new Set(
    topology
      .map((topo) => ({ id: topo.name, score: score(topo) }))
      .filter((scored) => scored.score > 0)
      .sort((a, b) => b.score - a.score || byName(a.id, b.id))
      .slice(0, count)
      .map((scored) => scored.id)
  )
}

/** The worst state any of a host's services is in, or ``null`` when all are fine. */
export function worstServiceState(
  summary: ServicesSummary | null | undefined
): 'CRITICAL' | 'UNKNOWN' | 'WARNING' | null {
  if (summary?.critical) {
    return 'CRITICAL'
  }
  if (summary?.unknown) {
    return 'UNKNOWN'
  }
  return summary?.warning ? 'WARNING' : null
}

/**
 * A group of hosts summed up as the daemon sums a group: its hosts' states in
 * the service slots (UP as ok, DOWN as critical, UNREACHABLE as unknown), and
 * its hosts' services.
 */
export function summarizeHosts(topos: Iterable<TopologyNode>): {
  hostCount: number
  hosts: ServicesSummary
  services: ServicesSummary
} {
  let hostCount = 0
  const hosts = { ok: 0, warning: 0, critical: 0, unknown: 0, pending: 0 }
  const services = { ok: 0, warning: 0, critical: 0, unknown: 0, pending: 0 }
  for (const n of topos) {
    hostCount++
    if (n.state === 'UP') {
      hosts.ok++
    } else if (n.state === 'DOWN') {
      hosts.critical++
    } else if (n.state === 'UNREACHABLE') {
      hosts.unknown++
    } else if (n.state === 'PENDING') {
      hosts.pending++
    }
    const s = n.services_summary
    if (s) {
      services.ok += s.ok
      services.warning += s.warning
      services.critical += s.critical
      services.unknown += s.unknown
      services.pending += s.pending
    }
  }
  return { hostCount, hosts, services }
}

// Severity rank: 2 = critical/down, 1 = warn/unknown, 0 = ok.
// Used for the initial spiral pre-layout (problems toward the center) and
// for severity-stratified forceX/forceY targets so high-severity hosts stay
// near origin instead of getting flung to the rim by charge alone.
export function severityRank(n: TopologyNode | undefined): 0 | 1 | 2 {
  if (!n) {
    return 0
  }
  if (!HEALTHY_HOST_STATES.has(n.state)) {
    return 2
  }
  const s = n.services_summary
  if (!s) {
    return 0
  }
  if (s.critical > 0) {
    return 2
  }
  if (s.warning > 0 || s.unknown > 0) {
    return 1
  }
  return 0
}

/** The order hosts with nothing else between them are drawn and listed in. */
export function byName(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0
}
