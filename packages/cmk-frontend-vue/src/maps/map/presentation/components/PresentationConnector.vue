<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import type { ObjectState, ShapeElement } from '@/maps/types/api'

import { type FlowVisual, flowVisual } from '../connectorFlow'

interface Pt {
  x: number
  y: number
}

const props = defineProps<{
  element: ShapeElement
  start: Pt
  end: Pt
  state: ObjectState | undefined
  selected: boolean
  interactive: boolean
  // View-mode drill-down on a bound link: hover/open events instead of editing.
  hoverable?: boolean
  scale: number
}>()

defineEmits<{
  pointerdown: [PointerEvent]
  endpointDown: [which: 'start' | 'end', event: PointerEvent]
  hover: [MouseEvent]
  'hover-leave': []
  open: [MouseEvent]
  context: [MouseEvent]
}>()

const visForward = computed(() => flowVisual(props.element, props.state))
const visBack = computed(() =>
  flowVisual(props.element, props.state, props.element.flow_metric_back ?? null)
)
// Classic two-way weathermap: a back metric splits the link at its midpoint,
// each half coloured/animated by its own direction, arrows meeting in the middle.
const twoWay = computed(() => !!props.element.flow && !!props.element.flow_metric_back)

const isArrow = computed(() => props.element.shape === 'arrow')
const angle = computed(() => Math.atan2(props.end.y - props.start.y, props.end.x - props.start.x))

const haloWidth = computed(() =>
  twoWay.value
    ? Math.max(visForward.value.width, visBack.value.width) + 8
    : visForward.value.width + 8
)

function lerp(t: number): Pt {
  return {
    x: props.start.x + (props.end.x - props.start.x) * t,
    y: props.start.y + (props.end.y - props.start.y) * t
  }
}

// Marching-ants flow: animate the dash offset toward the segment end by one
// dash period.
function flowStyleFor(vis: FlowVisual): Record<string, string> {
  if (vis.durationSec === null) {
    return {}
  }
  const period =
    (vis.dashArray ?? '')
      .split(/\s+/)
      .map(Number)
      .reduce((a, b) => a + b, 0) || 18
  return {
    '--pres-flow-shift': `${-period}px`,
    animationDuration: `${vis.durationSec}s`
  }
}

function arrowFor(tip: Pt, a: number, width: number): { base: Pt; points: string } {
  const headLen = Math.max(10, width * 2.4)
  const base = { x: tip.x - Math.cos(a) * headLen, y: tip.y - Math.sin(a) * headLen }
  const w = Math.max(6, width * 1.6)
  const baseL = { x: base.x - Math.sin(a) * w, y: base.y + Math.cos(a) * w }
  const baseR = { x: base.x + Math.sin(a) * w, y: base.y - Math.cos(a) * w }
  return { base, points: `${tip.x},${tip.y} ${baseL.x},${baseL.y} ${baseR.x},${baseR.y}` }
}

interface Segment {
  x1: number
  y1: number
  x2: number
  y2: number
  vis: FlowVisual
  arrowPoints: string | null
  flowStyle: Record<string, string>
}

const segments = computed<Segment[]>(() => {
  if (!twoWay.value) {
    const vis = visForward.value
    const arrow = isArrow.value ? arrowFor(props.end, angle.value, vis.width) : null
    const tail = arrow ? arrow.base : props.end
    return [
      {
        x1: props.start.x,
        y1: props.start.y,
        x2: tail.x,
        y2: tail.y,
        vis,
        arrowPoints: arrow?.points ?? null,
        flowStyle: flowStyleFor(vis)
      }
    ]
  }
  // Two-way: forward half runs start→mid, return half end→mid; both always
  // carry an arrowhead so the directions read at a glance.
  const GAP = 0.04
  const midF = lerp(0.5 - GAP)
  const midB = lerp(0.5 + GAP)
  const arrowF = arrowFor(midF, angle.value, visForward.value.width)
  const arrowB = arrowFor(midB, angle.value + Math.PI, visBack.value.width)
  return [
    {
      x1: props.start.x,
      y1: props.start.y,
      x2: arrowF.base.x,
      y2: arrowF.base.y,
      vis: visForward.value,
      arrowPoints: arrowF.points,
      flowStyle: flowStyleFor(visForward.value)
    },
    {
      x1: props.end.x,
      y1: props.end.y,
      x2: arrowB.base.x,
      y2: arrowB.base.y,
      vis: visBack.value,
      arrowPoints: arrowB.points,
      flowStyle: flowStyleFor(visBack.value)
    }
  ]
})
</script>

