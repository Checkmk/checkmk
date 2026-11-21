/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  DONUT_MAX_WIDTH,
  ORBIT_R_MIN,
  SVC_R_MAX,
  cutOffBy,
  donutOuterRadius,
  fanR,
  finiteOr,
  firstFinite,
  hostDownAbove,
  orbitR,
  problemScoreFromTopo,
  severityRank,
  showSvcLabel,
  svcR,
  worstAffected
} from '@/maps/map/flow/geometry'
import type { ServicesSummary, TopologyNode } from '@/maps/types/api'

import { aTopologyNode } from '../../support/fixtures'

function summary(extra: Partial<ServicesSummary> = {}): ServicesSummary {
  return { ok: 0, warning: 0, critical: 0, unknown: 0, pending: 0, ...extra }
}

function node(state: string, servicesSummary: ServicesSummary | null = null): TopologyNode {
  return aTopologyNode({ name: 'h', state, services_summary: servicesSummary })
}

describe('finiteOr', () => {
  it('passes finite numbers through', () => {
    expect(finiteOr(5)).toBe(5)
    expect(finiteOr(-2.5)).toBe(-2.5)
  })

  it('replaces NaN, Infinity and non-numbers with the fallback', () => {
    expect(finiteOr(NaN)).toBe(0)
    expect(finiteOr(Infinity)).toBe(0)
    expect(finiteOr('7')).toBe(0)
    expect(finiteOr(undefined, 9)).toBe(9)
  })
})

describe('firstFinite', () => {
  it('returns the first finite of the two candidates', () => {
    expect(firstFinite(3, 4)).toBe(3)
    expect(firstFinite(NaN, 4)).toBe(4)
  })

  it('returns NaN when neither candidate is finite', () => {
    expect(Number.isNaN(firstFinite(NaN, 'x'))).toBe(true)
  })
})

describe('svcR', () => {
  it('shrinks the service radius as the count grows', () => {
    expect(svcR(1)).toBe(SVC_R_MAX)
    expect(svcR(6)).toBe(SVC_R_MAX)
    expect(svcR(7)).toBe(9)
    expect(svcR(12)).toBe(9)
    expect(svcR(20)).toBe(7)
    expect(svcR(21)).toBe(6)
  })
})

describe('orbitR and fanR', () => {
  it('never drop below the minimum orbit radius', () => {
    expect(orbitR(1)).toBe(ORBIT_R_MIN)
    expect(fanR(1)).toBe(ORBIT_R_MIN)
  })

  it('grow with the service count', () => {
    expect(orbitR(50)).toBeGreaterThan(ORBIT_R_MIN)
    expect(fanR(50)).toBeGreaterThan(ORBIT_R_MIN)
  })
})

describe('showSvcLabel', () => {
  it('shows labels only up to ten services', () => {
    expect(showSvcLabel(10)).toBe(true)
    expect(showSvcLabel(11)).toBe(false)
  })
})

describe('donutOuterRadius', () => {
  it('caps the ring width at the maximum on extreme zoom-out', () => {
    // Tiny zoomK demands a huge compensating width; it must clamp.
    const r = donutOuterRadius(0.0001)
    expect(r).toBeLessThanOrEqual(21 + DONUT_MAX_WIDTH)
  })

  it('produces a finite radius for a degenerate zoom of zero', () => {
    expect(Number.isFinite(donutOuterRadius(0))).toBe(true)
  })
})

describe('problemScoreFromTopo', () => {
  it('is zero for a healthy host with no service summary', () => {
    expect(problemScoreFromTopo(node('UP'))).toBe(0)
  })

  it('penalises an unhealthy host', () => {
    expect(problemScoreFromTopo(node('DOWN'))).toBe(100)
  })

  it('weights critical over warning and unknown', () => {
    const score = problemScoreFromTopo(node('UP', summary({ critical: 1, warning: 1, unknown: 1 })))
    expect(score).toBe(4 + 2 + 2)
  })
})

describe('severityRank', () => {
  it('returns 0 for an undefined node', () => {
    expect(severityRank(undefined)).toBe(0)
  })

  it('ranks an unhealthy host as 2', () => {
    expect(severityRank(node('DOWN'))).toBe(2)
  })

  it('ranks a healthy host with criticals as 2', () => {
    expect(severityRank(node('UP', summary({ critical: 1 })))).toBe(2)
  })

  it('ranks warnings/unknowns as 1', () => {
    expect(severityRank(node('UP', summary({ warning: 1 })))).toBe(1)
    expect(severityRank(node('OK', summary({ unknown: 2 })))).toBe(1)
  })

  it('ranks a fully healthy host as 0', () => {
    expect(severityRank(node('UP', summary()))).toBe(0)
  })
})

describe('worstAffected', () => {
  const crit = { ok: 0, warning: 0, critical: 1, unknown: 0, pending: 0 }

  it('puts a host down that cuts others off before one down alone', () => {
    const topology = [
      aTopologyNode({ name: 'a-alone', state: 'DOWN', services_summary: crit }),
      aTopologyNode({ name: 'b-cause', state: 'DOWN' }),
      aTopologyNode({ name: 'child', state: 'UNREACHABLE', parents: ['b-cause'] }),
      aTopologyNode({ name: 'grandchild', state: 'UNREACHABLE', parents: ['child'] })
    ]
    expect([...worstAffected(topology, 1)]).toEqual(['b-cause'])
  })

  it('never picks an unreachable host, and picks among equals by name', () => {
    const topology = [
      aTopologyNode({ name: 'b', state: 'DOWN' }),
      aTopologyNode({ name: 'a', state: 'DOWN' }),
      aTopologyNode({ name: 'cut', state: 'UNREACHABLE' })
    ]
    expect([...worstAffected(topology, 3)]).toEqual(['a', 'b'])
  })
})

describe('hostDownAbove', () => {
  const topology = [
    aTopologyNode({ name: 'core', state: 'DOWN' }),
    aTopologyNode({ name: 'switch', state: 'UNREACHABLE', parents: ['core'] }),
    aTopologyNode({ name: 'edge', state: 'UP', parents: ['core'] })
  ]

  it('finds the host down above unreachable ones', () => {
    expect(hostDownAbove('switch', topology)).toBe('core')
    expect(hostDownAbove('core', topology)).toBe('core')
  })

  it('finds nothing above a host that is up', () => {
    expect(hostDownAbove('edge', topology)).toBeNull()
  })
})

describe('cutOffBy', () => {
  it('counts a host for the host down behind any of its parents, through a chain', () => {
    const topology = [
      aTopologyNode({ name: 'core', state: 'DOWN' }),
      aTopologyNode({ name: 'link', state: 'UNREACHABLE', parents: ['core'] }),
      aTopologyNode({ name: 'orphan', state: 'UNREACHABLE', parents: ['gone'] }),
      aTopologyNode({ name: 'leaf', state: 'UNREACHABLE', parents: ['orphan', 'link'] })
    ]
    expect(cutOffBy(topology)).toEqual(new Map([['core', 2]]))
  })

  it('ends a parent cycle rather than going round', () => {
    const topology = [
      aTopologyNode({ name: 'a', state: 'UNREACHABLE', parents: ['b'] }),
      aTopologyNode({ name: 'b', state: 'UNREACHABLE', parents: ['a'] })
    ]
    expect(cutOffBy(topology)).toEqual(new Map())
  })
})
