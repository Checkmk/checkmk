/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { select } from 'd3-selection'
import { describe, expect, it } from 'vitest'
import { ref } from 'vue'

import { useFlowFilter } from '@/maps/map/flow/composables/useFlowFilter'
import type { FLink, FNode } from '@/maps/map/flow/nodes'
import { flowClass } from '@/maps/map/flow/paint'
import { DIMMED_OPACITY } from '@/maps/utils/objectFilter'

import { aTopologyNode } from '../../../support/fixtures'

const SVG_NS = 'http://www.w3.org/2000/svg'

function aNode(id: string, nodeType: FNode['nodeType'] = 'host'): FNode {
  return { id, nodeType, state: 'UP', output: '', bfsLevel: 0 }
}

/** A site with ``router`` under it, and ``app01`` and ``db01`` under the router. */
function drawnTree(): SVGSVGElement {
  const site = aNode('site:heute', 'site')
  const router = aNode('router')
  const nodes = [site, router, aNode('app01'), aNode('db01')]
  const links: FLink[] = [
    { source: site, target: router, sourceState: 'UP', isServiceLink: false },
    { source: router, target: nodes[2]!, sourceState: 'UP', isServiceLink: false },
    { source: router, target: nodes[3]!, sourceState: 'UP', isServiceLink: false }
  ]
  const svg = document.createElementNS(SVG_NS, 'svg')
  const area = select(svg)
  area.selectAll('g').data(nodes).enter().append('g').attr('class', flowClass.node)
  area.selectAll('path').data(links).enter().append('path').attr('class', flowClass.link)
  return svg
}

function opacityOf(svg: SVGSVGElement, id: string): string | null {
  const node = select(svg)
    .selectAll<SVGGElement, FNode>(`g.${flowClass.node}`)
    .filter((candidate) => candidate.id === id)
  return node.attr('opacity')
}

describe('useFlowFilter', () => {
  it('keeps a hit readable by what it hangs from, up to its site', () => {
    const svg = drawnTree()
    const filter = useFlowFilter({
      svgEl: ref(svg),
      needle: () => 'app01',
      problemsOnly: () => false,
      worstServiceState: () => null
    })
    filter.apply()
    expect(['site:heute', 'router', 'app01'].map((id) => opacityOf(svg, id))).toEqual([
      '1',
      '1',
      '1'
    ])
    expect(opacityOf(svg, 'db01')).toBe(String(DIMMED_OPACITY))
  })

  it('finds a host by one of its services', () => {
    const filter = useFlowFilter({
      svgEl: ref(null),
      needle: () => 's:ntp',
      problemsOnly: () => false,
      worstServiceState: () => null
    })
    const topology = [
      aTopologyNode({
        name: 'app01',
        services: [
          {
            name: 'NTP Time',
            state: 'OK',
            output: '',
            acknowledged: false,
            in_downtime: false,
            notifications_enabled: true
          }
        ]
      }),
      aTopologyNode({ name: 'db01' })
    ]
    expect([...filter.foundHosts(topology)]).toEqual(['app01'])
  })
})
