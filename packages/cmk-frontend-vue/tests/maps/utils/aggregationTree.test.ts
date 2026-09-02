/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import type { AggregationNode } from '@/maps/types/api'
import {
  aggregationLeafId,
  countLeavesByState,
  flattenAggregationLeaves,
  walkAggregationLeavesWithPath
} from '@/maps/utils/aggregationTree'

import { anAggregationNode } from '../support/fixtures'

function leaf(name: string, extra: Partial<AggregationNode> = {}): AggregationNode {
  return anAggregationNode({ name, node_type: 'bi_leaf', state: 0, children: [], ...extra })
}

function agg(name: string, children: AggregationNode[], state = 0): AggregationNode {
  return anAggregationNode({ name, node_type: 'bi_aggregator', state, children })
}

describe('flattenAggregationLeaves', () => {
  it('collects leaves across nested aggregators in order', () => {
    const tree = agg('root', [
      agg('branch-a', [leaf('l1'), leaf('l2')]),
      agg('branch-b', [leaf('l3')])
    ])
    expect(flattenAggregationLeaves(tree).map((l) => l.name)).toEqual(['l1', 'l2', 'l3'])
  })

  it('returns the node itself when it is already a leaf', () => {
    expect(flattenAggregationLeaves(leaf('solo')).map((l) => l.name)).toEqual(['solo'])
  })

  it('returns nothing for an aggregator with no children', () => {
    expect(flattenAggregationLeaves(agg('empty', []))).toEqual([])
  })
})

describe('walkAggregationLeavesWithPath', () => {
  it('records the aggregator path down to each leaf', () => {
    const tree = agg('root', [agg('branch', [leaf('l1')])])
    expect(walkAggregationLeavesWithPath(tree)).toEqual([
      { leaf: expect.objectContaining({ name: 'l1' }), path: ['root', 'branch', 'l1'] }
    ])
  })

  it('uses just the leaf name for a top-level leaf', () => {
    expect(walkAggregationLeavesWithPath(leaf('solo'))[0]!.path).toEqual(['solo'])
  })
})

describe('aggregationLeafId', () => {
  it('builds a host;service id when a service is present', () => {
    expect(aggregationLeafId(leaf('x', { host_name: 'web01', service_description: 'ping' }))).toBe(
      'web01;ping'
    )
  })

  it('tolerates a missing host on a service leaf', () => {
    expect(aggregationLeafId(leaf('x', { service_description: 'ping' }))).toBe(';ping')
  })

  it('falls back to the host name for host leaves', () => {
    expect(aggregationLeafId(leaf('x', { host_name: 'web01' }))).toBe('web01')
  })

  it('falls back to the node name when neither host nor service exists', () => {
    expect(aggregationLeafId(leaf('synthetic'))).toBe('synthetic')
  })
})

describe('countLeavesByState', () => {
  it('tallies leaves into the four BI state buckets', () => {
    const leaves = [
      leaf('a', { state: 0 }),
      leaf('b', { state: 2 }),
      leaf('c', { state: 2 }),
      leaf('d', { state: 1 })
    ]
    expect(countLeavesByState(leaves)).toEqual({ 0: 1, 1: 1, 2: 2, 3: 0 })
  })

  it('returns an all-zero tally for no leaves', () => {
    expect(countLeavesByState([])).toEqual({ 0: 0, 1: 0, 2: 0, 3: 0 })
  })
})
