/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { select } from 'd3-selection'
import { afterEach, describe, expect, it } from 'vitest'
import { ref } from 'vue'

import { useFlowSelection } from '@/maps/map/flow/composables/useFlowSelection'
import { siteNodeId } from '@/maps/map/flow/nodeIds'
import type { FNode } from '@/maps/map/flow/nodes'
import { flowClass } from '@/maps/map/flow/paint'
import type { MapElement } from '@/maps/types/api'

const SVG_NS = 'http://www.w3.org/2000/svg'

function hostNode(name: string): FNode {
  return { id: name, state: 'UP', output: '', bfsLevel: 1, nodeType: 'host' }
}

function siteNode(siteId: string): FNode {
  return {
    id: siteNodeId(siteId),
    state: 'UP',
    output: '',
    bfsLevel: 0,
    nodeType: 'site',
    siteId
  }
}

/** What the view hands the composable — enough of it for the assertions. */
function mapElementFromFNode(node: FNode): MapElement {
  return node.nodeType === 'site'
    ? ({ id: node.id, type: 'site', x: 0, y: 0, host_name: node.siteId } as MapElement)
    : ({ id: node.id, type: 'host', x: 0, y: 0, host_name: node.id } as MapElement)
}

/**
 * The drawn map, as the band reads it: one ``g`` per node at a known place.
 * jsdom lays nothing out, so every box is stubbed — the composable only ever
 * asks for the rectangles.
 */
function drawnMap(nodes: readonly { node: FNode; x: number; y: number }[]): SVGSVGElement {
  const svg = document.createElementNS(SVG_NS, 'svg')
  svg.getBoundingClientRect = () => new DOMRect(0, 0, 900, 600)
  // jsdom implements no pointer capture; the band only ever holds and drops it.
  let captured = false
  svg.setPointerCapture = () => {
    captured = true
  }
  svg.hasPointerCapture = () => captured
  svg.releasePointerCapture = () => {
    captured = false
  }
  document.body.appendChild(svg)
  for (const { x, y } of nodes) {
    const group = document.createElementNS(SVG_NS, 'g')
    group.setAttribute('class', flowClass.node)
    group.getBoundingClientRect = () => new DOMRect(x - 10, y - 10, 20, 20)
    svg.appendChild(group)
  }
  select(svg)
    .selectAll<SVGGElement, FNode>(`g.${flowClass.node}`)
    .data(nodes.map((placed) => placed.node))
  return svg
}

/** A band pulled from one corner to the other, as the operator drags it. */
function dragBand(
  svg: SVGSVGElement,
  from: { x: number; y: number },
  to: { x: number; y: number }
): void {
  const event = (type: string, at: { x: number; y: number }): PointerEvent =>
    new PointerEvent(type, {
      bubbles: true,
      shiftKey: true,
      button: 0,
      pointerId: 1,
      clientX: at.x,
      clientY: at.y
    })
  svg.dispatchEvent(event('pointerdown', from))
  svg.dispatchEvent(event('pointermove', to))
  svg.dispatchEvent(event('pointerup', to))
}

function selectionOver(svg: SVGSVGElement) {
  const selection = useFlowSelection({ svgEl: ref(svg), mapElementFromFNode })
  selection.attachMarquee(svg)
  return selection
}

describe('useFlowSelection', () => {
  afterEach(() => {
    document.body.replaceChildren()
  })

  it('leaves the site root out of a band pulled over it', () => {
    // A site root is a drawn grouping, and its ``host_name`` is the site id.
    // Lassoing one and acknowledging the selection would send the command to a
    // host that does not exist, so the band skips it — just as shift-click does.
    const svg = drawnMap([
      { node: siteNode('heute'), x: 100, y: 100 },
      { node: hostNode('web-01'), x: 200, y: 100 }
    ])
    const selection = selectionOver(svg)

    dragBand(svg, { x: 50, y: 50 }, { x: 400, y: 300 })

    expect(selection.selectedObjects.value.map((object) => object.host_name)).toEqual(['web-01'])
  })

  it('picks up every host whose centre the band covers', () => {
    const svg = drawnMap([
      { node: hostNode('web-01'), x: 100, y: 100 },
      { node: hostNode('db-01'), x: 200, y: 100 },
      { node: hostNode('far-away'), x: 800, y: 500 }
    ])
    const selection = selectionOver(svg)

    dragBand(svg, { x: 50, y: 50 }, { x: 400, y: 300 })

    expect(selection.selectedObjects.value.map((object) => object.host_name)).toEqual([
      'web-01',
      'db-01'
    ])
  })

  it('takes no site root by hand either', () => {
    const svg = drawnMap([{ node: siteNode('heute'), x: 100, y: 100 }])
    const selection = selectionOver(svg)

    selection.toggle(siteNode('heute'))

    expect(selection.selectedObjects.value).toEqual([])
  })
})
