/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import { defineComponent, ref } from 'vue'

import AggregationSubtree from '@/maps/map/static/components/AggregationSubtree.vue'
import type { AggregationNode, MapElement, ObjectState } from '@/maps/types/api'

import { anAggregationNode } from '../../../support/fixtures'

// The subtree is pure SVG geometry: its nodes are unlabeled <g> groups without
// an accessible representation (no role/aria-label — see the report on the
// missing keyboard path), so all structural assertions stay container-scoped
// DOM queries.

const WORST_PATH_COLOR = 'rgb(244 114 182)'

function leaf(name: string, state: number, extra: Partial<AggregationNode> = {}): AggregationNode {
  return anAggregationNode({
    name,
    node_type: 'bi_leaf',
    state,
    children: [],
    host_name: name,
    ...extra
  })
}

function agg(name: string, children: AggregationNode[], state = 0): AggregationNode {
  return anAggregationNode({ name, node_type: 'bi_aggregator', state, children })
}

function renderTree(tree: AggregationNode, maxDepth = 5): Element {
  const { container } = render(AggregationSubtree, {
    props: { tree, iconSize: 32, maxDepth }
  })
  return container
}

describe('AggregationSubtree rendering', () => {
  it('renders one node per non-root tree node', () => {
    const tree = agg('root', [leaf('a', 0), leaf('b', 0)])
    const container = renderTree(tree)
    // Root is the map icon itself and is skipped.
    expect(container.querySelectorAll('.maps-aggregation-subtree__node')).toHaveLength(2)
  })

  it('draws a link per parent-child edge', () => {
    const tree = agg('root', [leaf('a', 0), agg('mid', [leaf('c', 0)])])
    const container = renderTree(tree)
    // 3 non-root nodes → 3 edges from their parents.
    expect(container.querySelectorAll('line')).toHaveLength(3)
  })

  it('respects maxDepth by trimming deeper nodes', () => {
    const deep = agg('root', [agg('mid', [leaf('deep', 0)])])
    const container = renderTree(deep, 1)
    // Only the depth-1 "mid" node remains; the depth-2 leaf is trimmed.
    expect(container.querySelectorAll('.maps-aggregation-subtree__node')).toHaveLength(1)
  })
})

describe('AggregationSubtree worst-path highlight', () => {
  it('highlights only the link to the worst leaf', () => {
    const tree = agg('root', [leaf('ok', 0), leaf('crit', 2)])
    const container = renderTree(tree)
    const worstLinks = [...container.querySelectorAll('line')].filter(
      (l) => l.getAttribute('stroke') === WORST_PATH_COLOR
    )
    expect(worstLinks).toHaveLength(1)
  })

  it('has no highlight when every leaf is OK', () => {
    const tree = agg('root', [leaf('a', 0), leaf('b', 0)])
    const container = renderTree(tree)
    const worstLinks = [...container.querySelectorAll('line')].filter(
      (l) => l.getAttribute('stroke') === WORST_PATH_COLOR
    )
    expect(worstLinks).toHaveLength(0)
  })
})

describe('AggregationSubtree node decoration', () => {
  it('writes name, state and flags into the node tooltip', () => {
    const tree = agg('root', [leaf('web01', 2, { acknowledged: true })])
    const container = renderTree(tree)
    const title = container.querySelector('.maps-aggregation-subtree__node title')
    expect(title?.textContent).toContain('web01')
    expect(title?.textContent).toContain('CRITICAL')
    expect(title?.textContent).toContain('ack')
  })

  it('dashes the circle stroke for a node in downtime', () => {
    const tree = agg('root', [leaf('web01', 1, { in_downtime: true })])
    const container = renderTree(tree)
    const circle = container.querySelector('.maps-aggregation-subtree__node circle')
    expect(circle?.getAttribute('stroke-dasharray')).toBe('3 2')
  })
})

describe('AggregationSubtree interaction', () => {
  it('reports node-enter with a synthetic object and state on hover', async () => {
    const tree = agg('root', [leaf('web01', 2)])
    // node-enter is the hover contract; capture it via a real handler on a
    // host wrapper instead of inspecting emitted events.
    const entered = ref<{ obj: MapElement; state: ObjectState } | null>(null)
    const { container } = render(
      defineComponent({
        components: { AggregationSubtree },
        setup() {
          const onNodeEnter = (obj: MapElement, state: ObjectState) => {
            entered.value = { obj, state }
          }
          return { tree, onNodeEnter }
        },
        template: `
          <AggregationSubtree :tree="tree" :icon-size="32" :max-depth="5" @node-enter="onNodeEnter" />
        `
      })
    )

    // mouseenter on the SVG node group is the exact contract event; the group
    // has no accessible role, so it is located via a container-scoped query.
    await fireEvent.mouseEnter(container.querySelector('.maps-aggregation-subtree__node')!)

    expect(entered.value?.obj.host_name).toBe('web01')
    expect(entered.value?.state.state).toBe('CRITICAL')
  })
})
