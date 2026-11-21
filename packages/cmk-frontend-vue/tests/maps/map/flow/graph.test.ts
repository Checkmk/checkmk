/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { VISIBLE_HOSTS } from '@/maps/map/flow/fold'
import { NODE_R, cutOffBy } from '@/maps/map/flow/geometry'
import { createFlowGraph, foldsHosts } from '@/maps/map/flow/graph'
import type { HostLayout, TopologyNode } from '@/maps/types/api'

import { aTopologyNode } from '../../support/fixtures'

type Graph = ReturnType<typeof createFlowGraph>

function build(
  graph: Graph,
  topology: TopologyNode[],
  extra: {
    opened?: string[]
    found?: string[]
    problemsOnly?: boolean
    picked?: string
    hostLayout?: HostLayout
    savedPositions?: Record<string, { x: number; y: number }>
  } = {}
) {
  return graph.build({
    topology,
    layout: 'donut',
    connectionId: 'site',
    savedPositions: extra.savedPositions ?? {},
    height: 800,
    opened: new Map((extra.opened ?? []).map((id) => [id, 1])),
    found: new Set(extra.found ?? []),
    problemsOnly: extra.problemsOnly ?? false,
    cutOff: cutOffBy(topology),
    picked: extra.picked ?? null,
    hostLayout: extra.hostLayout ?? 'tree'
  })
}

function aGraph(): Graph {
  return createFlowGraph({ describeTruncation: (count) => `+${count}` })
}

/** A router with ``count`` hosts behind it, each in the state ``childState`` gives it. */
function behindRouter(
  count: number,
  childState: (index: number) => string = () => 'UP',
  routerState = 'UP'
): TopologyNode[] {
  return [
    aTopologyNode({ name: 'router', state: routerState }),
    ...Array.from({ length: count }, (_, i) =>
      aTopologyNode({ name: `host-${i}`, parents: ['router'], state: childState(i) })
    )
  ]
}

const drawnHosts = (built: ReturnType<typeof build>): string[] =>
  built.nodes.filter((node) => node.nodeType === 'host').map((node) => node.id)
const folds = (built: ReturnType<typeof build>) =>
  built.nodes.filter((node) => node.nodeType === 'fold')

describe('foldsHosts', () => {
  it('folds a hierarchy drawn as a tree, as the graph then does', () => {
    expect(foldsHosts(behindRouter(30), 'tree')).toBe(true)
    expect(build(aGraph(), behindRouter(30)).startsAsTree).toBe(true)
  })

  it('folds nothing drawn as a network', () => {
    expect(foldsHosts(behindRouter(30), 'network')).toBe(false)
  })

  it('folds nothing where most hosts have no parent on the map', () => {
    const flat = Array.from({ length: 10 }, (_, i) => aTopologyNode({ name: `host-${i}` }))
    expect(foldsHosts(flat, 'tree')).toBe(false)
    expect(build(aGraph(), flat).startsAsTree).toBe(false)
  })
})

