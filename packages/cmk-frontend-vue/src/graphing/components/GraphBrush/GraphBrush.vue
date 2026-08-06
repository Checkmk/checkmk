<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { area } from 'd3-shape'
import { computed, onBeforeUnmount, ref } from 'vue'

import type { TimeRangeCommitKind } from '../../types'
import type { Metric, RequestedTimeRange, TimeRange } from '../TimeSeriesGraph'
import {
  type BrushMode,
  clampMove,
  hitTestMode,
  pxToTime,
  recenter,
  resizeLeft,
  resizeRight,
  timeToPx
} from './geometry'
import { computeSparklineBands, formatOverviewExtent } from './utils'

const props = defineProps<{
  metrics: Metric[] // coarse overview series
  domain: TimeRange // strip extent
  window: { start: number; end: number } // selection = renderer viewTimeRange
  minSpan: number | null
  width: number // figure width (px)
  plotLeft: number // track left inset (= renderer MARGIN.left)
  plotWidth: number // track width (= plot width)
}>()

const emit = defineEmits<{
  'update:requestedTimeRange': [RequestedTimeRange, TimeRangeCommitKind]
}>()

const DRAG_THRESHOLD_PX = 4
const HANDLE_PX = 7 // hit-test half-width for the edge resize handles

const STRIP_TOP = 9
const STRIP_H = 32
const STRIP_BOTTOM = STRIP_TOP + STRIP_H
const BAR_Y = 45
const BAR_H = 8
const TRACK_TOP = STRIP_TOP
const TRACK_H = BAR_Y + BAR_H - TRACK_TOP
const TRACK_BOTTOM = TRACK_TOP + TRACK_H

const EDGE_TOP = TRACK_TOP
const EDGE_BOTTOM = BAR_Y + BAR_H
const HANDLE_W = 8
const HANDLE_H = 16
const HANDLE_TOP = (STRIP_TOP + STRIP_BOTTOM) / 2 - HANDLE_H / 2
const HANDLE_GRIP_DX = [-2, 0, 2]
const HANDLE_GRIP_Y1 = HANDLE_TOP + 4
const HANDLE_GRIP_Y2 = HANDLE_TOP + HANDLE_H - 4

const LABEL_GAP = 6
const LABEL_Y = EDGE_BOTTOM + LABEL_GAP + 8 // baseline (+8 ≈ the 11px label's cap height)
const HEIGHT = LABEL_Y + 4 // room below the baseline for descenders

const toPx = (time: number) =>
  timeToPx(time, props.domain.start, props.domain.end, props.plotLeft, props.plotWidth)
const toTime = (px: number) =>
  pxToTime(px, props.domain.start, props.domain.end, props.plotLeft, props.plotWidth)

const sparklinePaths = computed<{ d: string; color: string }[]>(() => {
  const { bands, sampleCount, yMin, yMax } = computeSparklineBands(props.metrics)
  if (sampleCount === 0) {
    return []
  }
  const sampleTimes = Array.from(
    { length: sampleCount },
    (_, i) => props.domain.start + i * props.domain.step
  )
  const span = yMax - yMin || 1
  // Maps the value domain into the strip (STRIP_TOP..STRIP_BOTTOM); the move-bar sits below it.
  const yPx = (value: number) => STRIP_BOTTOM - ((value - yMin) / span) * STRIP_H

  return bands.map(({ lower, upper, color }) => {
    const gen = area<number>()
      .x((_, i) => toPx(sampleTimes[i]!))
      .y0((_, i) => yPx(lower[i]!))
      .y1((_, i) => yPx(upper[i]!))
    return { d: gen(lower) ?? '', color }
  })
})

const svgRef = ref<SVGSVGElement | null>(null)
const preview = ref<{ start: number; end: number } | null>(null)
const dragging = ref(false)
const winRange = computed(() => preview.value ?? props.window)
const winLeftPx = computed(() => toPx(winRange.value.start))
const winRightPx = computed(() => toPx(winRange.value.end))

