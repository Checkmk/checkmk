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

import type { TopologyNode } from '@/maps/types/api'

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