<template>
  <g
    :class="{ 'maps-presentation-connector--selected': selected }"
    @pointerdown="$emit('pointerdown', $event)"
  >
    <!-- Wide transparent hit area: selecting / dragging in the editor, hover
         and drill-down on a bound link in view mode. -->
    <line
      v-if="interactive || hoverable"
      class="maps-presentation-connector__hit"
      :x1="start.x"
      :y1="start.y"
      :x2="end.x"
      :y2="end.y"
      :stroke-width="16 / scale"
      @mouseenter="hoverable && $emit('hover', $event)"
      @mouseleave="hoverable && $emit('hover-leave')"
      @click="hoverable && $emit('open', $event)"
      @contextmenu="hoverable && $emit('context', $event)"
    />
    <line
      v-if="selected"
      class="maps-presentation-connector__halo"
      :x1="start.x"
      :y1="start.y"
      :x2="end.x"
      :y2="end.y"
      :stroke-width="haloWidth"
    />
    <!-- One segment for a plain link, two (split at the midpoint, arrows
         meeting in the middle) for a two-way weathermap link. -->
    <template v-for="(seg, i) in segments" :key="i">
      <line
        class="maps-presentation-connector__line"
        :class="{ 'maps-presentation-connector__line--flow': seg.vis.durationSec !== null }"
        :x1="seg.x1"
        :y1="seg.y1"
        :x2="seg.x2"
        :y2="seg.y2"
        :stroke="seg.vis.color"
        :stroke-width="seg.vis.width"
        :stroke-dasharray="seg.vis.dashArray"
        :style="seg.flowStyle"
        stroke-linecap="round"
      />
      <polygon v-if="seg.arrowPoints" :points="seg.arrowPoints" :fill="seg.vis.color" />
    </template>
    <!-- Endpoint handles: drag onto an element to dock, off to free. -->
    <template v-if="selected && interactive">
      <circle
        :cx="start.x"
        :cy="start.y"
        :r="8 / scale"
        :stroke-width="2 / scale"
        class="maps-presentation-connector__dot"
        @pointerdown.stop="$emit('endpointDown', 'start', $event)"
      />
      <circle
        :cx="end.x"
        :cy="end.y"
        :r="8 / scale"
        :stroke-width="2 / scale"
        class="maps-presentation-connector__dot"
        @pointerdown.stop="$emit('endpointDown', 'end', $event)"
      />
    </template>
    <!-- Value/label pills render in the labels overlay above the elements
         (PresentationConnectorLabels) so docked endpoints can't cover them. -->
  </g>
</template>

<style scoped>
.maps-presentation-connector__hit {
  stroke: transparent;
  stroke-width: 16;
  cursor: pointer;
  pointer-events: stroke;
}

.maps-presentation-connector__halo {
  stroke: color-mix(in srgb, var(--color-corporate-green-50) 55%, transparent);
  pointer-events: none;
}

.maps-presentation-connector__line {
  pointer-events: none;
}

.maps-presentation-connector__line--flow {
  animation-name: pres-flow;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
}

@keyframes pres-flow {
  to {
    stroke-dashoffset: var(--pres-flow-shift, -18px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .maps-presentation-connector__line--flow {
    animation: none;
  }
}

.maps-presentation-connector__dot {
  fill: var(--white);
  stroke: var(--color-corporate-green-50);
  pointer-events: auto;
  cursor: grab;
}

.maps-presentation-connector__dot:active {
  cursor: grabbing;
}
</style>
