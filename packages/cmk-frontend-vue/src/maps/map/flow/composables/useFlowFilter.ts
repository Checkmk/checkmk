/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Narrowing a flow map down to what the operator is looking for.
 *
 * Non-matching nodes are dimmed and desaturated rather than removed, and the
 * matches are raised above them. Removing them would change the graph, which
 * would restart the force simulation and rearrange the whole map on every
 * keystroke — the operator would lose the picture they were reading.
 *
 * The group operators the other map types accept are dropped: a flow map's
 * nodes are only ever hosts and services, so a group term could never match.
 */
import { select } from 'd3-selection'
import { type Ref, computed, watch } from 'vue'

import { HEALTHY_HOST_STATES } from '@/maps/map/flow/geometry'
import { serviceNameOf } from '@/maps/map/flow/nodeIds'
import type { FLink, FNode } from '@/maps/map/flow/nodes'
import { flowClass } from '@/maps/map/flow/paint'
import {
  DIMMED_FILTER,
  DIMMED_OPACITY,
  type FilterField,
  matchesFilterTerms,
  parseFilterTerms
} from '@/maps/utils/objectFilter'

const UNSUPPORTED_FIELDS: ReadonlySet<FilterField> = new Set(['hostgroup', 'servicegroup'])

interface FlowFilterOptions {
  svgEl: Readonly<Ref<SVGSVGElement | null>>
  /** What the operator typed into the map's search. */
  needle: () => string
  problemsOnly: () => boolean
  worstServiceState: (node: FNode) => string | null
}

export function useFlowFilter(options: FlowFilterOptions) {
  const { svgEl, needle, problemsOnly, worstServiceState } = options

  // Parsed once per keystroke rather than once per node: the match runs inside
  // three loops over every node the map draws.
  const terms = computed(() =>
    parseFilterTerms(needle()).filter((term) => !UNSUPPORTED_FIELDS.has(term.field))
  )
  const isActive = computed(() => problemsOnly() || terms.value.length > 0)

  function hasProblem(node: FNode): boolean {
    if (node.nodeType === 'host') {
      return !HEALTHY_HOST_STATES.has(node.state) || worstServiceState(node) !== null
    }
    return node.state !== 'OK' && node.state !== 'PENDING'
  }

  function fieldValue(node: FNode, field: FilterField): string[] {
    const serviceName = node.nodeType === 'service' ? serviceNameOf(node.id) : ''
    const hostName =
      node.nodeType === 'service' || node.nodeType === 'more' ? (node.hostId ?? '') : node.id
    switch (field) {
      case 'host':
        return [hostName, node.topo?.alias ?? node.parentTopo?.alias ?? '']
      case 'service':
        return [serviceName]
      case 'id':
        return [node.id]
      case 'any':
        return [
          node.id,
          hostName,
          serviceName,
          node.topo?.alias ?? '',
          node.parentTopo?.alias ?? ''
        ]
      case 'hostgroup':
      case 'servicegroup':
        return []
    }
  }

  function matches(node: FNode): boolean {
    if (problemsOnly() && !hasProblem(node)) {
      return false
    }
    return matchesFilterTerms(terms.value, (field) => fieldValue(node, field))
  }

  // Whether the dimming is currently written into the DOM, so an inactive
  // filter clears it once instead of on every render.
  let dimmed = false

  function apply(): void {
    if (!svgEl.value) {
      return
    }
    const area = select(svgEl.value)
    const nodes = `g.${flowClass.node}`
    const links = `line.${flowClass.link}`
    if (!isActive.value) {
      if (!dimmed) {
        return
      }
      dimmed = false
      area.selectAll(`${nodes}, ${links}`).attr('opacity', 1)
      area.selectAll(nodes).style('filter', null)
      return
    }
    dimmed = true
    // Matched once per node, not once per read: each match parses nothing but
    // it does allocate a string per field per term, and the three node
    // callbacks and the link callback below would each ask again.
    const matched = new Set<string>()
    const nodeSelection = area.selectAll<SVGGElement, FNode>(nodes)
    nodeSelection.each((node) => {
      if (matches(node)) {
        matched.add(node.id)
      }
    })
    nodeSelection
      .attr('opacity', (node) => (matched.has(node.id) ? 1 : DIMMED_OPACITY))
      .style('filter', (node) => (matched.has(node.id) ? null : DIMMED_FILTER))
      .filter((node) => matched.has(node.id))
      .raise()
    area
      .selectAll<SVGLineElement, FLink>(links)
      .attr('opacity', (link) =>
        matched.has(link.source.id) && matched.has(link.target.id) ? 1 : DIMMED_OPACITY
      )
  }

  watch([terms, problemsOnly], () => apply())

  return { apply }
}
