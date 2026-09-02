<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type HierarchyNode, tree as d3Tree, hierarchy } from 'd3-hierarchy'
import { computed } from 'vue'

import type { AggregationNode, MapElement, ObjectState } from '@/maps/types/api'
import { BI_STATE_FULL_LABEL } from '@/maps/utils/aggregationTree'
import { resolveCheckmkUrl } from '@/maps/utils/deploymentBase'
import { buildCheckmkUrl, openUrl } from '@/maps/utils/mapNavigation'
import { newMapElement, newObjectState } from '@/maps/utils/model'
import { ACKNOWLEDGED_COLOR, DOWNTIME_COLOR, stateColor } from '@/maps/utils/stateColors'

const props = defineProps<{
  tree: AggregationNode
  iconSize: number
  maxDepth: number
  lineColor?: string | null
  lineWidth?: number | null
}>()

// Default subtree line: zinc-400 at full alpha (1.5px) reads on both light and
// dark map tiles. The legacy "zinc-500 @ 50% alpha, 1px" washed out anywhere
// the map background was busy.
const DEFAULT_LINE_COLOR = 'rgb(161 161 170)'
const DEFAULT_LINE_WIDTH = 1.5
const resolvedLineColor = computed(() => props.lineColor || DEFAULT_LINE_COLOR)
const resolvedLineWidth = computed(() => props.lineWidth ?? DEFAULT_LINE_WIDTH)
// Worst-path edges stay one step thicker than the regular tree edges so the
// highlight still reads when the operator picks a custom heavy stroke.
const worstPathLineWidth = computed(() => resolvedLineWidth.value + 1.5)

function trimToDepth(node: AggregationNode, remaining: number): AggregationNode {
  if (node.children.length === 0) {
    return node
  }
  if (remaining <= 0) {
    return { ...node, children: [] }
  }
  return { ...node, children: node.children.map((c) => trimToDepth(c, remaining - 1)) }
}

const trimmedTree = computed(() => trimToDepth(props.tree, props.maxDepth))

const emit = defineEmits<{
  'node-enter': [obj: MapElement, state: ObjectState, event: MouseEvent]
  'node-leave': []
}>()

// Sizes scale with the map's icon size so subtree nodes look proportional.
const nodeRadius = computed(() => Math.max(8, props.iconSize * 0.4))
const fontSize = computed(() => Math.max(11, Math.round(props.iconSize * 0.42)))
const vSpacing = computed(() => Math.max(70, props.iconSize * 2.6))
const hSpacing = computed(() => Math.max(120, props.iconSize * 4))

const MAX_LABEL = 18
const BADGE_OFFSET_F = 0.7 // badge center offset from node center (× nodeRadius)
const BADGE_RADIUS_F = 0.55 // badge circle radius (× nodeRadius)
const TOP_PAD = 20 // top inset before the root row
const LABEL_PAD = 60 // extra horizontal padding for label overflow
// Highlight colour for the path from the root to the worst leaf.
// Stays distinct from the state-fill colours (which use saturated
// reds/yellows for actual leaf state) so the path stands out as a
// trace rather than another state colour.
const WORST_PATH_COLOR = 'rgb(244 114 182)'

function stateColorFor(node: AggregationNode): string {
  return stateColor(BI_STATE_FULL_LABEL[node.state] ?? 'PENDING')
}

function strokeFor(node: AggregationNode): string {
  if (node.in_downtime) {
    return DOWNTIME_COLOR
  }
  if (node.acknowledged) {
    return ACKNOWLEDGED_COLOR
  }
  return 'rgb(24 24 27)'
}

function truncate(s: string): string {
  return s.length > MAX_LABEL ? `${s.slice(0, MAX_LABEL - 2)}…` : s
}

function tooltipFor(node: AggregationNode): string {
  const stateLabel = BI_STATE_FULL_LABEL[node.state] ?? 'PENDING'
  const flags: string[] = []
  if (node.in_downtime) {
    flags.push('downtime')
  }
  if (node.acknowledged) {
    flags.push('ack')
  }
  const suffix = flags.length ? ` (${flags.join(', ')})` : ''
  return `${node.name} — ${stateLabel}${suffix}`
}