const edgeHandles = computed(() =>
  [winLeftPx.value, winRightPx.value].map((x) => ({
    x,
    grips: HANDLE_GRIP_DX.map((dx) => x + dx)
  }))
)

const rangeLabel = computed(() => formatOverviewExtent(props.domain))

let mode: BrushMode = 'move'
let grabOffset = 0 // seconds between cursor and window.start (move)

const localX = (ev: MouseEvent) => ev.clientX - (svgRef.value?.getBoundingClientRect().left ?? 0)
const localY = (ev: MouseEvent) => ev.clientY - (svgRef.value?.getBoundingClientRect().top ?? 0)

// The svg spans the whole figure; only the track itself is interactive.
function onTrack(x: number, y: number): boolean {
  return (
    x >= props.plotLeft &&
    x <= props.plotLeft + props.plotWidth &&
    y >= TRACK_TOP &&
    y <= TRACK_BOTTOM
  )
}

function onMouseDown(ev: MouseEvent): void {
  const x = localX(ev)
  if (ev.button !== 0 || !onTrack(x, localY(ev))) {
    return
  }
  ev.preventDefault()
  const span = props.window.end - props.window.start
  mode = hitTestMode(x, toPx(props.window.start), toPx(props.window.end), HANDLE_PX)
  if (mode === 'recenter') {
    const [s, e] = recenter(toTime(x), span, props.domain.start, props.domain.end)
    preview.value = { start: s, end: e }
    grabOffset = toTime(x) - s
    mode = 'move'
  } else if (mode === 'move') {
    grabOffset = toTime(x) - props.window.start
  }
  dragging.value = true
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

function onMove(ev: MouseEvent): void {
  const time = toTime(localX(ev))
  const span = props.window.end - props.window.start
  const floor = props.minSpan ?? 60
  if (mode === 'move') {
    const [s, e] = clampMove(
      time - grabOffset,
      time - grabOffset + span,
      props.domain.start,
      props.domain.end
    )
    preview.value = { start: s, end: e }
  } else if (mode === 'resize-l') {
    preview.value = {
      start: resizeLeft(time, props.window.end, props.domain.start, floor),
      end: props.window.end
    }
  } else if (mode === 'resize-r') {
    preview.value = {
      start: props.window.start,
      end: resizeRight(time, props.window.start, props.domain.end, floor)
    }
  }
}

function onUp(): void {
  window.removeEventListener('mousemove', onMove)
  window.removeEventListener('mouseup', onUp)
  dragging.value = false
  const next = preview.value
  preview.value = null
  if (!next) {
    return
  }
  if (
    Math.abs(toPx(next.start) - toPx(props.window.start)) < DRAG_THRESHOLD_PX &&
    Math.abs(toPx(next.end) - toPx(props.window.end)) < DRAG_THRESHOLD_PX
  ) {
    return
  }
  emit(
    'update:requestedTimeRange',
    { start: Math.round(next.start), end: Math.round(next.end) },
    mode === 'move' ? 'translated_timerange' : 'changed_timerange_span'
  )
}

onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onMove)
  window.removeEventListener('mouseup', onUp)
})
</script>

