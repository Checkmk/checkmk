/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, it } from 'vitest'

import {
  crowdingWarning,
  leafSample,
  leafStateCounts,
  leavesBeyondSample,
  leavesOf
} from '@/maps/map/edit/aggregationPreviewFacts'
import type { AggregationNode } from '@/maps/types/api'

const _t = ((message: string, args?: Record<string, unknown>) =>
  untranslated(message.replace('%{count}', String(args?.count)))) as never

function leaf(name: string, state: number): AggregationNode {
  return {
    node_type: 'bi_leaf',
    name,
    state,
    host_name: name,
    output: '',
    acknowledged: false,
    in_downtime: false,
    children: []
  }
}

function branch(children: AggregationNode[]): AggregationNode {
  return {
    node_type: 'bi_aggregator',
    name: 'root',
    state: 0,
    output: '',
    acknowledged: false,
    in_downtime: false,
    children
  }
}

describe('leavesOf', () => {
  it('has nothing to show without a tree', () => {
    expect(leavesOf(null)).toEqual([])
  })

  it('flattens the tree down to its leaves', () => {
    expect(leavesOf(branch([leaf('a', 0), branch([leaf('b', 2)])])).map((l) => l.name)).toEqual([
      'a',
      'b'
    ])
  })
})

describe('leafStateCounts', () => {
  it('lists the states problems-first and counts every leaf', () => {
    const counts = leafStateCounts([leaf('a', 0), leaf('b', 2), leaf('c', 2), leaf('d', 1)])

    expect(counts.map((count) => count.label)).toEqual(['CRIT', 'WARN', 'UNKN', 'OK'])
    expect(counts.map((count) => count.count)).toEqual([2, 1, 0, 1])
  })

  it('colours each state from the shared state tokens', () => {
    expect(leafStateCounts([leaf('a', 0)])[3]!.color).toBe('var(--color-state-ok)')
  })
})

describe('leafSample', () => {
  it('names the first few leaves and counts the rest', () => {
    const leaves = ['a', 'b', 'c', 'd', 'e', 'f', 'g'].map((name) => leaf(name, 0))

    expect(leafSample(leaves).map((entry) => entry.label)).toEqual(['a', 'b', 'c', 'd', 'e'])
    expect(leavesBeyondSample(leaves)).toBe(2)
  })

  it('counts nothing beyond the sample for a small tree', () => {
    expect(leavesBeyondSample([leaf('a', 0)])).toBe(0)
  })
})

describe('crowdingWarning', () => {
  const many = Array.from({ length: 51 }, (_, index) => leaf(`h${index}`, 0))

  it('warns once an expanded subtree would fan out that far', () => {
    expect(crowdingWarning(many, 2, _t)).toContain('51 nodes')
  })

  it('stays quiet at depth 0, which draws the root glyph alone', () => {
    expect(crowdingWarning(many, 0, _t)).toBeNull()
  })

  it('stays quiet for a tree that still fits', () => {
    expect(crowdingWarning(many.slice(0, 20), 3, _t)).toBeNull()
  })
})