function syntheticObject(node: AggregationNode): MapElement {
  const isLeaf = node.node_type === 'bi_leaf'
  const type = isLeaf ? (node.service_description ? 'service' : 'host') : 'aggregation'
  return newMapElement({
    id: `bi-subtree-${node.host_name ?? ''}-${node.service_description ?? ''}-${node.name}`,
    type,
    z: 1,
    host_name: node.host_name ?? null,
    service_description: node.service_description ?? null,
    aggregation_id: isLeaf ? null : node.name
  })
}

function syntheticState(obj: MapElement, node: AggregationNode): ObjectState {
  return newObjectState({
    object_id: obj.id,
    type: obj.type,
    state: BI_STATE_FULL_LABEL[node.state] ?? 'PENDING',
    acknowledged: node.acknowledged,
    in_downtime: node.in_downtime
  })
}

function onNodeClick(node: AggregationNode) {
  if (node.node_type !== 'bi_leaf' || !node.host_name) {
    return
  }
  const url = buildCheckmkUrl(syntheticObject(node), resolveCheckmkUrl())
  if (url) {
    openUrl(url, '_blank')
  }
}

function onNodeEnter(node: AggregationNode, event: MouseEvent) {
  const obj = syntheticObject(node)
  emit('node-enter', obj, syntheticState(obj, node), event)
}

interface RenderedNode {
  id: string
  x: number
  y: number
  data: AggregationNode
  onWorstPath: boolean
}
interface RenderedLink {
  key: string
  x1: number
  y1: number
  x2: number
  y2: number
  onWorstPath: boolean
}

// d3.tree() produces a tidy hierarchical layout: every parent's subtree gets a
// contiguous horizontal range, so siblings cluster under their parent and edges
// never cross. nodeSize gives a stable per-node footprint regardless of tree
// width — much more predictable than forceSimulation for strict hierarchies.
const layout = computed(() => {
  const root: HierarchyNode<AggregationNode> = hierarchy(trimmedTree.value, (n) => n.children)
  const layoutFn = d3Tree<AggregationNode>().nodeSize([hSpacing.value, vSpacing.value])
  return layoutFn(root)
})

// Set of d3 hierarchy nodes that lie on the path from the root to the
// worst-state leaf. Operators triaging an aggregation flip want to
// answer "which branch caused this?" without clicking through every
// leaf — highlighting the path makes that visual at a glance.
//
// Tie-break: the deepest leaf wins (more specific failure trumps a
// shallower one of the same severity). When all leaves are OK the set
// is empty and the highlight is a no-op.
const worstPath = computed<Set<HierarchyNode<AggregationNode>>>(() => {
  type HN = HierarchyNode<AggregationNode>
  // Collect leaves first so the comparator can pick its worst without
  // tripping up TS's flow-sensitive narrowing inside the each() callback.
  const problemLeaves: HN[] = []
  layout.value.each((n: HN) => {
    if (n.data.node_type === 'bi_leaf' && n.data.state > 0) {
      problemLeaves.push(n)
    }
  })
  problemLeaves.sort((a, b) => {
    if (a.data.state !== b.data.state) {
      return b.data.state - a.data.state
    }
    return b.depth - a.depth // deeper wins as a tie-break
  })
  const worst = problemLeaves[0]
  if (worst === undefined) {
    return new Set()
  }
  const set = new Set<HN>()
  let cur: HN | null = worst
  while (cur !== null) {
    set.add(cur)
    cur = cur.parent
  }
  return set
})

const renderedNodes = computed<RenderedNode[]>(() => {
  const out: RenderedNode[] = []
  let i = 0
  const path = worstPath.value
  layout.value.each((n) => {
    if (n.depth === 0) {
      i++
      return
    }
    out.push({
      id: `n${i++}`,
      x: n.x ?? 0,
      y: TOP_PAD + (n.y ?? 0),
      data: n.data,
      onWorstPath: path.has(n)
    })
  })
  return out
})

const renderedLinks = computed<RenderedLink[]>(() => {
  const out: RenderedLink[] = []
  let idx = 0
  const path = worstPath.value
  layout.value.each((n) => {
    if (!n.parent) {
      return
    }
    out.push({
      key: `l${idx++}`,
      x1: n.parent.x ?? 0,
      y1: TOP_PAD + (n.parent.y ?? 0),
      x2: n.x ?? 0,
      y2: TOP_PAD + (n.y ?? 0),
      onWorstPath: path.has(n) && path.has(n.parent)
    })
  })
  return out
})

