/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  type LayoutNode,
  type PinnableNode,
  bfsLevels,
  layoutR,
  needsServices,
  placeServiceNodes,
  preLayoutHosts,
  preLayoutHostsBelowSite,
  rankBySeverity,
  rowColumns,
  rowSpacingFallback,
  siteScaleForZoom
} from '@/maps/map/flow/layout'
import type { TopologyNode } from '@/maps/types/api'

function topo(name: string, state = 'UP', parents: string[] = []): TopologyNode {
  return { name, parents, state, output: '', services: [] } as unknown as TopologyNode
}

function host(id: string, state = 'UP'): LayoutNode {
  return { id, topo: topo(id, state) }
}

describe('rankBySeverity', () => {
  it('puts worst states first, ties broken alphabetically', () => {
    const ranked = rankBySeverity([
      host('zeta', 'UP'),
      host('alpha', 'UP'),
      host('down-host', 'DOWN'),
      host('warn-host', 'WARNING')
    ])
    expect(ranked.map((h) => h.id)).toEqual(['down-host', 'warn-host', 'alpha', 'zeta'])
  })

  it('does not mutate the input array', () => {
    const input = [host('b', 'UP'), host('a', 'DOWN')]
    rankBySeverity(input)
    expect(input.map((h) => h.id)).toEqual(['b', 'a'])
  })
})

describe('preLayoutHosts', () => {
  it('places the worst host nearest the center of the spiral', () => {
    const hosts = [host('healthy-1'), host('healthy-2'), host('crit', 'DOWN')]
    preLayoutHosts(hosts)
    const dist = (h: LayoutNode) => Math.hypot(h.x ?? 0, h.y ?? 0)
    const crit = hosts.find((h) => h.id === 'crit')!
    for (const h of hosts) {
      if (h !== crit) {
        expect(dist(crit)).toBeLessThan(dist(h))
      }
    }
  })

  it('assigns distinct positions (no pixel-perfect overlap)', () => {
    const hosts = Array.from({ length: 50 }, (_, i) => host(`h${i}`))
    preLayoutHosts(hosts)
    const keys = new Set(hosts.map((h) => `${Math.round(h.x!)}:${Math.round(h.y!)}`))
    expect(keys.size).toBe(50)
  })

  it('is a no-op for an empty list', () => {
    expect(() => preLayoutHosts([])).not.toThrow()
  })
})

describe('preLayoutHostsBelowSite', () => {
  it('keeps every host below the site anchor', () => {
    const hosts = Array.from({ length: 30 }, (_, i) => host(`h${i}`))
    const site = { x: 100, y: -200 }
    preLayoutHostsBelowSite(site, hosts, 40)
    for (const h of hosts) {
      expect(h.y!).toBeGreaterThanOrEqual(site.y + 40)
    }
  })
})

describe('layoutR / needsServices', () => {
  it('fan uses the fan radius, everything else the orbit radius', () => {
    // fanR packs a half circle, so it needs roughly twice the orbit radius.
    expect(layoutR('fan', 40)).toBeGreaterThan(layoutR('orbit', 40))
    expect(layoutR('donut', 40)).toBe(layoutR('orbit', 40))
  })

  it('only full-service layouts trigger the bulk service fetch', () => {
    expect(needsServices('fan')).toBe(true)
    expect(needsServices('orbit')).toBe(true)
    expect(needsServices('row')).toBe(true)
    expect(needsServices('donut')).toBe(false)
    expect(needsServices('off')).toBe(false)
    expect(needsServices(null)).toBe(false)
  })
})

describe('siteScaleForZoom', () => {
  it('inflates at low zoom, clamps at 3.5, stays 1 at full zoom', () => {
    expect(siteScaleForZoom(1)).toBe(1)
    expect(siteScaleForZoom(2)).toBe(1)
    expect(siteScaleForZoom(0.5)).toBe(2)
    expect(siteScaleForZoom(0.1)).toBe(3.5)
    // NaN/garbage zoom must not produce NaN transforms.
    expect(siteScaleForZoom(Number.NaN)).toBe(1)
  })
})

