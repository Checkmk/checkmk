/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AggregationNode, MonitoringState } from '@/maps/types/api'
import { stateRank } from '@/maps/utils/stateColors'

export const BI_STATE_LABEL: Record<number, string> = {
  0: 'OK',
  1: 'WARN',
  2: 'CRIT',
  3: 'UNKN'
}

// Same codes mapped to MonitoringState names — used where BI nodes mix with
// host/service state-color lookups (stateColorVar() expects "OK"/"WARNING"/...).
export const BI_STATE_FULL_LABEL: Record<number, MonitoringState> = {
  0: 'OK',
  1: 'WARNING',
  2: 'CRITICAL',
  3: 'UNKNOWN'
}

/** A BI state's severity on Checkmk's ladder; the state code itself ranks UNKNOWN above CRIT. */
export function biStateRank(state: number): number {
  return stateRank(BI_STATE_FULL_LABEL[state])
}

export const BI_STATE_TONE: Record<number, 'ok' | 'warn' | 'crit' | 'unknown'> = {
  0: 'ok',
  1: 'warn',
  2: 'crit',
  3: 'unknown'
}

export function flattenAggregationLeaves(
  node: AggregationNode,
  out: AggregationNode[] = []
): AggregationNode[] {
  if (node.node_type === 'bi_leaf') {
    out.push(node)
  } else {
    for (const child of node.children) {
      flattenAggregationLeaves(child, out)
    }
  }
  return out
}

export interface AggregationLeafWithPath {
  leaf: AggregationNode
  path: string[]
}

export function walkAggregationLeavesWithPath(
  node: AggregationNode,
  path: string[] = []
): AggregationLeafWithPath[] {
  if (node.node_type === 'bi_leaf') {
    return [{ leaf: node, path: [...path, node.name] }]
  }
  const out: AggregationLeafWithPath[] = []
  const sub = [...path, node.name]
  for (const child of node.children) {
    out.push(...walkAggregationLeavesWithPath(child, sub))
  }
  return out
}

// Stable identifier for a leaf, matching the (host, service) shape the
// detail drawer + bulk-ack paths use. Falls back to the leaf's `name`
// for synthetic / placeholder leaves that carry neither.
export function aggregationLeafId(leaf: AggregationNode): string {
  if (leaf.service_description) {
    return `${leaf.host_name ?? ''};${leaf.service_description}`
  }
  return leaf.host_name ?? leaf.name
}

export function countLeavesByState(leaves: AggregationNode[]): Record<number, number> {
  const counts: Record<number, number> = { 0: 0, 1: 0, 2: 0, 3: 0 }
  for (const l of leaves) {
    counts[l.state] = (counts[l.state] ?? 0) + 1
  }
  return counts
}
