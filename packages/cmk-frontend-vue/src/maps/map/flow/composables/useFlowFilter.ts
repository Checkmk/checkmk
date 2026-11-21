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
 * keystroke — the operator would lose the picture they were reading. Only a
 * hit folded away is worth that: the map then draws it, once typing pauses.
 *
 * The group operators the other map types accept are dropped: a flow map's
 * nodes are only ever hosts and services, so a group term could never match.
 */
import { select } from 'd3-selection'
import { type Ref, computed, watch } from 'vue'

import { HEALTHY_HOST_STATES } from '@/maps/map/flow/geometry'
import { KIND_TRAITS, serviceNameOf, serviceNodeId } from '@/maps/map/flow/nodeIds'
import type { FLink, FNode } from '@/maps/map/flow/nodes'
import { flowClass } from '@/maps/map/flow/paint'
import type { TopologyNode } from '@/maps/types/api'
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
    if (KIND_TRAITS[node.nodeType].hostShaped) {
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

  /**
   * The hosts the search names, itself or by one of its services, so a map that
   * folds hosts away can draw them.
   */
  function foundHosts(topology: readonly TopologyNode[]): Set<string> {
    if (!terms.value.length) {
      return new Set()
    }
    const named = (node: FNode): boolean =>
      matchesFilterTerms(terms.value, (field) => fieldValue(node, field))
    return new Set(
      topology
        .filter(
          (topo) =>
            named({
              id: topo.name,
              nodeType: 'host',
              state: topo.state,
              output: '',
              bfsLevel: 0,
              topo
            }) ||
            (topo.services ?? []).some((service) =>
              named({
                id: serviceNodeId(topo.name, service.name),
                nodeType: 'service',
                hostId: topo.name,
                state: service.state,
                output: '',
                bfsLevel: 0,
                parentTopo: topo
              })
            )
        )
        .map((topo) => topo.name)
    )
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
    const links = `path.${flowClass.link}`
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
    const linkSelection = area.selectAll<SVGPathElement, FLink>(links)
    const shown = terms.value.length ? withPathsUp(matched, linkSelection.data()) : matched
    nodeSelection
      .attr('opacity', (node) => (shown.has(node.id) ? 1 : DIMMED_OPACITY))
      .style('filter', (node) => (shown.has(node.id) ? null : DIMMED_FILTER))
      .filter((node) => matched.has(node.id))
      .raise()
    linkSelection.attr('opacity', (link) =>
      shown.has(link.source.id) && shown.has(link.target.id) ? 1 : DIMMED_OPACITY
    )
  }

  /**
   * The hits and what they hang from, up to their site: a host found is read
   * by where it sits, which a dimmed path would hide.
   */
  function withPathsUp(matched: ReadonlySet<string>, drawnLinks: FLink[]): Set<string> {
    const parentOf = new Map<string, string>()
    for (const link of drawnLinks) {
      // The tree's own parent, not a further one: the path is read as drawn.
      if (!link.isServiceLink && !link.furtherParent) {
        parentOf.set(link.target.id, link.source.id)
      }
    }
    const shown = new Set(matched)
    for (const id of matched) {
      let parent = parentOf.get(id)
      while (parent !== undefined && !shown.has(parent)) {
        shown.add(parent)
        parent = parentOf.get(parent)
      }
    }
    return shown
  }

  watch([terms, problemsOnly], () => apply())

  return { apply, foundHosts }
}
