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
  elbowsOf,
  freeCellBeside,
  hostColumnWidth,
  hostLabelLines,
  layoutR,
  needsServices,
  placeServiceNodes,
  preLayoutHostsBelowSite,
  rankBySeverity,
  rowColumns,
  rowSpacingFallback,
  siteScaleForZoom,
  treeLayout
} from '@/maps/map/flow/layout'
import { foldNodeId } from '@/maps/map/flow/nodeIds'
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

describe('treeLayout', () => {
  const children = new Map([
    ['core', ['sw-a', 'sw-b']],
    ['sw-a', ['a1', 'a2']],
    ['sw-b', ['b1']]
  ])
  const layout = (
    rootGroups: string[][],
    childrenOf: ReadonlyMap<string, readonly string[]>,
    hosts: string[] = []
  ) =>
    treeLayout({
      rootGroups,
      childrenOf,
      hosts,
      footprint: (id) => ({ width: hostColumnWidth(id), height: 56 })
    })

  it('starts each subtree below its siblings, a parent beside its first child', () => {
    const { at } = layout([['core']], children)
    const y = (id: string) => at.get(id)!.y
    expect(y('a1')).toBeLessThan(y('a2'))
    expect(y('a2')).toBeLessThan(y('b1'))
    expect(at.get('sw-a')!.x).toBeLessThan(at.get('a1')!.x)
    expect(y('core')).toBe(y('sw-a'))
    expect(y('sw-a')).toBe(y('a1'))
  })

  it('keeps a parent where it is when more of its children are drawn', () => {
    const few = layout([['core']], new Map([['core', ['c-0', 'c-1']]]))
    const many = layout(
      [['core']],
      new Map([['core', Array.from({ length: 30 }, (_, i) => `c-${i}`)]])
    )
    expect(many.at.get('core')).toEqual(few.at.get('core'))
  })

  it("wraps a site's many top hosts into columns, below its trees", () => {
    const lone = Array.from({ length: 100 }, (_, i) => `lone-${i}`)
    const { at } = layout([['core', ...lone]], children)
    const columns = new Set(lone.map((id) => at.get(id)!.x))
    expect(columns.size).toBeGreaterThan(1)
    expect(Math.min(...lone.map((id) => at.get(id)!.y))).toBeGreaterThan(at.get('b1')!.y)
  })

  it('leaves each column room for its widest label', () => {
    const wide = new Map([['core', ['a-host-with-a-long-name']]])
    const hosts = ['core', 'a-host-with-a-long-name']
    const { at } = layout([['core']], wide, hosts)
    expect(at.get('a-host-with-a-long-name')!.x - at.get('core')!.x).toBeGreaterThan(
      hostColumnWidth('a-host-with-a-long-name')
    )
  })

  it('wraps many leaves under one parent into a grid wider than tall', () => {
    const leaves = Array.from({ length: 100 }, (_, i) => `leaf-${String(i).padStart(3, '0')}`)
    const { at } = layout([['core']], new Map([['core', leaves]]))
    const xs = leaves.map((leaf) => at.get(leaf)!.x)
    const ys = leaves.map((leaf) => at.get(leaf)!.y)
    expect(new Set(xs).size).toBeGreaterThan(1)
    expect(Math.max(...ys) - Math.min(...ys)).toBeLessThan(100 * 56)
  })

  it('fills a grid row by row, its columns closer than the levels of the tree', () => {
    const leaves = Array.from({ length: 30 }, (_, i) => `leaf-${String(i).padStart(2, '0')}`)
    const { at } = layout([['core']], new Map([['core', leaves]]))
    const first = at.get('leaf-00')!
    const second = at.get('leaf-01')!
    expect(second.y).toBe(first.y)
    expect(second.x - first.x).toBeLessThan(first.x - at.get('core')!.x)
  })

  it('starts a grid that comes first a row below its parent', () => {
    const leaves = Array.from({ length: 30 }, (_, i) => `leaf-${String(i).padStart(2, '0')}`)
    const { at } = layout([['core']], new Map([['core', leaves]]))
    expect(at.get('leaf-00')!.y - at.get('core')!.y).toBeGreaterThanOrEqual(56)
  })

  it('wraps many hosts that hold only a fold into a grid, each fold beside its host', () => {
    const hosts = Array.from({ length: 30 }, (_, i) => `sw-${String(i).padStart(2, '0')}`)
    const childrenOf = new Map([
      ['core', hosts],
      ...hosts.map((id): [string, string[]] => [id, [foldNodeId(id)]])
    ])
    const { at, reach } = layout([['core']], childrenOf)
    const [first, second] = [at.get('sw-00')!, at.get('sw-01')!]
    const fold = at.get(foldNodeId('sw-00'))!
    expect([second.y, fold.y]).toEqual([first.y, first.y])
    expect(first.x < fold.x && fold.x < second.x).toBe(true)
    // The edge to the second comes down between the first's fold and its own name.
    const down = second.x - reach.get('sw-01')!
    expect(down).toBeGreaterThan(fold.x + hostColumnWidth(foldNodeId('sw-00')) / 2)
    expect(down).toBeLessThan(second.x - hostColumnWidth('sw-01') / 2)
  })

  it('keeps a host opened in a grid in its column, its hosts below its row', () => {
    const hosts = Array.from({ length: 30 }, (_, i) => `sw-${String(i).padStart(2, '0')}`)
    const holding = (open: boolean) =>
      new Map([
        ['core', hosts],
        ...hosts.map((id): [string, string[]] => [
          id,
          open && id === 'sw-04' ? ['srv-1', 'srv-2'] : [foldNodeId(id)]
        ])
      ])
    const before = layout([['core']], holding(false)).at
    const { at } = treeLayout({
      rootGroups: [['core']],
      childrenOf: holding(true),
      hosts: [],
      opened: new Set(['sw-04']),
      footprint: (id) => ({ width: hostColumnWidth(id), height: 56 })
    })
    expect(at.get('sw-04')!.x).toBe(before.get('sw-04')!.x)
    expect(at.get('sw-04')!.y).toBeGreaterThan(before.get('sw-04')!.y)
    expect(at.get('sw-05')).toEqual(before.get('sw-05'))
    expect(at.get('srv-2')!.y).toBeLessThan(at.get('sw-06')!.y)
  })

  it('puts a grid where its first leaf comes among the subtrees', () => {
    const leaves = Array.from({ length: 20 }, (_, i) => `leaf-${String(i).padStart(2, '0')}`)
    const { at } = layout(
      [['core']],
      new Map([
        ['core', ['sw-a', 'leaf-00', 'sw-b', ...leaves.slice(1)]],
        ['sw-a', ['a1']],
        ['sw-b', ['b1']]
      ])
    )
    expect(at.get('sw-a')!.y).toBeLessThan(at.get('leaf-00')!.y)
    expect(at.get('leaf-19')!.y).toBeLessThan(at.get('sw-b')!.y)
  })

  it('puts each group of roots below the previous one, its site beside its first tree', () => {
    const { at, groupAt } = layout([['core'], ['site-b-root']], children)
    const coreTree = ['core', 'sw-a', 'sw-b', 'a1', 'a2', 'b1'].map((id) => at.get(id)!.y)
    const other = at.get('site-b-root')!
    expect(other.y).toBeGreaterThan(Math.max(...coreTree))
    expect(groupAt[1]).toEqual(other)
    expect(groupAt[0]).toEqual(at.get('core'))
  })

  it('moves only what is below a tree when it grows', () => {
    const roots = Array.from({ length: 10 }, (_, i) => `root-${i}`)
    const before = layout([roots], new Map())
    const after = layout(
      [roots],
      new Map([['root-5', Array.from({ length: 6 }, (_, i) => `child-${i}`)]])
    )
    for (const root of roots.slice(0, 6)) {
      expect(after.at.get(root)).toEqual(before.at.get(root))
    }
    expect(after.at.get('root-6')!.y).toBeGreaterThan(before.at.get('root-6')!.y)
  })

  it('starts a host with two parents once, under the first', () => {
    const twoParents = new Map([
      ['p1', ['shared']],
      ['p2', ['shared']]
    ])
    const { at } = layout([['p1', 'p2']], twoParents)
    expect(at.get('shared')!.y).toBeCloseTo(at.get('p1')!.y)
  })

  it('places a host on a parent cycle once, outside the trees', () => {
    const cycle = new Map([
      ['p', ['q']],
      ['q', ['p']]
    ])
    const { at, groupAt } = layout([['root']], cycle, ['root', 'p', 'q'])
    expect([...at.keys()].sort()).toEqual(['p', 'q', 'root'])
    expect(groupAt).toHaveLength(1)
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

describe('freeCellBeside', () => {
  const cells = (rows: number, count: number) =>
    Array.from({ length: count }, (_, i) => ({
      x: Math.floor(i / rows) * 100,
      y: (i % rows) * 80
    }))

  it('takes the place a sibling left in the grid', () => {
    const siblings = cells(4, 10).filter((cell) => cell.x !== 100 || cell.y !== 160)
    expect(freeCellBeside(siblings, 60)).toEqual({ x: 100, y: 160 })
  })

  it('reads hosts a little off their places, as collide leaves them, as the same grid', () => {
    const siblings = cells(4, 10)
      .filter((cell) => cell.x !== 100 || cell.y !== 160)
      .map((cell, i) => ({ x: cell.x - (i % 2), y: cell.y + (i % 3) * 1.5 }))
    const free = freeCellBeside(siblings, 60)!
    expect(free.x).toBeCloseTo(100, -1)
    expect(free.y).toBeCloseTo(160, -1)
  })

  it('fills a grid row by row', () => {
    const siblings = cells(4, 8).filter(
      (cell) => !(cell.x === 100 && cell.y === 240) && !(cell.x === 0 && cell.y === 240)
    )
    expect(freeCellBeside(siblings, 60)).toEqual({ x: 0, y: 240 })
  })

  it('starts a new row below a full grid', () => {
    expect(freeCellBeside(cells(4, 8), 60)).toEqual({ x: 0, y: 320 })
  })

  it('goes below the last sibling in a single column', () => {
    expect(freeCellBeside(cells(8, 3), 60)?.x).toBe(0)
    expect(freeCellBeside(cells(8, 3), 60)!.y).toBeGreaterThan(160)
  })
})

describe('hostLabelLines', () => {
  it('draws a name that fits a column on one line', () => {
    expect(hostLabelLines('sw-core-01.demo.checkmk.com')).toEqual(['sw-core-01.demo.checkmk.com'])
  })

  it('breaks a domain name after the host’s own part', () => {
    expect(hostLabelLines('storage-netapp-01.demo.checkmk.com')).toEqual([
      'storage-netapp-01.',
      'demo.checkmk.com'
    ])
  })

  it('breaks a long name after one of its parts, keeping all of it', () => {
    const name = 'internal-clb-demo-cmk-919536368.eu-central-1.elb.amazonaws.com'
    const lines = hostLabelLines(name)
    expect(lines).toEqual(['internal-clb-demo-cmk-919536368.', 'eu-central-1.elb.amazonaws.com'])
    for (const line of lines) {
      expect(line.length * 7 + 12).toBeLessThanOrEqual(hostColumnWidth(name))
    }
  })
})

describe('elbowsOf', () => {
  it('runs the edges of a column right of its parent at right angles', () => {
    const elbows = elbowsOf({ x: 0, y: 0 }, [{ id: 'a', x: 200, y: 0 }], 66)
    expect(elbows.get('a')).toMatchObject({ drop: 200, rise: 100, reach: 100 })
  })

  it('comes down to a child further along a grid where the layout says', () => {
    const children = [
      { id: 'a', x: 200, y: 0 },
      { id: 'b', x: 500, y: 0 }
    ]
    const elbows = elbowsOf({ x: 0, y: 0 }, children, 66, new Map([['b', 60]]))
    expect(elbows.get('b')?.reach).toBe(60)
    expect(elbows.get('a')?.reach).toBe(elbows.get('a')?.rise)
  })

  it("runs the edges to a grid's further columns along its parent's row", () => {
    const children = [
      { id: 'a', x: 200, y: 66 },
      { id: 'b', x: 500, y: 66 }
    ]
    const b = elbowsOf({ x: 0, y: 0 }, children, 66).get('b')!
    expect(66 + b.aside).toBe(0)
  })

  it('runs them just above the grid when a subtree comes before it', () => {
    const children = [
      { id: 'sub', x: 200, y: 0 },
      { id: 'a', x: 200, y: 200 },
      { id: 'b', x: 500, y: 200 }
    ]
    const b = elbowsOf({ x: 0, y: 0 }, children, 66).get('b')!
    expect(200 + b.aside).toBeGreaterThan(0)
    expect(200 + b.aside).toBeLessThan(200)
  })

  it('draws a straight edge to a child moved behind its parent, elbows to the others', () => {
    const elbows = elbowsOf(
      { x: 200, y: 0 },
      [
        { id: 'moved', x: 100, y: 0 },
        { id: 'a', x: 400, y: 0 }
      ],
      66
    )
    expect([...elbows.keys()]).toEqual(['a'])
    expect(elbows.get('a')?.drop).toBe(200)
  })
})