<template>
  <svg
    ref="svgRef"
    class="graphing-graph-brush"
    :class="{ 'graphing-graph-brush--dragging': dragging }"
    :width="width"
    :height="HEIGHT"
    @mousedown="onMouseDown"
  >
    <!-- Outer track encloses the waveform strip and the move-bar below it. -->
    <rect
      class="graphing-graph-brush__track"
      :x="plotLeft"
      :y="TRACK_TOP"
      :width="plotWidth"
      :height="TRACK_H"
    />
    <!-- Coarse cumulative-area sparkline (the overview waveform). -->
    <path
      v-for="(p, i) in sparklinePaths"
      :key="`area-${i}`"
      class="graphing-graph-brush__area"
      :d="p.d"
      :fill="p.color"
    />
    <!-- Dim the waveform outside the selection window. -->
    <rect
      class="graphing-graph-brush__mask"
      :x="plotLeft"
      :y="STRIP_TOP"
      :width="Math.max(0, winLeftPx - plotLeft)"
      :height="STRIP_H"
    />
    <rect
      class="graphing-graph-brush__mask"
      :x="winRightPx"
      :y="STRIP_TOP"
      :width="Math.max(0, plotLeft + plotWidth - winRightPx)"
      :height="STRIP_H"
    />
    <!-- Selection window over the waveform. -->
    <rect
      class="graphing-graph-brush__window"
      :x="winLeftPx"
      :y="STRIP_TOP"
      :width="Math.max(0, winRightPx - winLeftPx)"
      :height="STRIP_H"
    />
    <!-- Teal move-bar (drag to pan), below the waveform. -->
    <rect
      class="graphing-graph-brush__bar"
      :x="winLeftPx"
      :y="BAR_Y"
      :width="Math.max(0, winRightPx - winLeftPx)"
      :height="BAR_H"
      rx="6"
    />
    <!-- Each window edge: a full-height border line with a small centred resize handle. -->
    <g v-for="(handle, i) in edgeHandles" :key="`handle-${i}`">
      <line
        class="graphing-graph-brush__edge"
        :x1="handle.x"
        :x2="handle.x"
        :y1="EDGE_TOP"
        :y2="EDGE_BOTTOM"
      />
      <rect
        class="graphing-graph-brush__handle"
        :x="handle.x - HANDLE_W / 2"
        :y="HANDLE_TOP"
        :width="HANDLE_W"
        :height="HANDLE_H"
        rx="2"
      />
      <line
        v-for="(gx, k) in handle.grips"
        :key="`grip-${i}-${k}`"
        class="graphing-graph-brush__grip"
        :x1="gx"
        :x2="gx"
        :y1="HANDLE_GRIP_Y1"
        :y2="HANDLE_GRIP_Y2"
      />
    </g>

    <!-- Overview extent (the time range the strip covers), bottom-left. -->
    <text class="graphing-graph-brush__range" :x="plotLeft + 2" :y="LABEL_Y">{{ rangeLabel }}</text>
  </svg>
</template>

<style scoped>
.graphing-graph-brush {
  display: block;
  user-select: none;
}

.graphing-graph-brush--dragging {
  cursor: grabbing;
}

.graphing-graph-brush__track {
  fill: transparent;
  stroke: var(--ux-theme-6, #e0e0e0);
  shape-rendering: crispedges;
  cursor: grab;
}

.graphing-graph-brush__area {
  fill-opacity: 0.6;
  stroke: none;
}

.graphing-graph-brush__mask {
  fill: rgb(0 0 0 / 35%);
  cursor: pointer;
  pointer-events: all;
}

.graphing-graph-brush__window {
  fill: transparent;
  stroke: var(--ux-theme-7, #b0b0b0);
  stroke-opacity: 0.4;
  shape-rendering: crispedges;
  cursor: grab;
}

.graphing-graph-brush__bar {
  fill: var(--color-corporate-green-50, #15d1a0);
  cursor: grab;
}

.graphing-graph-brush--dragging .graphing-graph-brush__track,
.graphing-graph-brush--dragging .graphing-graph-brush__mask,
.graphing-graph-brush--dragging .graphing-graph-brush__window,
.graphing-graph-brush--dragging .graphing-graph-brush__bar {
  cursor: grabbing;
}

.graphing-graph-brush__edge {
  stroke: var(--color-mid-grey-60, #677883);
  stroke-width: 1;
  stroke-opacity: 0.5;
  shape-rendering: crispedges;
  pointer-events: none;
}

.graphing-graph-brush__handle {
  fill: var(--color-midnight-grey-100, #0f1215);
  stroke: var(--color-mid-grey-60, #677883);
  cursor: ew-resize;
}

.graphing-graph-brush__handle:hover {
  fill: var(--color-midnight-grey-80, #2b3138);
}

.graphing-graph-brush__grip {
  stroke: rgb(255 255 255 / 80%);
  pointer-events: none;
}

.graphing-graph-brush__range {
  fill: var(--font-color-dimmed, #73848d);
  font-size: 11px;
  pointer-events: none;
}
</style>
