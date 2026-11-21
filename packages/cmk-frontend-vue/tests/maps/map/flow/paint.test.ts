/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { select } from 'd3-selection'
import { describe, expect, it } from 'vitest'

import { donutOuterRadius } from '@/maps/map/flow/geometry'
import type { FNode, HostFrame } from '@/maps/map/flow/nodes'
import {
  type NodeVisuals,
  drawFoldBacks,
  drawNodes,
  flowClass,
  linkKey,
  nodeKindClass,
  positionFoldBacks,
  refreshNodes
} from '@/maps/map/flow/paint'

const visuals: NodeVisuals = {
  scale: 1,
  showsDonut: () => false,
  glowFilter: 'glow',
  isWorst: () => false,
  halo: () => ({ stroke: 'none', width: 0 }),
  donutSegments: () => [],
  badges: () => [],
  ariaLabel: (node) => node.id,
  moreLabel: (count) => `+${count} more`,
  foldLabel: (node) => `+${node.moreCount ?? 0} hosts`
}

function node(overrides: Partial<FNode> & Pick<FNode, 'id' | 'nodeType'>): FNode {
  return { state: 'OK', output: '', bfsLevel: 2, ...overrides }
}

/** Paints a node set the way the canvas does: join, draw the entered, refresh the merge. */
function paint(root: SVGGElement, nodes: FNode[]): void {
  const join = select(root)
    .selectAll<SVGGElement, FNode>(`g.${flowClass.node}`)
    .data(nodes, (n) => n.id)
  join.exit().remove()
  const entered = join.enter().append('g').attr('class', nodeKindClass)
  drawNodes(entered)
  refreshNodes(entered.merge(join), visuals)
}

function newRoot(): SVGGElement {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
  const g = document.createElementNS('http://www.w3.org/2000/svg', 'g')
  svg.appendChild(g)
  document.body.appendChild(svg)
  return g
}

describe('flow paint — a later topology push', () => {
  it('re-sizes a service dot when its host crosses a service-count bucket', () => {
    const root = newRoot()
    paint(root, [node({ id: 'h/svc', nodeType: 'service', hostId: 'h', svcTotalCount: 5 })])

    // The same node, now on a host with 30 services: the layout packs the ring
    // tighter, so the dot has to shrink with it rather than keep r=11.
    paint(root, [node({ id: 'h/svc', nodeType: 'service', hostId: 'h', svcTotalCount: 30 })])

    const group = root.querySelector(`g.${flowClass.node}`)!
    expect(group.querySelector('circle')!.getAttribute('r')).toBe('6')
    const label = group.querySelector(`text.${flowClass.label}`) as SVGTextElement
    expect(label.getAttribute('y')).toBe('10')
    // 30 services is past the point where their names still fit.
    expect(label.style.display).toBe('none')
  })

  it("re-reads a '+N more' stand-in's glyph when the count behind it changes", () => {
    const root = newRoot()
    paint(root, [
      node({ id: 'h/more', nodeType: 'more', hostId: 'h', svcTotalCount: 5, moreCount: 3 })
    ])

    paint(root, [
      node({ id: 'h/more', nodeType: 'more', hostId: 'h', svcTotalCount: 30, moreCount: 25 })
    ])

    const glyph = root.querySelector<SVGTextElement>(`g.${flowClass.node} text.${flowClass.glyph}`)!
    expect(glyph.textContent).toBe('+25')
    expect(glyph.style.fontSize).toBe('7px')
  })
})

describe('flow paint — fold-backs', () => {
  it("puts an opened group's fold-back badge on its head's edge, towards its hosts", () => {
    const site = node({ id: 'site', nodeType: 'site', x: 0, y: 0 })
    const head = node({ id: 'router', nodeType: 'host', x: 100, y: 40 })
    const hosts = [0, 1].map((i) => node({ id: `host-${i}`, nodeType: 'host', x: 300, y: i * 66 }))
    const frames: HostFrame[] = [
      { head: site, members: [head, ...hosts], opened: false },
      { head, members: hosts, opened: true }
    ]
    const layer = newRoot()

    positionFoldBacks(
      drawFoldBacks(layer, frames, { label: () => 'Collapse', onFold: () => {} }),
      1
    )

    const badges = layer.querySelectorAll(`g.${flowClass.foldBack}`)
    expect(badges).toHaveLength(1)
    expect(badges[0]!.getAttribute('aria-expanded')).toBe('true')
    const [, x, y] = /translate\(([-\d.]+),([-\d.]+)\)/.exec(badges[0]!.getAttribute('transform')!)!
    expect([Number(x), Number(y)]).toEqual([head.x! + donutOuterRadius(1), head.y])
  })
})

describe('flow paint — an edge', () => {
  const host = (id: string): FNode => ({
    id,
    nodeType: 'host',
    state: 'UP',
    output: '',
    bfsLevel: 0
  })

  it('is drawn afresh when it turns into the edge of a further parent', () => {
    const [source, target] = [host('router'), host('app01')]
    const tree = { source, target, sourceState: 'UP', isServiceLink: false }
    expect(linkKey({ ...tree, furtherParent: true })).not.toBe(linkKey(tree))
  })
})