describe('bfsLevels', () => {
  it('assigns 0 to roots and increments per parent hop', () => {
    const nodes = [topo('root'), topo('child', 'UP', ['root']), topo('grandchild', 'UP', ['child'])]
    const levels = bfsLevels(nodes)
    expect(levels.get('root')).toBe(0)
    expect(levels.get('child')).toBe(1)
    expect(levels.get('grandchild')).toBe(2)
  })

  it('treats hosts whose parents are outside the visible set as roots', () => {
    const nodes = [topo('visible', 'UP', ['outside-the-map'])]
    expect(bfsLevels(nodes).get('visible')).toBe(0)
  })

  it('still levels every node in a parent cycle', () => {
    const nodes = [topo('a', 'UP', ['b']), topo('b', 'UP', ['a'])]
    const levels = bfsLevels(nodes)
    expect(levels.has('a')).toBe(true)
    expect(levels.has('b')).toBe(true)
  })

  it('sinks what it could not reach to one level, not to one level each', () => {
    // The deepest level sets the layer spacing the whole map is laid out on, so
    // a level per unreachable node would drive it up with the size of the
    // topology and flatten every real layer into one band.
    const nodes = [
      topo('root'),
      topo('child', 'UP', ['root']),
      // A cycle of three, reachable from no root.
      topo('a', 'UP', ['c']),
      topo('b', 'UP', ['a']),
      topo('c', 'UP', ['b'])
    ]
    const levels = bfsLevels(nodes)
    expect(levels.get('child')).toBe(1)
    expect(levels.get('a')).toBe(2)
    expect(levels.get('b')).toBe(2)
    expect(levels.get('c')).toBe(2)
    expect(Math.max(...levels.values())).toBe(2)
  })
})

describe('rowColumns', () => {
  it('never asks for more columns than there are services', () => {
    expect(rowColumns(2)).toBe(2)
  })

  it('grows with the count, so a wide grid does not become a single long row', () => {
    expect(rowColumns(24)).toBeGreaterThan(rowColumns(8))
  })
})

describe('rowSpacingFallback', () => {
  it('reserves room for the longest service name', () => {
    const short = rowSpacingFallback([{ id: 'host::CPU' }])
    const long = rowSpacingFallback([{ id: 'host::Interface 1 of 4 on a long name' }])
    expect(long).toBeGreaterThan(short)
  })
})

describe('placeServiceNodes', () => {
  const hostAt = (x: number, y: number): LayoutNode => ({ id: 'host', x, y })
  const services = (count: number): PinnableNode[] =>
    Array.from({ length: count }, (_unused, index) => ({ id: `host::svc-${index}` }))

  function place(layout: 'fan' | 'orbit' | 'row', count: number): PinnableNode[] {
    const nodes = services(count)
    placeServiceNodes({
      layout,
      hosts: new Map([['host', hostAt(100, 200)]]),
      servicesByHost: new Map([['host', nodes]]),
      rowSpacings: new Map()
    })
    return nodes
  }

  it('pins every service, so the simulation never gets a say in where they go', () => {
    for (const layout of ['fan', 'orbit', 'row'] as const) {
      for (const node of place(layout, 6)) {
        expect(Number.isFinite(node.fx)).toBe(true)
        expect(Number.isFinite(node.fy)).toBe(true)
      }
    }
  })

  it('fans and rows stay below their host; an orbit surrounds it', () => {
    expect(place('fan', 6).every((node) => (node.fy as number) > 200)).toBe(true)
    expect(place('row', 6).every((node) => (node.fy as number) > 200)).toBe(true)
    expect(place('orbit', 6).some((node) => (node.fy as number) < 200)).toBe(true)
  })

  it('wraps a row grid onto more than one line once it runs out of columns', () => {
    const placed = place('row', 24)
    expect(new Set(placed.map((node) => node.fy)).size).toBeGreaterThan(1)
  })

  it('leaves a service whose host it has never heard of alone', () => {
    const orphans = services(3)
    placeServiceNodes({
      layout: 'fan',
      hosts: new Map(),
      servicesByHost: new Map([['gone', orphans]]),
      rowSpacings: new Map()
    })
    expect(orphans.every((node) => node.fx === undefined)).toBe(true)
  })
})