describe('createFlowGraph', () => {
  it('draws hosts whose parents are not on the map as a flat map, without folds', () => {
    const topology = Array.from({ length: 300 }, (_, i) =>
      aTopologyNode({ name: `host-${i}`, parents: ['core-switch'] })
    )
    const built = build(aGraph(), topology)
    expect(drawnHosts(built)).toHaveLength(300)
    expect(folds(built)).toEqual([])
  })

  it('folds the hosts behind a failed router rather than drawing every unreachable one', () => {
    const built = build(
      aGraph(),
      behindRouter(600, () => 'UNREACHABLE', 'DOWN')
    )
    expect(drawnHosts(built)).toEqual(['router'])
    expect(folds(built)[0]?.moreCount).toBe(600)
  })

  it('draws every host of a hierarchy drawn as a network', () => {
    const built = build(
      aGraph(),
      behindRouter(600, () => 'UNREACHABLE', 'DOWN'),
      {
        hostLayout: 'network'
      }
    )
    expect(drawnHosts(built)).toHaveLength(601)
    expect(folds(built)).toEqual([])
    expect(built.startsAsTree).toBe(false)
  })

  it('draws no more down hosts than the budget allows', () => {
    const built = build(
      aGraph(),
      behindRouter(400, () => 'DOWN')
    )
    expect(drawnHosts(built).length).toBeLessThanOrEqual(VISIBLE_HOSTS + 1)
    expect(folds(built)[0]?.moreCount).toBe(400 - (drawnHosts(built).length - 1))
  })

  it('keeps remembering where the operator put a host while it is folded away', () => {
    const graph = aGraph()
    const topology = behindRouter(300)
    const savedPositions = { 'host-250': { x: 4000, y: 4000 } }
    const built = build(graph, topology, { savedPositions })
    expect(drawnHosts(built)).not.toContain('host-250')
    expect(graph.pinnedPositions()).toMatchObject(savedPositions)
  })

  it('remembers where the operator put a host that folds away before the map saved it', () => {
    const graph = aGraph()
    const topology = behindRouter(300)
    const opened = build(graph, topology, { opened: ['router'] })
    const host = opened.byId.get('host-250')!
    host.fx = 4000
    host.fy = 4000

    build(graph, topology)

    expect(graph.pinnedPositions()).toMatchObject({ 'host-250': { x: 4000, y: 4000 } })
  })

  it('frees the hosts folded away below a host the operator drags', () => {
    const graph = aGraph()
    build(graph, behindRouter(300), { savedPositions: { 'host-250': { x: 4000, y: 4000 } } })

    graph.unpinDescendants('router', new Map())

    expect(graph.pinnedPositions()).not.toHaveProperty('host-250')
  })

  it('remembers no site the tree layout placed', () => {
    const graph = aGraph()
    build(graph, behindRouter(30))
    expect(graph.pinnedPositions()).toEqual({})
  })

  it('draws a searched host wherever it hangs', () => {
    const built = build(aGraph(), behindRouter(30), { found: ['host-7'] })
    expect(drawnHosts(built).sort()).toEqual(['host-7', 'router'])
  })

  it('draws a host with a service in trouble wherever it hangs while the map shows only problems', () => {
    const topology = behindRouter(30).map((topo) =>
      topo.name === 'host-7'
        ? {
            ...topo,
            services_summary: { ok: 0, warning: 0, critical: 1, unknown: 0, pending: 0 },
            unhandled_service_problems: 1
          }
        : topo
    )
    expect(drawnHosts(build(aGraph(), topology))).not.toContain('host-7')
    expect(drawnHosts(build(aGraph(), topology, { problemsOnly: true }))).toContain('host-7')
  })

  it('keeps hosts unreachable through a host down folded while the map shows only problems', () => {
    const built = build(
      aGraph(),
      behindRouter(30, () => 'UNREACHABLE', 'DOWN'),
      {
        problemsOnly: true
      }
    )
    expect(drawnHosts(built)).toEqual(['router'])
  })

  it('leaves out a group without problems while the map shows only problems', () => {
    expect(folds(build(aGraph(), behindRouter(30)))).toHaveLength(1)
    expect(folds(build(aGraph(), behindRouter(30), { problemsOnly: true }))).toEqual([])
  })

  it('hangs a host past the quiet hosts left out under the ancestor that stays', () => {
    const crit = { ok: 0, warning: 0, critical: 1, unknown: 0, pending: 0 }
    const topology = [
      aTopologyNode({ name: 'core', services_summary: crit, unhandled_service_problems: 1 }),
      ...behindRouter(30, (i) => (i === 7 ? 'DOWN' : 'UP')).map((topo) =>
        topo.name === 'router' ? { ...topo, parents: ['core'] } : topo
      )
    ]
    const built = build(aGraph(), topology, { problemsOnly: true })
    const edge = built.links.find(
      (link) => link.source.id === 'core' && link.target.id === 'host-7'
    )
    expect(edge).toMatchObject({ skipsHosts: true })
    expect(edge?.furtherParent).toBeUndefined()
  })

  it('draws a picked host without problems while the map shows only problems', () => {
    expect(
      drawnHosts(build(aGraph(), behindRouter(30), { problemsOnly: true, picked: 'host-7' }))
    ).toContain('host-7')
  })

  it('keeps a host whose problem is handled folded while the map shows only problems', () => {
    const topology = behindRouter(30).map((topo) =>
      topo.name === 'host-7' ? { ...topo, state: 'DOWN', acknowledged: true } : topo
    )
    expect(drawnHosts(build(aGraph(), topology, { problemsOnly: true }))).not.toContain('host-7')
  })

  it('draws none of the hits of a search that names most of the map', () => {
    const topology = behindRouter(200)
    const built = build(aGraph(), topology, { found: topology.map((topo) => topo.name) })
    expect(drawnHosts(built)).toEqual(['router'])
  })

  it('hangs a host that a change of state shows beside its parent and leaves the rest where it is', () => {
    const graph = aGraph()
    const topology = behindRouter(30)
    build(graph, topology)
    const settled = build(graph, topology)
    // Where a drag on the router leaves its tree.
    for (const node of settled.byId.values()) {
      if (node.nodeType !== 'site') {
        node.x = node.x! + 1000
        node.y = node.y! + 2000
      }
    }
    const router = { x: settled.byId.get('router')!.x!, y: settled.byId.get('router')!.y! }

    const down = topology.map((topo) =>
      topo.name === 'host-3' ? { ...topo, state: 'DOWN' } : topo
    )
    const shown = build(graph, down)
    const host = shown.byId.get('host-3')!
    expect(shown.byId.get('router')!.x).toBe(router.x)
    expect(host.x).toBeGreaterThan(router.x)
    expect(Math.abs(host.y! - router.y)).toBeLessThan(500)
  })

  it('hangs a site’s trees beside where the operator put the site', () => {
    const topology = behindRouter(30)
    const [frame] = build(aGraph(), topology).frames
    const site = frame!.head
    const before = frame!.members.find((member) => member.id === 'router')!
    const offset = { x: site.x! + 5000, y: site.y! + 3000 }

    const moved = build(aGraph(), topology, { savedPositions: { [site.id]: offset } })
    const router = moved.byId.get('router')!
    expect(router.x! - offset.x).toBeCloseTo(before.x! - site.x!)
    expect(router.y! - offset.y).toBeCloseTo(before.y! - site.y!)
  })

  it('hangs the children of a host the operator placed to the right of that host', () => {
    const built = build(aGraph(), behindRouter(10), {
      savedPositions: { router: { x: 5000, y: 5000 } }
    })
    for (const host of drawnHosts(built).filter((id) => id !== 'router')) {
      const child = built.byId.get(host)!
      expect(child.x).toBeGreaterThan(5000)
      expect(Math.abs(child.y! - 5000)).toBeLessThan(1500)
    }
  })

  it.each([
    {
      becomes: 'a change of state shows',
      problemsOnly: false,
      change: (topo: TopologyNode): TopologyNode => ({ ...topo, state: 'DOWN' })
    },
    {
      becomes: 'turns into a problem while the map shows only problems',
      problemsOnly: true,
      change: (topo: TopologyNode): TopologyNode => ({
        ...topo,
        services_summary: { ok: 0, warning: 0, critical: 1, unknown: 0, pending: 0 },
        unhandled_service_problems: 1
      })
    }
  ])(
    'puts a host that $becomes into a free place, moving none of the others',
    ({ problemsOnly, change }) => {
      const graph = aGraph()
      const topology = behindRouter(30, (i) => (i < 12 ? 'DOWN' : 'UP'))
      build(graph, topology, { problemsOnly })
      const before = build(graph, topology, { problemsOnly })
      const at = new Map(
        before.nodes
          .filter((node) => node.nodeType === 'host')
          .map((node) => [node.id, { x: node.x!, y: node.y! }])
      )

      const changed = topology.map((topo) => (topo.name === 'host-20' ? change(topo) : topo))
      const after = build(graph, changed, { problemsOnly })
      const added = after.byId.get('host-20')!
      for (const [id, was] of at) {
        expect(after.byId.get(id)).toMatchObject(was)
        expect(Math.hypot(added.x! - was.x, added.y! - was.y)).toBeGreaterThan(NODE_R * 2)
      }
    }
  )

  it('keeps a host of an opened group drawn where it was when it recovers', () => {
    const graph = aGraph()
    const topology = behindRouter(30, (i) => (i < 12 ? 'DOWN' : 'UP'))
    build(graph, topology, { opened: ['router'] })
    const was = build(graph, topology, { opened: ['router'] }).byId.get('host-3')!
    const position = { x: was.x, y: was.y }

    const up = topology.map((topo) => (topo.name === 'host-3' ? { ...topo, state: 'UP' } : topo))
    expect(build(graph, up, { opened: ['router'] }).byId.get('host-3')).toMatchObject(position)
  })

  it('runs the edges into the further columns of a grid above it, not through the hosts before', () => {
    const built = build(aGraph(), behindRouter(30), { opened: ['router'] })
    const edges = built.links.filter((link) => link.source.id === 'router')
    const firstColumn = Math.min(...edges.map((link) => link.target.x!))
    for (const { target, elbow } of edges) {
      expect(elbow?.aside === 0).toBe(target.x === firstColumn)
    }
  })

  it('runs the edges into a grid in the gaps between its columns, clear of the names', () => {
    const built = build(aGraph(), behindRouter(30), { opened: ['router'] })
    const edges = built.links.filter((link) => link.source.id === 'router')
    const columns = [...new Set(edges.map((link) => link.target.x!))].sort((a, b) => a - b)
    for (const { elbow } of edges) {
      expect(elbow?.rise).toBe((columns[1]! - columns[0]!) / 2)
    }
  })

  it('tells the edge from a host’s further parent apart from the one it hangs under', () => {
    const topology = [
      ...behindRouter(30).map((topo) =>
        topo.name === 'host-0' ? { ...topo, parents: ['router', 'router-b'] } : topo
      ),
      aTopologyNode({ name: 'router-b' })
    ]
    const built = build(aGraph(), topology, { opened: ['router'] })
    const into = (parent: string) =>
      built.links.find((link) => link.source.id === parent && link.target.id === 'host-0')
    expect(into('router')?.furtherParent).toBeUndefined()
    expect(into('router-b')?.furtherParent).toBe(true)
  })

  it('puts the sibling with more hosts in trouble below it first', () => {
    const crit = { ok: 0, warning: 0, critical: 1, unknown: 0, pending: 0 }
    const below = (parent: string, troubled: number): TopologyNode[] =>
      Array.from({ length: 25 }, (_, i) =>
        aTopologyNode({
          name: `${parent}-${i}`,
          parents: [parent],
          services_summary: i < troubled ? crit : null,
          unhandled_service_problems: i < troubled ? 1 : 0
        })
      )
    const built = build(
      aGraph(),
      [
        aTopologyNode({ name: 'router' }),
        aTopologyNode({ name: 'a', parents: ['router'] }),
        aTopologyNode({ name: 'b', parents: ['router'] }),
        ...below('a', 1),
        ...below('b', 3)
      ],
      { opened: ['router'] }
    )

    expect(built.byId.get('b')!.y!).toBeLessThan(built.byId.get('a')!.y!)
  })

  it('puts the host down that cuts off more hosts first', () => {
    const behind = (parent: string, count: number): TopologyNode[] =>
      Array.from({ length: count }, (_, i) =>
        aTopologyNode({ name: `${parent}-${i}`, parents: [parent], state: 'UNREACHABLE' })
      )
    const built = build(
      aGraph(),
      [
        aTopologyNode({ name: 'router' }),
        aTopologyNode({ name: 'a', parents: ['router'], state: 'DOWN' }),
        aTopologyNode({ name: 'b', parents: ['router'], state: 'DOWN' }),
        ...behind('a', 5),
        ...behind('b', 20)
      ],
      { opened: ['router'] }
    )

    expect(built.byId.get('b')!.y!).toBeLessThan(built.byId.get('a')!.y!)
  })

  it('puts the sibling with a host down further below it before one with more service problems', () => {
    const crit = { ok: 0, warning: 0, critical: 1, unknown: 0, pending: 0 }
    const built = build(
      aGraph(),
      [
        aTopologyNode({ name: 'router' }),
        aTopologyNode({ name: 'a', parents: ['router'] }),
        aTopologyNode({ name: 'b', parents: ['router'] }),
        aTopologyNode({ name: 'b-switch', parents: ['b'] }),
        aTopologyNode({ name: 'b-down', parents: ['b-switch'], state: 'DOWN' }),
        ...Array.from({ length: 25 }, (_, i) =>
          aTopologyNode({
            name: `a-${i}`,
            parents: ['a'],
            services_summary: i < 5 ? crit : null,
            unhandled_service_problems: i < 5 ? 1 : 0
          })
        )
      ],
      { opened: ['router'] }
    )

    expect(built.byId.get('b')!.y!).toBeLessThan(built.byId.get('a')!.y!)
  })

  it('counts in a fold only the hosts whose problems nobody has taken on', () => {
    const crit = { ok: 0, warning: 0, critical: 1, unknown: 0, pending: 0 }
    const topology = behindRouter(30).map((topo) => {
      switch (topo.name) {
        case 'host-0':
          return { ...topo, state: 'DOWN', acknowledged: true }
        case 'host-1':
          return { ...topo, services_summary: crit, unhandled_service_problems: 1 }
        case 'host-2':
          return { ...topo, services_summary: crit, unhandled_service_problems: 0 }
        default:
          return topo
      }
    })

    const [fold] = folds(build(aGraph(), topology))

    expect(fold).toMatchObject({
      state: 'CRITICAL',
      foldAttention: { critical: 1, handled: 2, none: 27 },
      foldPressing: [{ name: 'host-1', needs: 'critical' }]
    })
  })

  it('draws a picked host out of its fold, and folds it back once unpicked', () => {
    const graph = aGraph()
    const topology = behindRouter(30)

    const picked = build(graph, topology, { picked: 'host-7' })
    // The graph updates its nodes in place, so they are read before the next build.
    const pickedDrawn = picked.nodes.some((node) => node.id === 'host-7')
    const pickedFolded = folds(picked)[0]!.moreCount
    const unpicked = build(graph, topology)

    expect([pickedDrawn, pickedFolded]).toEqual([true, 29])
    expect(unpicked.nodes.some((node) => node.id === 'host-7')).toBe(false)
    expect(folds(unpicked)[0]!.moreCount).toBe(30)
  })

  it('counts a fold by host states and its services by service states', () => {
    const services = { ok: 3, warning: 0, critical: 1, unknown: 0, pending: 0 }
    const topology = behindRouter(30).map((topo) =>
      topo.name === 'host-0'
        ? { ...topo, state: 'DOWN', acknowledged: true }
        : topo.name === 'host-1'
          ? { ...topo, services_summary: services }
          : topo
    )

    const [fold] = folds(build(aGraph(), topology))

    expect(fold).toMatchObject({
      foldSummary: {
        hosts: { ok: 29, warning: 0, critical: 1, unknown: 0, pending: 0 },
        services: { ok: 3, warning: 0, critical: 1, unknown: 0, pending: 0 }
      }
    })
  })

  it('orders an opened group by what its hosts need, handled problems after open ones', () => {
    const crit = { ok: 0, warning: 0, critical: 1, unknown: 0, pending: 0 }
    const warn = { ok: 0, warning: 1, critical: 0, unknown: 0, pending: 0 }
    const child = (name: string, fields: Partial<TopologyNode>): TopologyNode =>
      aTopologyNode({ name, parents: ['router'], ...fields })
    const built = build(
      aGraph(),
      [
        aTopologyNode({ name: 'router' }),
        child('a-ok', {}),
        child('b-crit-acked', { services_summary: crit }),
        child('c-down-acked', { state: 'DOWN', acknowledged: true }),
        child('d-warn', { services_summary: warn, unhandled_service_problems: 1 }),
        child('e-crit', { services_summary: crit, unhandled_service_problems: 1 }),
        child('f-unreachable', { state: 'UNREACHABLE' })
      ],
      { opened: ['router'] }
    )

    const order = drawnHosts(built)
      .filter((id) => id !== 'router')
      .sort((a, b) => built.byId.get(a)!.y! - built.byId.get(b)!.y!)
    expect(order).toEqual([
      'e-crit',
      'd-warn',
      'f-unreachable',
      'b-crit-acked',
      'c-down-acked',
      'a-ok'
    ])
  })

  it('lays the tree out afresh after a switch of service layout', () => {
    const topology = [
      ...behindRouter(30, (i) => (i < 3 ? 'DOWN' : 'UP')),
      ...Array.from({ length: 8 }, (_, i) =>
        aTopologyNode({ name: `edge-${i}`, state: i < 2 ? 'DOWN' : 'UP' })
      )
    ]
    // One the operator dragged, which keeps its place through the switch.
    const savedPositions = { 'edge-0': { x: 4000, y: 4000 } }
    const graph = aGraph()
    build(graph, topology, { savedPositions })
    build(graph, topology, { savedPositions })

    graph.forgetLayout('fan', 'row')
    const after = build(graph, topology, { savedPositions })
    const fresh = build(aGraph(), topology, { savedPositions })
    for (const node of fresh.nodes.filter((n) => n.nodeType !== 'service')) {
      expect(after.byId.get(node.id), node.id).toMatchObject({ x: node.x, y: node.y })
    }
  })

  it('lays the tree out afresh when the operator opens a fold', () => {
    const graph = aGraph()
    const topology = behindRouter(30)
    build(graph, topology)
    build(graph, topology).byId.get('router')!.x = 9999
    const opened = build(graph, topology, { opened: ['router'] })
    expect(opened.byId.get('router')!.x).not.toBe(9999)
  })
})