const size = computed(() => {
  let minX = 0
  let maxX = 0
  let maxY = 0
  layout.value.each((n) => {
    const x = n.x ?? 0
    const y = n.y ?? 0
    if (x < minX) {
      minX = x
    }
    if (x > maxX) {
      maxX = x
    }
    if (y > maxY) {
      maxY = y
    }
  })
  return {
    w: Math.max(320, maxX - minX + hSpacing.value + LABEL_PAD),
    h: maxY + vSpacing.value + TOP_PAD * 2
  }
})
</script>

<template>
  <svg
    :width="size.w"
    :height="size.h"
    :viewBox="`${-size.w / 2} 0 ${size.w} ${size.h}`"
    class="maps-aggregation-subtree"
    :style="{ left: `${-size.w / 2 + iconSize / 2}px`, top: `${iconSize}px` }"
  >
    <line
      v-for="link in renderedLinks"
      :key="link.key"
      :x1="link.x1"
      :y1="link.y1"
      :x2="link.x2"
      :y2="link.y2"
      :stroke="link.onWorstPath ? WORST_PATH_COLOR : resolvedLineColor"
      :stroke-width="link.onWorstPath ? worstPathLineWidth : resolvedLineWidth"
    />
    <!-- Root is the MapElement icon itself, so skip it here -->
    <g
      v-for="node in renderedNodes"
      :key="node.id"
      :transform="`translate(${node.x}, ${node.y})`"
      class="maps-aggregation-subtree__node"
      tabindex="0"
      role="button"
      :aria-label="tooltipFor(node.data)"
      @click.stop="onNodeClick(node.data)"
      @keydown.enter.prevent="onNodeClick(node.data)"
      @keydown.space.prevent="onNodeClick(node.data)"
      @mouseenter="onNodeEnter(node.data, $event)"
      @mouseleave="$emit('node-leave')"
    >
      <title>{{ tooltipFor(node.data) }}</title>
      <circle
        :r="nodeRadius"
        :fill="stateColorFor(node.data)"
        :stroke="node.onWorstPath ? WORST_PATH_COLOR : strokeFor(node.data)"
        :stroke-width="
          node.onWorstPath ? 3 : node.data.in_downtime || node.data.acknowledged ? 2.5 : 1.5
        "
        :stroke-dasharray="node.data.in_downtime ? '3 2' : undefined"
      />
      <!-- Downtime/ack badges — same SVG paths as MapElement's badges so
                 the visual language matches across normal icons and subtree nodes. -->
      <g
        v-if="node.data.in_downtime"
        :transform="`translate(${-BADGE_OFFSET_F * nodeRadius}, ${-BADGE_OFFSET_F * nodeRadius})`"
      >
        <circle
          :r="nodeRadius * BADGE_RADIUS_F"
          :fill="DOWNTIME_COLOR"
          stroke="rgb(24 24 27)"
          stroke-width="1"
        />
        <path
          transform="translate(-6, -6) scale(0.5)"
          fill="white"
          d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"
        />
      </g>
      <g
        v-else-if="node.data.acknowledged"
        :transform="`translate(${BADGE_OFFSET_F * nodeRadius}, ${-BADGE_OFFSET_F * nodeRadius})`"
      >
        <circle
          :r="nodeRadius * BADGE_RADIUS_F"
          :fill="ACKNOWLEDGED_COLOR"
          stroke="rgb(24 24 27)"
          stroke-width="1"
        />
        <path
          transform="translate(-6, -6) scale(0.5)"
          fill="none"
          stroke="rgb(24 24 27)"
          stroke-width="3.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M4.5 12.75l6 6 9-13.5"
        />
      </g>
      <text
        :y="nodeRadius + fontSize + 2"
        text-anchor="middle"
        fill="rgb(212 212 216)"
        :font-size="fontSize"
        font-family="system-ui,-apple-system,sans-serif"
        style="paint-order: stroke; stroke: rgb(0 0 0 / 70%); stroke-width: 3px"
      >
        {{ truncate(node.data.name) }}
      </text>
    </g>
  </svg>
</template>

<style scoped>
.maps-aggregation-subtree {
  position: absolute;
  pointer-events: none;
}

.maps-aggregation-subtree__node {
  pointer-events: auto;
  cursor: pointer;
}

.maps-aggregation-subtree__node:focus-visible {
  outline: 2px solid var(--color-corporate-green-50);
  outline-offset: 2px;
}
</style>
