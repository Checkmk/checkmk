/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { select } from 'd3-selection'
import { describe, expect, it } from 'vitest'

import type { FNode } from '@/maps/map/flow/nodes'
import {
  type NodeVisuals,
  drawNodes,
  flowClass,
  nodeKindClass,
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
  moreLabel: (count) => `+${count} more`
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

    const glyph = root.querySelector(`g.${flowClass.node} text.${flowClass.glyph}`)!
    expect(glyph.textContent).toBe('+25')
    expect(glyph.getAttribute('font-size')).toBe('7')
  })
})
